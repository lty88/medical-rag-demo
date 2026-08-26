import type {
  AtlasConsultContext,
  ConsultationFormState,
  ConsultationResponse,
  BodyAtlasResponse,
  KnowledgeStats,
  ResearchSearchForm,
  ResearchSearchResponse,
} from '../types'

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

/**
 * 拼接本地代理或生产后端的 API 请求地址。
 * @param path 以斜杠开头的后端接口路径
 * @returns 可直接交给 fetch 的完整或同源地址
 */
function apiUrl(path: string): string {
  return `${apiBaseUrl}${path}`
}

/**
 * 从失败响应中提取可读错误信息。
 * @param response HTTP 响应对象
 * @returns 后端错误详情或通用错误说明
 */
async function readError(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: string | Array<{ msg: string }> }
    if (typeof data.detail === 'string') return data.detail
    if (Array.isArray(data.detail)) return data.detail.map((item) => item.msg).join('；')
  } catch {
    // 失败响应不一定是 JSON，继续返回统一说明。
  }
  return `请求失败（${response.status}）`
}

/**
 * 提交症状和人群信息，执行完整安全检索链路。
 * @param form 用户填写的咨询表单
 * @param visualContext 健康可视化选中的系统与器官导航上下文
 * @returns 后端结构化咨询响应
 */
export async function submitConsultation(
  form: ConsultationFormState,
  visualContext: AtlasConsultContext | null = null,
): Promise<ConsultationResponse> {
  const payload = {
    ...form,
    duration: form.duration || null,
    temperature: form.temperature || null,
    additional_info: form.additional_info || null,
    visual_context: visualContext
      ? { source: 'health_atlas', ...visualContext }
      : null,
  }
  const response = await fetch(apiUrl('/api/consult'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) throw new Error(await readError(response))
  return (await response.json()) as ConsultationResponse
}

/**
 * 获取当前知识库、向量检索和精排模式。
 * @returns 后端启动时加载的知识库统计
 */
export async function fetchKnowledgeStats(): Promise<KnowledgeStats> {
  const response = await fetch(apiUrl('/api/knowledge/stats'))
  if (!response.ok) throw new Error(await readError(response))
  return (await response.json()) as KnowledgeStats
}

/**
 * 获取人体系统与器官的健康科普图谱。
 * @returns 用于可视化交互的人体系统数据
 */
export async function fetchBodyAtlas(): Promise<BodyAtlasResponse> {
  const response = await fetch(apiUrl('/api/atlas/body'))
  if (!response.ok) throw new Error(await readError(response))
  return (await response.json()) as BodyAtlasResponse
}

/**
 * 执行不触发 LLM 生成的独立医疗证据检索。
 * @param form 检索问题与结果数量
 * @returns 混合召回和医疗精排后的证据列表
 */
export async function searchResearchEvidence(
  form: ResearchSearchForm,
): Promise<ResearchSearchResponse> {
  const response = await fetch(apiUrl('/api/research/search'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(form),
  })
  if (!response.ok) throw new Error(await readError(response))
  return (await response.json()) as ResearchSearchResponse
}
