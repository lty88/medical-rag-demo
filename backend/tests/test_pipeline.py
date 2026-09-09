"""医疗安全主链路的局部单元测试。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.config import BASE_DIR, Settings
from app.models import ConsultationRequest, ResearchSearchRequest, SourceDocument
from app.pipeline import MedicalRagPipeline
from app.services.atlas import build_body_atlas
from app.services.embedding_text import build_embedding_text
from app.services.generator import EvidenceBoundGenerator
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


class GeneratorTests(unittest.TestCase):
    """验证最终检索证据会进入兼容 LLM 接口并保留失败原因。"""

    def setUp(self) -> None:
        """创建一条带来源和权限信息的最终候选证据。"""

        from app.models import RankedDocument

        self.candidates = [
            RankedDocument(
                document=SourceDocument(
                    id="evidence-1",
                    title="咳嗽伴血痰的相关资料",
                    question="咳嗽时痰中带血怎么办",
                    content="痰中带血需要结合出血量和伴随表现进一步评估。",
                    source="test-guideline",
                    source_type="guideline",
                    trust_level="primary",
                    allow_treatment_generation=False,
                )
            )
        ]

    def test_sends_final_evidence_to_configured_llm(self) -> None:
        """验证候选全文、来源与权限真正交给新的 LangChain 入口。"""
        generator = EvidenceBoundGenerator(
            "https://llm.example/v1", "test-key", "test-model", enable_thinking=False,
        )
        output = {"title": "辅助信息", "summary": "需要进一步评估[S1]",
                  "sections": [{"title": "依据", "content": "关注出血量[S1]"}]}
        with patch("app.services.generator.complete_json", return_value=output) as call:
            answer = generator.generate("咳嗽时有血痰", self.candidates, [], False)
        self.assertEqual(answer.mode, "configured-llm")
        self.assertIn("test-guideline", call.call_args.kwargs["user_content"])
        self.assertIn("痰中带血需要结合出血量", call.call_args.kwargs["user_content"])
        self.assertIn("不允许", call.call_args.kwargs["user_content"])
        self.assertIs(call.call_args.kwargs["enable_thinking"], False)

    def test_reports_missing_model_in_fallback_detail(self) -> None:
        """未配置模型时保留证据模板回退并解释缺失字段。"""
        generator = EvidenceBoundGenerator("https://llm.example/v1", "test-key", None)
        answer = generator.generate("咳嗽时有血痰", self.candidates, [], False)
        self.assertEqual(answer.mode, "evidence-template")
        self.assertIn("LLM_MODEL", answer.detail)

    def test_model_failure_preserves_safe_fallback(self) -> None:
        """共享 SDK 错误仍进入原来的安全模板回退。"""
        from app.services.langchain_chat import ModelCallError

        generator = EvidenceBoundGenerator("https://llm.example/v1", "secret-test-key", "test")
        with patch("app.services.generator.complete_json",
                   side_effect=ModelCallError("模型服务返回 HTTP 403")):
            answer = generator.generate("咳嗽时有血痰", self.candidates, [], False)
        self.assertEqual(answer.mode, "evidence-template")
        self.assertIn("HTTP 403", answer.detail)
        self.assertNotIn("secret-test-key", answer.detail)


class AtlasTests(unittest.TestCase):
    """验证健康可视化数据具有系统层级和非诊断边界。"""

    def test_body_atlas_contains_systems_and_safety_boundary(self) -> None:
        """人体图谱应包含核心系统并明确不构成个体诊断。"""

        atlas = build_body_atlas()

        self.assertGreaterEqual(len(atlas.systems), 6)
        self.assertTrue(any(system.id == "circulatory" for system in atlas.systems))
        self.assertGreaterEqual(len(atlas.departments), 45)
        stomatology = next(
            department
            for department in atlas.departments
            if department.id == "stomatology"
        )
        self.assertEqual(stomatology.official_code, "12")
        digestive = next(system for system in atlas.systems if system.id == "digestive")
        self.assertTrue(any(organ.id == "upper-anterior-teeth" for organ in digestive.organs))
        anorectal = next(organ for organ in digestive.organs if organ.id == "anorectal")
        self.assertIn("colorectal-surgery", anorectal.department_ids)
        self.assertTrue(
            any(option.id == "bleeding" for option in anorectal.symptom_options)
        )
        perianal = next(
            region for region in atlas.body_regions if region.id == "perianal-region"
        )
        self.assertIn("tcm-anorectal", perianal.department_ids)
        self.assertIn("不构成诊断", atlas.disclaimer)


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
            llm_base_url=None,
            llm_api_key=None,
            llm_model=None,
        )
        self.pipeline = MedicalRagPipeline(settings)

    def tearDown(self) -> None:
        """释放测试创建的临时目录。"""

        self.temporary_directory.cleanup()

    def test_routine_question_reaches_validation(self) -> None:
        """普通头痛信息请求应完成检索并通过引用校验。"""

        with self.assertLogs(
            "uvicorn.error.medical_rag.pipeline", level="INFO"
        ) as captured_logs:
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
        log_text = "\n".join(captured_logs.output)
        self.assertIn("[用户输入]", log_text)
        self.assertIn("[检索结果][BM25]", log_text)
        self.assertIn("[检索结果][最终证据]", log_text)

    def test_emergency_question_stops_before_retrieval(self) -> None:
        """验证图的急症分支不会调用 Retriever 或生成器，而非仅检查响应文案。"""

        with (
            patch.object(self.pipeline, "_retrieve", side_effect=AssertionError("急症不应检索")) as retrieve,
            patch.object(self.pipeline.generator, "generate", side_effect=AssertionError("急症不应生成")) as generate,
        ):
            response = self.pipeline.consult(
                ConsultationRequest(
                    symptoms="突然胸痛，伴随大汗和呼吸困难，疼痛向左臂放射。",
                    age=56,
                    sex="male",
                )
            )
        retrieve.assert_not_called()
        generate.assert_not_called()
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

    def test_research_search_returns_ranked_evidence_without_generation(self) -> None:
        """研究检索应返回精排分数和来源，不进入答案生成器。"""

        with self.assertLogs(
            "uvicorn.error.medical_rag.pipeline", level="INFO"
        ) as captured_logs:
            response = self.pipeline.search_research_evidence(
                ResearchSearchRequest(query="头痛需要关注什么", top_k=3)
            )

        self.assertTrue(response.results)
        self.assertLessEqual(response.total, 3)
        self.assertTrue(response.results[0].source)
        self.assertGreaterEqual(response.results[0].rerank_score, 0)
        log_text = "\n".join(captured_logs.output)
        self.assertIn("[检索结果][研究检索]", log_text)
        self.assertNotIn("[LLM请求]", log_text)


if __name__ == "__main__":
    unittest.main()
