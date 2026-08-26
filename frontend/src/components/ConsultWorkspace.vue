<script setup lang="tsx">
import ConsultationForm from './ConsultationForm.vue'
import EvidencePanel from './EvidencePanel.vue'
import PipelineTrace from './PipelineTrace.vue'
import ResultPanel from './ResultPanel.vue'
import type {
  AtlasConsultContext,
  ConsultationFormState,
  ConsultationResponse,
  KnowledgeStats,
} from '../types'

defineProps<{
  loading: boolean
  error: string
  result: ConsultationResponse | null
  stats: KnowledgeStats | null
  draft: ConsultationFormState
  atlasContext: AtlasConsultContext | null
}>()

const emit = defineEmits<{
  submit: [form: ConsultationFormState]
  updateDraft: [form: ConsultationFormState]
  clearAtlasContext: []
  openResearch: []
}>()

/**
 * 转发咨询表单快照给应用壳执行后端请求。
 * @param form 症状与基础人群信息
 */
function submitConsultation(form: ConsultationFormState) {
  emit('submit', form)
}

/**
 * 将表单编辑后的草稿同步给应用壳，以便跨工作区保留。
 * @param form 当前问诊表单快照
 */
function updateConsultationDraft(form: ConsultationFormState) {
  emit('updateDraft', form)
}

/**
 * 通知应用壳移除当前健康可视化导航上下文。
 */
function clearAtlasContext() {
  emit('clearAtlasContext')
}
</script>

<template>
  <section class="consult-workspace">
    <header class="workspace-hero consult-hero">
      <div>
        <p class="science-kicker">EVIDENCE-GROUNDED MEDICAL AGENT</p>
        <h2>让每一个健康问题，<br /><em>先经过证据与安全。</em></h2>
        <p>系统先完成急症分诊，再执行百万级混合检索、医疗精排和受证据约束的模型生成。</p>
      </div>
      <div class="hero-runtime-orb">
        <span>RAG</span>
        <i />
        <small>{{ stats?.llm_model ?? 'EVIDENCE MODE' }}</small>
      </div>
    </header>

    <div class="capability-strip">
      <span><b>01</b> 隐私脱敏</span>
      <span><b>02</b> 急症前置</span>
      <span><b>03</b> 双路召回</span>
      <span><b>04</b> 医疗精排</span>
      <span><b>05</b> 引用校验</span>
    </div>

    <div class="consult-grid">
      <ConsultationForm
        :loading="loading"
        :initial-draft="draft"
        :atlas-context="atlasContext"
        @submit="submitConsultation"
        @update-draft="updateConsultationDraft"
        @clear-atlas-context="clearAtlasContext"
      />
      <div class="consult-output">
        <div v-if="error" class="request-error" role="alert">
          <strong>链路未完成</strong>
          <span>{{ error }}</span>
        </div>

        <section v-if="loading" class="panel generation-loading" aria-live="polite">
          <div class="generation-pulse" aria-hidden="true"><span /></div>
          <p class="science-kicker">RETRIEVE · RERANK · GENERATE</p>
          <h2>正在组织有出处的回答</h2>
          <p>系统正在执行双路召回、医疗精排和生成后校验。</p>
          <div class="loading-track"><span /></div>
        </section>

        <template v-else-if="result">
          <ResultPanel :result="result" />
          <div class="consult-detail-grid">
            <PipelineTrace :steps="result.pipeline" />
            <EvidencePanel
              :citations="result.citations"
              :generation-mode="result.generation_mode"
            />
          </div>
        </template>

        <section v-else class="panel assistant-ready">
          <span class="assistant-cross" aria-hidden="true">✦</span>
          <p class="science-kicker">UNIFIED HEALTH CONVERSATION</p>
          <h3>今天想了解什么健康问题？</h3>
          <p>描述起病时间、部位、严重程度和伴随表现，会获得更准确的检索证据。</p>
          <div class="ready-actions">
            <button type="button" @click="emit('openResearch')">先查证据库</button>
            <span>当前仅处理本次输入，不建立个人病历。</span>
          </div>
        </section>
      </div>
    </div>
  </section>
</template>
