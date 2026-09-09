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

export type WorkspaceKey = 'consult' | 'atlas' | 'records' | 'research' | 'knowledge' | 'monitor' | 'chat'

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

export type MedicalDocumentType =
  | 'outpatient_record'
  | 'discharge_record'
  | 'laboratory_report'
  | 'ultrasound_report'
  | 'imaging_report'
  | 'pathology_report'
  | 'other'

export interface MedicalDocumentFinding {
  name: string
  original_text: string
  explanation: string
  level: 'normal' | 'attention' | 'urgent' | 'uncertain'
}

export interface MedicalDocumentEvidence {
  marker: string
  title: string
  excerpt: string
  source: string
  source_type: string
  trust_level: string
  source_url: string | null
}

export interface MedicalDocumentInterpretationResponse {
  request_id: string
  file_name: string
  document_type: string
  extraction_mode: 'text' | 'vision'
  title: string
  summary: string
  urgency: 'routine' | 'attention' | 'urgent' | 'insufficient'
  findings: MedicalDocumentFinding[]
  sections: AnswerSection[]
  red_flags: string[]
  questions_for_doctor: string[]
  limitations: string[]
  evidence: MedicalDocumentEvidence[]
  retrieval_mode: string
  generation_model: string
  privacy_notice: string
  disclaimer: string
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
  department_ids: string[]
}

export interface AtlasSymptomOption {
  id: string
  label: string
  query_text: string
  department_ids: string[]
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
  department_ids: string[]
}

export interface AtlasDepartment {
  id: string
  official_code: string
  name: string
  english_name: string
  group: string
  summary: string
  common_reasons: string[]
  target_system_id: string
  target_organ_id: string | null
  focus_aliases: string[]
  preferred_model: AnatomyModelId | null
}

export interface AtlasComplaintSelection {
  region_id: string
  region_name: string
  structure_label: string
  symptoms: AtlasSymptomOption[]
  description: string
  department_ids: string[]
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
  suggested_departments: string[]
}

export interface BodyAtlasResponse {
  title: string
  description: string
  systems: AtlasSystem[]
  departments: AtlasDepartment[]
  body_regions: AtlasBodyRegion[]
  models: AtlasModelProfile[]
  default_model: AnatomyModelId
  disclaimer: string
}
