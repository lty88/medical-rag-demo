"""病历、检查报告与医学报告截图的安全提取和辅助解读服务。"""

from __future__ import annotations

import base64
import logging
import re
import time
import uuid
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any
from app.services.langchain_chat import ModelCallError, complete_json, parse_complete_json

from pypdf import PdfReader
from pypdf.errors import PyPdfError
from pydantic import ValidationError

from app.config import Settings
from app.models import (
    AnswerSection,
    MedicalDocumentEvidence,
    MedicalDocumentFinding,
    MedicalDocumentInterpretationResponse,
    ResearchSearchResponse,
)
from app.services.privacy import redact_privacy


LOGGER = logging.getLogger("uvicorn.error.medical_rag.document")
SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".png", ".jpg", ".jpeg", ".webp"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
IMAGE_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}
DOCUMENT_TYPE_LABELS = {
    "outpatient_record": "门诊病历",
    "discharge_record": "出院记录",
    "laboratory_report": "检验报告",
    "ultrasound_report": "超声或 B 超报告",
    "imaging_report": "CT、MRI 或 X 光影像报告",
    "pathology_report": "病理报告",
    "other": "其他医疗资料",
}


class DocumentInterpretationError(Exception):
    """可安全返回给前端的文件校验或模型调用异常。"""

    def __init__(self, status_code: int, message: str) -> None:
        """保存 HTTP 状态码和不包含隐私内容的错误说明。

        Args:
            status_code: 接口应返回的 HTTP 状态码。
            message: 可直接展示给用户的安全错误说明。
        """

        super().__init__(message)
        self.status_code = status_code
        self.message = message


@dataclass(frozen=True)
class ExtractedMedicalDocument:
    """完成格式校验和文本提取后的内存对象。"""

    file_name: str
    document_type: str
    extraction_mode: str
    text: str


class MedicalDocumentInterpreter:
    """将用户上传资料转成可检索、可追溯的结构化辅助解读。"""

    def __init__(self, settings: Settings) -> None:
        """保存文件限制和 OpenAI 兼容模型配置。

        Args:
            settings: 应用文件限制、LLM 与视觉模型配置。
        """

        self.settings = settings

    def validate_upload(self, file_name: str, data: bytes) -> tuple[str, str]:
        """校验文件名、扩展名、体积和关键文件头。

        Args:
            file_name: 浏览器上传的原始文件名。
            data: 已限制长度读取的文件字节。

        Returns:
            安全文件名和小写扩展名。

        Raises:
            DocumentInterpretationError: 文件为空、超限、格式不支持或伪装扩展名时抛出。
        """

        normalized_name = (file_name or "未命名资料").replace("\\", "/")
        safe_name = Path(normalized_name).name[:180]
        extension = Path(safe_name).suffix.lower()
        if not data:
            raise DocumentInterpretationError(400, "文件内容为空，请重新选择资料。")
        if len(data) > self.settings.medical_document_max_bytes:
            limit_mb = self.settings.medical_document_max_bytes / 1024 / 1024
            raise DocumentInterpretationError(413, f"文件超过 {limit_mb:g} MB 限制。")
        if extension not in SUPPORTED_EXTENSIONS:
            raise DocumentInterpretationError(
                415,
                "当前支持 PDF、TXT、Markdown、PNG、JPG 和 WebP；DICOM 与视频需由专业影像系统处理。",
            )
        if extension == ".pdf" and not data.startswith(b"%PDF"):
            raise DocumentInterpretationError(415, "文件扩展名是 PDF，但内容不是有效 PDF。")
        if extension == ".png" and not data.startswith(b"\x89PNG\r\n\x1a\n"):
            raise DocumentInterpretationError(415, "文件扩展名是 PNG，但内容不是有效 PNG。")
        if extension in {".jpg", ".jpeg"} and not data.startswith(b"\xff\xd8\xff"):
            raise DocumentInterpretationError(415, "文件扩展名是 JPG，但内容不是有效 JPEG。")
        if extension == ".webp" and not (
            data.startswith(b"RIFF") and data[8:12] == b"WEBP"
        ):
            raise DocumentInterpretationError(415, "文件扩展名是 WebP，但内容不是有效 WebP。")
        return safe_name, extension

    def extract(
        self,
        file_name: str,
        data: bytes,
        declared_document_type: str,
        request_id: str,
    ) -> ExtractedMedicalDocument:
        """从文本、PDF 或报告图片中提取可用于检索的文字。

        Args:
            file_name: 浏览器上传的原始文件名。
            data: 文件完整字节，生命周期仅限当前请求。
            declared_document_type: 用户选择的资料类型。
            request_id: 串联提取、检索与生成日志的请求标识。

        Returns:
            已限制长度且经过常见身份字段脱敏的报告文字。

        Raises:
            DocumentInterpretationError: 无法提取文字或视觉模型不可用时抛出。
        """

        safe_name, extension = self.validate_upload(file_name, data)
        if extension in IMAGE_EXTENSIONS:
            extracted_text = self._extract_image_text(data, extension, request_id)
            extraction_mode = "vision"
        elif extension == ".pdf":
            extracted_text = self._extract_pdf_text(data)
            extraction_mode = "text"
        else:
            extracted_text = self._decode_text(data)
            extraction_mode = "text"

        normalized = re.sub(r"\n{3,}", "\n\n", extracted_text).strip()
        if len(normalized) < 10:
            raise DocumentInterpretationError(
                422,
                "没有识别到足够的报告文字。扫描版 PDF 请转成清晰图片上传，原始影像请由影像科医生阅片。",
            )
        limited = normalized[: self.settings.medical_document_max_characters]
        private_safe_text = redact_privacy(limited).text
        return ExtractedMedicalDocument(
            file_name=safe_name,
            document_type=declared_document_type,
            extraction_mode=extraction_mode,
            text=private_safe_text,
        )

    def interpret(
        self,
        document: ExtractedMedicalDocument,
        symptom_description: str,
        interpretation_focus: str,
        evidence_response: ResearchSearchResponse,
        request_id: str,
        started_at: float,
    ) -> MedicalDocumentInterpretationResponse:
        """结合上传资料、可选症状和本地 RAG 证据生成结构化解读。

        Args:
            document: 完成格式校验与隐私脱敏的资料。
            symptom_description: 用户选填的症状背景。
            interpretation_focus: 用户希望重点了解的方向。
            evidence_response: 本地 BM25、FAISS、RRF 与 Reranker 检索结果。
            request_id: 当前解读请求标识。
            started_at: API 接收请求时的高精度起始时间。

        Returns:
            含关键发现、风险提示、问医生问题、证据和限制的结构化结果。

        Raises:
            DocumentInterpretationError: 文本模型配置缺失、调用失败或响应不可解析时抛出。
        """

        if not all((self.settings.llm_base_url, self.settings.llm_api_key, self.settings.llm_model)):
            raise DocumentInterpretationError(
                503,
                "病历解读需要配置 LLM_BASE_URL、LLM_API_KEY 和 LLM_MODEL。",
            )
        evidence = self._format_evidence(evidence_response)
        system_prompt = (
            "你是医疗资料解读助手，只做资料释义和就医沟通辅助，不做确诊、处方或替代医生。"
            "必须区分报告原文、通俗解释和推测；不得把用户症状改写成报告结论。"
            "若上传的是超声、CT、MRI等报告截图，只解释图中文字；如果只有原始影像而没有可读报告，"
            "必须写入limitations并说明需要影像科医生阅片。不得给药名、剂量、停药或治疗方案。"
            "报告中的危急值、恶性可能、急性出血、梗阻、血栓或其他紧急措辞应列入red_flags；"
            "不确定时使用uncertain，不得为了安慰用户而标记normal。"
            "本地证据只能辅助解释，所有引用必须使用给定的[S数字]，证据不足时直接说明。"
            "输出必须是JSON对象，只含title、summary、urgency、findings、sections、red_flags、"
            "questions_for_doctor、limitations。findings每项只含name、original_text、explanation、level，"
            "level只能是normal、attention、urgent、uncertain；sections每项只含title、content；"
            "urgency只能是routine、attention、urgent、insufficient。"
        )
        user_prompt = (
            f"资料类型：{DOCUMENT_TYPE_LABELS.get(document.document_type, '其他医疗资料')}\n"
            f"用户症状（可能为空）：{redact_privacy(symptom_description).text or '未填写'}\n"
            f"解读重点：{interpretation_focus or '整体摘要与异常项'}\n\n"
            f"资料文字：\n{document.text}\n\n"
            f"本地检索证据：\n{evidence or '未检索到可用证据'}"
        )
        result = self._complete_json(
            self.settings.llm_model or "",
            system_prompt,
            user_prompt,
            request_id,
            "interpretation",
        )
        summary = str(result.get("summary") or "模型未生成有效摘要。")
        findings = self._parse_findings(result.get("findings"), request_id)
        sections = self._parse_sections(result.get("sections"), summary, request_id)
        return MedicalDocumentInterpretationResponse(
            request_id=request_id,
            file_name=document.file_name,
            document_type=document.document_type,
            extraction_mode=document.extraction_mode,  # type: ignore[arg-type]
            title=str(result.get("title") or "检查资料辅助解读"),
            summary=summary,
            urgency=self._normalize_urgency(result.get("urgency")),
            findings=findings,
            sections=sections,
            red_flags=self._string_list(result.get("red_flags")),
            questions_for_doctor=self._string_list(result.get("questions_for_doctor")),
            limitations=self._ensure_limitations(result.get("limitations"), document),
            evidence=self._build_evidence(evidence_response),
            retrieval_mode=evidence_response.retrieval_mode,
            generation_model=self.settings.llm_model or "",
            privacy_notice="本服务不主动持久保存报告；上传框架可能使用临时文件。模型日志不记录正文。图片会发送给已配置的视觉模型，请上传前遮盖身份信息。",
            disclaimer="结果仅用于理解报告和准备就医问题，不是诊断结论，也不能替代出具报告的医生或影像科阅片。",
            duration_ms=round((time.perf_counter() - started_at) * 1000),
        )

    def _extract_pdf_text(self, data: bytes) -> str:
        """提取文字型 PDF 的前若干页文本。

        Args:
            data: 已验证 PDF 文件头的字节。

        Returns:
            按页拼接且受配置长度限制的文本。

        Raises:
            DocumentInterpretationError: PDF 加密、损坏或没有文本层时抛出。
        """

        try:
            reader = PdfReader(BytesIO(data))
            if reader.is_encrypted:
                raise DocumentInterpretationError(422, "暂不支持加密 PDF，请先解除密码保护。")
            pages = reader.pages[: self.settings.medical_document_max_pdf_pages]
            text = "\n\n".join(page.extract_text() or "" for page in pages)
        except DocumentInterpretationError:
            raise
        except (OSError, ValueError, PyPdfError) as error:
            raise DocumentInterpretationError(422, "PDF 无法读取或文件已经损坏。") from error
        if not text.strip():
            raise DocumentInterpretationError(
                422,
                "这个 PDF 没有可提取的文字层，请将关键页面导出为清晰图片后上传。",
            )
        return text

    def _decode_text(self, data: bytes) -> str:
        """将 UTF-8 或常见中文编码的纯文本资料解码。

        Args:
            data: TXT 或 Markdown 文件字节。

        Returns:
            解码后的 Unicode 文本。

        Raises:
            DocumentInterpretationError: 文件包含二进制内容或无法解码时抛出。
        """

        if b"\x00" in data[:4096]:
            raise DocumentInterpretationError(415, "文本文件包含二进制内容，无法安全读取。")
        for encoding in ("utf-8-sig", "gb18030"):
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        raise DocumentInterpretationError(422, "文本编码无法识别，请转换为 UTF-8。")

    def _extract_image_text(self, data: bytes, extension: str, request_id: str) -> str:
        """调用显式配置的视觉模型转录报告图片中的文字和结论。

        Args:
            data: 已验证格式的图片字节。
            extension: 图片小写扩展名。
            request_id: 当前解读请求标识。

        Returns:
            视觉模型逐字转录的报告文字。

        Raises:
            DocumentInterpretationError: 视觉模型配置缺失或无法返回有效文字时抛出。
        """

        if not all(
            (
                self.settings.llm_base_url,
                self.settings.llm_api_key,
                self.settings.llm_vision_model,
            )
        ):
            raise DocumentInterpretationError(
                503,
                "图片报告需要配置支持视觉输入的 LLM_VISION_MODEL。",
            )
        media_type = IMAGE_MEDIA_TYPES[extension]
        image_url = f"data:{media_type};base64,{base64.b64encode(data).decode('ascii')}"
        result = self._complete_json(
            self.settings.llm_vision_model or "",
            (
                "你是医疗文档转录器，不做诊断。逐字识别图片中可见的检查项目、数值、单位、参考范围、"
                "所见和结论，不补写看不清的内容。若图片主要是原始医学影像且没有可读报告文字，"
                "将extracted_text设为空，并在quality_note说明需要专业阅片。"
                "只返回JSON对象：extracted_text、quality_note。"
            ),
            [
                {"type": "text", "text": "请转录这份用户上传的医疗资料图片。"},
                {"type": "image_url", "image_url": {"url": image_url}},
            ],
            request_id,
            "vision-extraction",
        )
        extracted_text = str(result.get("extracted_text") or "").strip()
        if not extracted_text:
            quality_note = str(result.get("quality_note") or "图片中没有可读报告文字。")
            raise DocumentInterpretationError(422, quality_note[:300])
        return extracted_text

    def _complete_json(
        self,
        model: str,
        system_prompt: str,
        user_content: str | list[dict[str, Any]],
        request_id: str,
        stage: str,
    ) -> dict[str, Any]:
        """通过共享 LangChain 入口调用兼容模型并解析完整 JSON 对象。

        Args:
            model: 服务端模型名称。
            system_prompt: 限定模型职责和输出格式的系统提示词。
            user_content: 纯文本或由文本、图片组成的多模态用户消息。
            request_id: 当前解读请求标识。
            stage: 用于安全日志区分转录和最终解读的阶段名。

        Returns:
            模型消息中的 JSON 对象。

        Raises:
            DocumentInterpretationError: 网络、HTTP、超时或 JSON 结构异常时抛出。
        """

        try:
            return complete_json(
                base_url=self.settings.llm_base_url,
                api_key=self.settings.llm_api_key,
                model=model,
                system_prompt=system_prompt,
                user_content=user_content,
                timeout=self.settings.llm_timeout_seconds,
                max_tokens=max(
                    self.settings.llm_max_output_tokens,
                    self.settings.medical_document_max_output_tokens,
                ),
                enable_thinking=self.settings.llm_enable_thinking,
                request_id=request_id,
                stage=stage,
                structured_method=self.settings.llm_structured_method,
            )
        except ModelCallError as error:
            LOGGER.warning(
                "[病历解读][LLM失败] request_id=%s stage=%s error=%s",
                request_id, stage, error,
            )
            raise DocumentInterpretationError(error.status_code, str(error)) from error

    def _parse_json_object(self, content: str) -> dict[str, Any]:
        """通过共享完整性校验解析模型 JSON，拒绝截断的内层对象。

        Args:
            content: 模型返回文本。

        Returns:
            完整的顶层 JSON 对象。
        """
        return parse_complete_json(content)

    def _format_evidence(self, response: ResearchSearchResponse) -> str:
        """把本地混合检索结果格式化为带固定编号的上下文。

        Args:
            response: RAG 检索与精排结果。

        Returns:
            供模型引用的证据文本。
        """

        return "\n\n".join(
            f"[S{index}] 标题：{item.title}\n来源：{item.source}\n正文：{item.excerpt}"
            for index, item in enumerate(response.results, start=1)
        )

    def _build_evidence(self, response: ResearchSearchResponse) -> list[MedicalDocumentEvidence]:
        """把研究检索结果转换为病历解读证据卡片。

        Args:
            response: RAG 检索与精排结果。

        Returns:
            顺序稳定的前端证据对象列表。
        """

        return [
            MedicalDocumentEvidence(
                marker=f"S{index}",
                title=item.title,
                excerpt=item.excerpt,
                source=item.source,
                source_type=item.source_type,
                trust_level=item.trust_level,
                source_url=item.source_url,
            )
            for index, item in enumerate(response.results, start=1)
        ]

    def _parse_findings(self, value: Any, request_id: str) -> list[MedicalDocumentFinding]:
        """逐项校验模型关键发现，忽略单个损坏项而不让整次解读失败。

        Args:
            value: 模型返回的 findings 字段。
            request_id: 当前解读请求标识。

        Returns:
            通过接口模型校验的关键发现；没有有效项时返回空列表。
        """

        if not isinstance(value, list):
            return []
        findings: list[MedicalDocumentFinding] = []
        invalid_count = 0
        for item in value[:20]:
            try:
                findings.append(MedicalDocumentFinding.model_validate(item))
            except ValidationError:
                invalid_count += 1
        if invalid_count:
            LOGGER.warning(
                "[病历解读][字段降级] request_id=%s field=findings ignored=%s",
                request_id,
                invalid_count,
            )
        return findings

    def _parse_sections(
        self,
        value: Any,
        summary: str,
        request_id: str,
    ) -> list[AnswerSection]:
        """逐项校验解读章节，并在章节缺失时安全复用模型摘要。

        Args:
            value: 模型返回的 sections 字段。
            summary: 同一模型响应中的摘要文本。
            request_id: 当前解读请求标识。

        Returns:
            至少包含一个资料概览的解读章节。
        """

        sections: list[AnswerSection] = []
        invalid_count = 0
        if isinstance(value, list):
            for item in value[:12]:
                try:
                    sections.append(AnswerSection.model_validate(item))
                except ValidationError:
                    invalid_count += 1
        if invalid_count:
            LOGGER.warning(
                "[病历解读][字段降级] request_id=%s field=sections ignored=%s",
                request_id,
                invalid_count,
            )
        if not sections:
            sections.append(AnswerSection(title="资料概览", content=summary))
        return sections

    def _string_list(self, value: Any) -> list[str]:
        """将模型的可选数组安全收敛为非空短文本列表。

        Args:
            value: 模型返回的任意字段值。

        Returns:
            过滤空项并限制长度后的字符串列表。
        """

        if not isinstance(value, list):
            return []
        return [str(item).strip()[:500] for item in value if str(item).strip()][:12]

    def _ensure_limitations(
        self,
        value: Any,
        document: ExtractedMedicalDocument,
    ) -> list[str]:
        """为模型限制说明补充不会遗漏的产品安全边界。

        Args:
            value: 模型返回的限制数组。
            document: 当前资料及其提取模式。

        Returns:
            至少包含非诊断和图片非阅片边界的限制列表。
        """

        limitations = self._string_list(value)
        mandatory = ["本解读基于上传资料中可识别的文字，不构成诊断或治疗建议。"]
        if document.extraction_mode == "vision":
            mandatory.append("视觉模型可能漏读小字、单位或表格；请以医院原报告和医生解释为准。")
        for item in mandatory:
            if item not in limitations:
                limitations.append(item)
        return limitations

    def _normalize_urgency(self, value: Any) -> str:
        """将模型紧急程度限制在接口允许枚举内。

        Args:
            value: 模型返回的紧急程度。

        Returns:
            routine、attention、urgent 或 insufficient。
        """

        normalized = str(value or "insufficient").lower()
        return normalized if normalized in {"routine", "attention", "urgent", "insufficient"} else "insufficient"


def create_document_request_id() -> str:
    """生成不含用户身份信息的病历解读请求标识。

    Returns:
        十二位十六进制请求标识。
    """

    return uuid.uuid4().hex[:12]
