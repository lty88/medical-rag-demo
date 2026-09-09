<script setup lang="tsx">
import { computed, onMounted, ref } from 'vue'
import { fetchBodyAtlas, fetchKnowledgeStats, submitConsultation } from './api/client'
import AppSidebar from './components/AppSidebar.vue'
import ConsultWorkspace from './components/ConsultWorkspace.vue'
import EvidenceSearch from './components/EvidenceSearch.vue'
import FreeChatWorkspace from './components/FreeChatWorkspace.vue'
import HealthAtlas from './components/HealthAtlas.vue'
import KnowledgeWorkspace from './components/KnowledgeWorkspace.vue'
import MedicalRecordWorkspace from './components/MedicalRecordWorkspace.vue'
import ScientificCanvas from './components/ScientificCanvas.vue'
import SystemMonitor from './components/SystemMonitor.vue'
import type {
  AtlasConsultContext,
  BodyAtlasResponse,
  ConsultationFormState,
  ConsultationResponse,
  KnowledgeStats,
  WorkspaceKey,
  WorkspaceMenuItem,
} from './types'

const menuItems: WorkspaceMenuItem[] = [
  { key: 'consult', label: '智能问诊', description: '证据约束会话', index: '01' },
  { key: 'atlas', label: '健康可视化', description: '人体系统图谱', index: '02' },
  { key: 'records', label: '报告解读', description: '病历与检查资料', index: '03' },
  { key: 'research', label: '证据检索', description: '独立混合召回', index: '04' },
  { key: 'knowledge', label: '知识资产', description: '语料与权限', index: '05' },
  { key: 'monitor', label: '运行监测', description: '模型与索引', index: '06' },
  { key: 'chat', label: '自由对话', description: 'LLM · 短期记忆', index: '07' },
]

const activeWorkspace = ref<WorkspaceKey>('consult')
const loading = ref(false)
const error = ref('')
const result = ref<ConsultationResponse | null>(null)
const stats = ref<KnowledgeStats | null>(null)
const atlas = ref<BodyAtlasResponse | null>(null)
const consultDraft = ref<ConsultationFormState>(createInitialConsultationDraft())
const consultContext = ref<AtlasConsultContext | null>(null)
const atlasGeneratedPrompt = ref('')

const activeMenu = computed(
  () => menuItems.find((item) => item.key === activeWorkspace.value) ?? menuItems[0],
)

/**
 * 创建可跨工作区保留的初始问诊草稿。
 * @returns 包含默认人群条件的空白问诊表单
 */
function createInitialConsultationDraft(): ConsultationFormState {
  return {
    symptoms: '',
    age: 30,
    sex: 'unknown',
    pregnant: false,
    region: 'CN',
    duration: '',
    temperature: null,
    additional_info: '',
  }
}

/**
 * 并行读取知识库运行状态与人体系统图谱。
 */
async function loadWorkspaceData() {
  const [statsResult, atlasResult] = await Promise.allSettled([
    fetchKnowledgeStats(),
    fetchBodyAtlas(),
  ])
  stats.value = statsResult.status === 'fulfilled' ? statsResult.value : null
  atlas.value = atlasResult.status === 'fulfilled' ? atlasResult.value : null
}

/**
 * 切换一级工作区并清理跨页面错误提示。
 * @param workspace 要打开的工作区标识
 */
function changeWorkspace(workspace: WorkspaceKey) {
  activeWorkspace.value = workspace
  error.value = ''
}

/**
 * 保存问诊组件最新草稿，使页面切换后仍可继续填写。
 * @param draft 当前问诊表单快照
 */
function updateConsultDraft(draft: ConsultationFormState) {
  consultDraft.value = draft
}

/**
 * 清除健康可视化导航上下文，不改变用户已经填写的症状。
 */
function clearConsultContext() {
  consultContext.value = null
}

/**
 * 判断症状文本是否仍是系统生成、尚未补充的图谱引导语。
 * @param symptoms 当前症状文本
 * @returns 文本是否可由新的图谱选择安全替换
 */
function isAtlasPrompt(symptoms: string) {
  const normalized = symptoms.trim()
  return /^我想咨询与“.+”相关的不适：$/.test(normalized)
    || normalized === atlasGeneratedPrompt.value
}

/**
 * 把图谱中多部位、多症状选择转换为自然的问诊描述。
 * @param context 健康可视化生成的结构化问诊上下文
 * @returns 可直接继续补充的中文症状描述
 */
function buildAtlasSymptomPrompt(context: AtlasConsultContext) {
  const modelLabel = context.anatomy_model === 'female' ? '女性腹盆躯干图谱' : '男性全身图谱'
  if (!context.complaints.length) {
    return `我通过${modelLabel}选择了“${context.organ_name}”，想咨询相关不适：`
  }
  const descriptions = context.complaints.map((complaint) => {
    const details = [
      complaint.symptoms.map((symptom) => symptom.label).join('、'),
      complaint.description.trim(),
    ].filter(Boolean)
    return `${complaint.region_name}：${details.join('；') || '具体表现待补充'}`
  })
  return `我从${modelLabel}选择了以下不适：${descriptions.join('；')}。`
}

/**
 * 将健康可视化中选定的系统与器官带入智能问诊，并保留用户已有内容。
 * @param context 当前图谱选择形成的问诊导航上下文
 */
function startConsultFromAtlas(context: AtlasConsultContext) {
  const currentSymptoms = consultDraft.value.symptoms.trim()
  const shouldPrefill = !currentSymptoms || isAtlasPrompt(currentSymptoms)
  const nextPrompt = buildAtlasSymptomPrompt(context)
  consultContext.value = context
  atlasGeneratedPrompt.value = nextPrompt
  consultDraft.value = {
    ...consultDraft.value,
    symptoms: shouldPrefill
      ? nextPrompt
      : consultDraft.value.symptoms,
  }
  result.value = null
  changeWorkspace('consult')
}

/**
 * 提交问诊资料并保存完整 RAG 安全链路响应。
 * @param form 用户填写的症状和基础人群信息
 */
async function handleConsult(form: ConsultationFormState) {
  loading.value = true
  error.value = ''
  result.value = null
  try {
    result.value = await submitConsultation(form, consultContext.value)
  } catch (requestError) {
    error.value = requestError instanceof Error ? requestError.message : '请求失败，请检查后端服务。'
  } finally {
    loading.value = false
  }
}

onMounted(loadWorkspaceData)
</script>

<template>
  <main class="med-app-shell">
    <AppSidebar
      :active="activeWorkspace"
      :items="menuItems"
      :stats="stats"
      @change="changeWorkspace"
    />

    <section class="med-app-main">
      <ScientificCanvas :mode="activeWorkspace" />
      <header class="med-topbar">
        <div>
          <span class="topbar-index">{{ activeMenu.index }}</span>
          <div>
            <strong>{{ activeMenu.label }}</strong>
            <small>{{ activeMenu.description }}</small>
          </div>
        </div>
        <div class="topbar-actions">
          <span :class="['service-state', { offline: !stats }]">
            <i /> {{ stats ? 'SERVICE ONLINE' : 'SERVICE OFFLINE' }}
          </span>
          <span class="date-chip">MEDICAL RAG · RESEARCH CONSOLE</span>
        </div>
      </header>

      <div class="workspace-stage">
        <ConsultWorkspace
          v-if="activeWorkspace === 'consult'"
          :loading="loading"
          :error="error"
          :result="result"
          :stats="stats"
          :draft="consultDraft"
          :atlas-context="consultContext"
          @submit="handleConsult"
          @update-draft="updateConsultDraft"
          @clear-atlas-context="clearConsultContext"
          @open-research="changeWorkspace('research')"
        />
        <HealthAtlas
          v-else-if="activeWorkspace === 'atlas'"
          :atlas="atlas"
          @start-consult="startConsultFromAtlas"
        />
        <MedicalRecordWorkspace v-else-if="activeWorkspace === 'records'" />
        <EvidenceSearch v-else-if="activeWorkspace === 'research'" />
        <KnowledgeWorkspace
          v-else-if="activeWorkspace === 'knowledge'"
          :stats="stats"
        />
        <SystemMonitor v-else-if="activeWorkspace === 'monitor'" :stats="stats" @refresh="loadWorkspaceData" />
        <FreeChatWorkspace v-show="activeWorkspace === 'chat'" />
      </div>
    </section>
  </main>
</template>
