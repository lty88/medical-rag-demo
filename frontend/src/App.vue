<script setup lang="tsx">
import { onMounted, ref } from 'vue'
import { fetchKnowledgeStats, submitConsultation } from './api/client'
import ArchitectureFlow from './components/ArchitectureFlow.vue'
import ConsultationForm from './components/ConsultationForm.vue'
import EvidencePanel from './components/EvidencePanel.vue'
import PipelineTrace from './components/PipelineTrace.vue'
import ResultPanel from './components/ResultPanel.vue'
import type {
  ConsultationFormState,
  ConsultationResponse,
  KnowledgeStats,
} from './types'

const loading = ref(false)
const error = ref('')
const result = ref<ConsultationResponse | null>(null)
const stats = ref<KnowledgeStats | null>(null)

/**
 * 读取知识库状态，用于页头展示当前检索实现和文档数量。
 */
async function loadStats() {
  try {
    stats.value = await fetchKnowledgeStats()
  } catch {
    stats.value = null
  }
}

/**
 * 提交咨询表单并保存后端返回的完整安全链路结果。
 * @param form 用户当前填写的症状与人群信息
 */
async function handleSubmit(form: ConsultationFormState) {
  loading.value = true
  error.value = ''
  result.value = null
  try {
    result.value = await submitConsultation(form)
  } catch (requestError) {
    error.value = requestError instanceof Error ? requestError.message : '请求失败，请检查后端服务。'
  } finally {
    loading.value = false
  }
}

onMounted(loadStats)
</script>

<template>
  <main>
    <header class="hero">
      <nav class="topbar">
        <a class="brand" href="#">
          <span class="brand-mark">M</span>
          <span>
            <strong>MedRAG Lab</strong>
            <small>中文医疗混合检索台</small>
          </span>
        </a>
        <div class="topbar-status">
          <span class="live-dot" />
          <span v-if="stats">已载入 {{ stats.total_documents.toLocaleString() }} 条文档</span>
          <span v-else>等待后端连接</span>
        </div>
      </nav>

      <div class="hero-grid">
        <div class="hero-copy">
          <p class="hero-kicker">MEDICAL RAG / SAFETY FIRST</p>
          <h1>让每一次回答，<br /><em>先经过安全。</em></h1>
          <p class="hero-description">
            全量中文医疗 Embedding 与 BM25 双路独立召回，再由 RRF、医疗 Reranker 和安全规则共同决定最终证据。
          </p>
          <div class="hero-metrics">
            <div>
              <strong>2</strong>
              <span>路混合召回</span>
            </div>
            <div>
              <strong>6</strong>
              <span>层安全处理</span>
            </div>
            <div>
              <strong>0</strong>
              <span>默认治疗权限</span>
            </div>
          </div>
        </div>

        <aside class="system-card">
          <div class="system-card-header">
            <span>运行配置</span>
            <span class="system-state">{{ stats?.vector_index_ready ? 'FULL HYBRID' : 'INDEX NOT READY' }}</span>
          </div>
          <dl>
            <div>
              <dt>Vector</dt>
              <dd>{{ stats?.vector_mode ?? 'offline' }}</dd>
            </div>
            <div>
              <dt>Reranker</dt>
              <dd>{{ stats?.reranker_mode ?? 'offline' }}</dd>
            </div>
            <div>
              <dt>Generation</dt>
              <dd :class="stats?.llm_ready ? 'safe-value' : 'warning-value'">
                {{ stats?.llm_ready ? `${stats.llm_model} / CONFIGURED` : 'EVIDENCE TEMPLATE' }}
              </dd>
            </div>
            <div>
              <dt>Corpus</dt>
              <dd>{{ stats?.vector_document_count.toLocaleString() ?? 0 }} vectors</dd>
            </div>
            <div>
              <dt>Safety gate</dt>
              <dd class="safe-value">ENABLED</dd>
            </div>
          </dl>
          <p>Huatuo 问答默认仅参与召回，不获得治疗生成权限。</p>
        </aside>
      </div>
    </header>

    <ArchitectureFlow />

    <section class="workspace">
      <ConsultationForm :loading="loading" @submit="handleSubmit" />

      <div class="output-column">
        <div v-if="error" class="request-error" role="alert">
          <strong>无法完成请求</strong>
          <span>{{ error }}</span>
        </div>

        <section v-if="loading" class="panel generation-loading" aria-live="polite">
          <div class="generation-pulse" aria-hidden="true"><span /></div>
          <p class="eyebrow">RETRIEVE · RERANK · GENERATE</p>
          <h2>正在组织有出处的回答</h2>
          <p>系统正在完成双路召回、医疗精排和证据约束生成，请稍候。</p>
          <div class="loading-track"><span /></div>
        </section>

        <template v-else-if="result">
          <ResultPanel :result="result" />
          <div class="detail-grid">
            <PipelineTrace :steps="result.pipeline" />
            <EvidencePanel
              :citations="result.citations"
              :generation-mode="result.generation_mode"
            />
          </div>
        </template>

        <section v-else class="panel empty-output">
          <div class="empty-orbit" aria-hidden="true">
            <span />
          </div>
          <p class="eyebrow">READY FOR TRACE</p>
          <h2>选择一个场景，观察系统如何决策</h2>
          <p>普通咨询会完成全部步骤；急症在分诊处中止；治疗请求会在证据权限校验时被拒绝。</p>
        </section>
      </div>
    </section>

    <footer class="page-footer">
      <span>MedRAG Lab · 全量混合检索</span>
      <span>不是医疗器械，不提供诊断或处方</span>
    </footer>
  </main>
</template>
