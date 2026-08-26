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

export type WorkspaceKey = 'consult' | 'atlas' | 'research' | 'knowledge' | 'monitor'

export interface WorkspaceMenuItem {
  key: WorkspaceKey
  label: string
  description: string
  index: string
}

export interface ResearchSearchForm {
  query: string
  top_k: number
}

export interface ResearchEvidence {
  id: string
  title: string
  question: string
  excerpt: string
  source: string
  source_type: string
  trust_level: string
  source_url: string | null
  allow_treatment_generation: boolean
  bm25_score: number
  vector_score: number
  rrf_score: number
  rerank_score: number
}

export interface ResearchSearchResponse {
  request_id: string
  query: string
  total: number
  results: ResearchEvidence[]
  retrieval_mode: string
  duration_ms: number
}

export interface AtlasOrgan {
  id: string
  name: string
  summary: string
  observation: string
  mesh_aliases: string[]
  symptom_options: AtlasSymptomOption[]
  available_models: AnatomyModelId[]
}

export interface AtlasSymptomOption {
  id: string
  label: string
  query_text: string
}

export interface AtlasBodyRegion {
  id: string
  name: string
  english_name: string
  group: string
  side: 'left' | 'right' | 'middle' | 'bilateral'
  system_id: string
  location: string
  summary: string
  mesh_aliases: string[]
  symptom_options: AtlasSymptomOption[]
}

export interface AtlasComplaintSelection {
  region_id: string
  region_name: string
  structure_label: string
  symptoms: AtlasSymptomOption[]
  description: string
}

export interface AtlasSystem {
  id: string
  name: string
  english_name: string
  color: string
  summary: string
  organs: AtlasOrgan[]
  available_models: AnatomyModelId[]
}

export type AnatomyModelId = 'male' | 'female'

export interface AtlasModelProfile {
  id: AnatomyModelId
  name: string
  english_name: string
  description: string
  coverage: string
  structure_count: number
  available_system_ids: string[]
}

export interface AtlasConsultContext {
  anatomy_model: AnatomyModelId
  system_id: string
  system_name: string
  organ_id: string
  organ_name: string
  organ_summary: string
  observation: string
  complaints: AtlasComplaintSelection[]
}

export interface BodyAtlasResponse {
  title: string
  description: string
  systems: AtlasSystem[]
  body_regions: AtlasBodyRegion[]
  models: AtlasModelProfile[]
  default_model: AnatomyModelId
  disclaimer: string
}
