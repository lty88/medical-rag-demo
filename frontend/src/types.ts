export type Sex = 'female' | 'male' | 'other' | 'unknown'

export interface ConsultationFormState {
  symptoms: string
  age: number
  sex: Sex
  pregnant: boolean
  region: string
  duration: string
  temperature: number | null
  additional_info: string
}

export interface AnswerSection {
  title: string
  content: string
}

export interface AnswerContentPart {
  value: string
  marker: string | null
}

export interface Citation {
  marker: string
  title: string
  source: string
  source_url: string | null
  trust_level: string
  excerpt: string
  allow_treatment_generation: boolean
}

export interface PipelineStep {
  key: string
  label: string
  status: 'pending' | 'running' | 'passed' | 'blocked' | 'fallback'
  detail: string
  duration_ms: number
}

export interface ConsultationResponse {
  request_id: string
  urgency: 'emergency' | 'urgent' | 'routine' | 'insufficient'
  blocked: boolean
  title: string
  summary: string
  sections: AnswerSection[]
  red_flags: string[]
  follow_up_questions: string[]
  structured_symptoms: Record<string, unknown>
  citations: Citation[]
  pipeline: PipelineStep[]
  validation_issues: string[]
  retrieval_mode: string
  generation_mode: 'configured-llm' | 'evidence-template' | 'not-run'
  generation_model: string | null
  privacy_notice: string
  disclaimer: string
}

export interface KnowledgeStats {
  total_documents: number
  keyword_document_count: number
  vector_document_count: number
  source_counts: Record<string, number>
  trust_counts: Record<string, number>
  vector_mode: string
  embedding_model: string | null
  vector_index_ready: boolean
  reranker_mode: string
  reranker_model: string | null
  llm_ready: boolean
  llm_model: string | null
  capped: boolean
}

export interface ScenarioPreset {
  label: string
  description: string
  value: Partial<ConsultationFormState>
}
