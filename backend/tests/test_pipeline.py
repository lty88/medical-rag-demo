"""医疗安全主链路的局部单元测试。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.config import BASE_DIR, Settings
from app.models import ConsultationRequest, SourceDocument
from app.pipeline import MedicalRagPipeline
from app.services.embedding_text import build_embedding_text
from app.services.persistent_index import build_fts_query
from app.services.privacy import redact_privacy
from app.services.retrieval import reciprocal_rank_fusion
from app.services.triage import evaluate_red_flags


class PrivacyTests(unittest.TestCase):
    """验证常见直接身份信息不会进入后续链路。"""

    def test_redacts_phone_and_identity_number(self) -> None:
        """手机号和身份证号应被替换并记录命中类型。"""

        result = redact_privacy("手机号13800138000，身份证110101199001011234，头痛")
        self.assertNotIn("13800138000", result.text)
        self.assertNotIn("110101199001011234", result.text)
        self.assertEqual(result.redacted_types, ("手机号", "身份证号"))


class TriageTests(unittest.TestCase):
    """验证高风险描述会在检索前被规则捕获。"""

    def test_detects_chest_pain_with_supporting_signs(self) -> None:
        """胸痛伴大汗和呼吸困难应命中心血管危险信号。"""

        request = ConsultationRequest(symptoms="占位", age=56, sex="male")
        hits = evaluate_red_flags(request, "突然胸痛，伴随大汗和呼吸困难")
        self.assertIn("可能的急性心血管危险信号", hits)

    def test_detects_young_infant_fever(self) -> None:
        """三月龄以下婴儿达到规则体温时应被阻断。"""

        request = ConsultationRequest(
            symptoms="发热",
            age=0.1,
            temperature=38.0,
        )
        hits = evaluate_red_flags(request, request.symptoms)
        self.assertTrue(any("3 月龄以下" in hit for hit in hits))


class RetrievalTests(unittest.TestCase):
    """验证检索不依赖硬编码扩展，并能按文档 ID 融合独立召回。"""

    def test_fts_query_does_not_inject_hardcoded_medical_phrases(self) -> None:
        """关键词检索只应分析原始查询，不再注入人工维护的同义短语。"""

        fts_query = build_fts_query("饿了就肚子痛")
        self.assertNotIn("空腹", fts_query)
        self.assertNotIn("饥饿", fts_query)
        self.assertNotIn("胃痛", fts_query)

    def test_rrf_merges_independent_results_by_document_id(self) -> None:
        """同一文档分别被 BM25 与 FAISS 命中时应合并为一个候选。"""

        shared = SourceDocument(
            id="shared",
            title="共同候选",
            content="共同内容",
            source="test",
            source_type="test",
        )
        vector_only = SourceDocument(
            id="vector-only",
            title="向量候选",
            content="向量内容",
            source="test",
            source_type="test",
        )
        results = reciprocal_rank_fusion(
            [(shared, 8.0)],
            [(vector_only, 0.9), (shared, 0.8)],
            top_k=5,
        )
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].document.id, "shared")
        self.assertGreater(results[0].bm25_score, 0)
        self.assertGreater(results[0].vector_score, 0)


class EmbeddingTextTests(unittest.TestCase):
    """验证不同医疗资料会生成适合语义召回的向量文本。"""

    def test_medical_qa_uses_question_without_long_answer(self) -> None:
        """医疗问答应编码问题和关键词，不应让长回答稀释查询语义。"""

        text = build_embedding_text(
            title="饿了就胃痛怎么办",
            question="饿了就胃痛怎么办",
            content="这是一段很长的治疗与疾病介绍正文，不应进入问答向量。",
            keywords='["空腹", "胃痛"]',
            source_type="medical_qa",
            evidence_content_character_limit=512,
        )

        self.assertEqual(text.count("饿了就胃痛怎么办"), 1)
        self.assertIn("空腹", text)
        self.assertIn("胃痛", text)
        self.assertNotIn("治疗与疾病介绍正文", text)

    def test_evidence_document_includes_limited_content(self) -> None:
        """指南等证据文档应保留标题、关键词和受限长度的正文。"""

        text = build_embedding_text(
            title="急性腹痛临床路径",
            question="急性腹痛如何评估",
            content="先评估生命体征，再检查腹部危险信号。后续内容不参与本次测试。",
            keywords=["腹痛", "危险信号"],
            source_type="clinical_pathway",
            evidence_content_character_limit=20,
        )

        self.assertIn("急性腹痛临床路径", text)
        self.assertIn("危险信号", text)
        self.assertIn("先评估生命体征", text)
        self.assertNotIn("后续内容", text)


class PipelineTests(unittest.TestCase):
    """验证普通、急症和治疗请求三条核心路径。"""

    def setUp(self) -> None:
        """创建只加载内置示例知识的隔离流水线。"""

        self.temporary_directory = tempfile.TemporaryDirectory()
        settings = Settings(
            sample_data_path=BASE_DIR / "data" / "sample_knowledge.jsonl",
            raw_data_dir=Path(self.temporary_directory.name),
            search_index_path=Path(self.temporary_directory.name) / "missing.db",
            max_loaded_documents=100,
            retrieval_top_k=6,
            rrf_top_k=12,
            final_top_k=3,
            embedding_model=None,
            reranker_model=None,
        )
        self.pipeline = MedicalRagPipeline(settings)

    def tearDown(self) -> None:
        """释放测试创建的临时目录。"""

        self.temporary_directory.cleanup()

    def test_routine_question_reaches_validation(self) -> None:
        """普通头痛信息请求应完成检索并通过引用校验。"""

        response = self.pipeline.consult(
            ConsultationRequest(
                symptoms="头痛两天，休息后缓解，没有肢体无力，还需要观察什么？",
                age=28,
                sex="female",
                duration="2天",
            )
        )
        self.assertFalse(response.blocked)
        self.assertTrue(response.citations)
        self.assertEqual(response.pipeline[-1].key, "validation")
        self.assertEqual(response.pipeline[-1].status, "passed")

    def test_emergency_question_stops_before_retrieval(self) -> None:
        """急症描述应在危险信号阶段停止，不执行召回。"""

        response = self.pipeline.consult(
            ConsultationRequest(
                symptoms="突然胸痛，伴随大汗和呼吸困难，疼痛向左臂放射。",
                age=56,
                sex="male",
            )
        )
        self.assertTrue(response.blocked)
        self.assertEqual(response.urgency, "emergency")
        self.assertEqual(response.pipeline[-1].key, "triage")
        self.assertFalse(response.citations)

    def test_treatment_question_is_rejected_without_authorized_source(self) -> None:
        """只有示例或普通问答证据时不得生成具体药物治疗。"""

        response = self.pipeline.consult(
            ConsultationRequest(
                symptoms="怀孕12周，发热一天，应该吃什么药、用多少剂量？",
                age=31,
                sex="female",
                pregnant=True,
                temperature=38.2,
            )
        )
        self.assertTrue(response.blocked)
        self.assertEqual(response.urgency, "insufficient")
        self.assertIn("当前证据均无治疗生成权限", response.validation_issues)


if __name__ == "__main__":
    unittest.main()
