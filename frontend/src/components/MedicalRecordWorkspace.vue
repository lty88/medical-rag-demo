<script setup lang="tsx">
import { computed, ref } from 'vue'
import { interpretMedicalDocument } from '../api/client'
import type {
  MedicalDocumentInterpretationResponse,
  MedicalDocumentType,
} from '../types'
import MedicalDocumentResult from './MedicalDocumentResult.vue'
import MedicalDocumentUploader from './MedicalDocumentUploader.vue'

const documentType = ref<MedicalDocumentType>('ultrasound_report')
const selectedFile = ref<File | null>(null)
const symptomDescription = ref('')
const interpretationFocus = ref('')
const consent = ref(false)
const loading = ref(false)
const error = ref('')
const result = ref<MedicalDocumentInterpretationResponse | null>(null)

const documentTypes: Array<{ value: MedicalDocumentType; label: string; description: string }> = [
  { value: 'outpatient_record', label: '门诊病历', description: '主诉、诊断与医嘱文字' },
  { value: 'discharge_record', label: '出院记录', description: '住院经过与出院安排' },
  { value: 'laboratory_report', label: '检验报告', description: '血液、尿液及生化指标' },
  { value: 'ultrasound_report', label: '超声 / B 超', description: '彩超、B 超报告或截图' },
  { value: 'imaging_report', label: '影像报告', description: 'CT、MRI、X 光报告文字' },
  { value: 'pathology_report', label: '病理报告', description: '组织学结论与描述' },
  { value: 'other', label: '其他资料', description: '其他可读医疗文档' },
]

const focusOptions = ['先看异常项', '解释医学术语', '准备复诊问题', '结合症状理解']

const canSubmit = computed(
  () => Boolean(selectedFile.value && consent.value && !loading.value),
)

/**
 * 保存用户选择的医疗资料并清除上一条错误。
 * @param file 通过上传组件基础校验的文件
 */
function selectFile(file: File) {
  selectedFile.value = file
  error.value = ''
}

/**
 * 移除当前文件并清空已有解读结果。
 */
function clearFile() {
  selectedFile.value = null
  result.value = null
}

/**
 * 使用预设目标快速填写解读重点。
 * @param focus 用户希望优先理解的内容
 */
function applyFocus(focus: string) {
  interpretationFocus.value = interpretationFocus.value === focus ? '' : focus
}

/**
 * 上传文件并触发后端文字提取、本地 RAG 和结构化 LLM 解读。
 * 请求期间会更新加载状态、错误信息和当前结果。
 */
async function submitInterpretation() {
  const file = selectedFile.value
  if (!file || !consent.value) return
  loading.value = true
  error.value = ''
  result.value = null
  try {
    result.value = await interpretMedicalDocument(
      file,
      documentType.value,
      symptomDescription.value.trim(),
      interpretationFocus.value.trim(),
    )
  } catch (requestError) {
    error.value = requestError instanceof Error ? requestError.message : '资料解读失败，请稍后再试。'
  } finally {
    loading.value = false
  }
}

/**
 * 恢复为空白上传状态，同时保留用户已经阅读过的授权选择。
 */
function resetWorkspace() {
  selectedFile.value = null
  symptomDescription.value = ''
  interpretationFocus.value = ''
  result.value = null
  error.value = ''
}
</script>

<template>
  <section class="medical-record-workspace">
    <header class="workspace-hero medical-record-hero">
      <div>
        <p class="science-kicker">MEDICAL DOCUMENT INTERPRETATION</p>
        <h2>读懂报告，<em>准备下一次就医沟通</em></h2>
        <p>提取病历、检验和影像报告中的文字，结合可选症状与本地医学证据，区分报告原文、通俗解释、风险提示和仍需医生确认的问题。</p>
      </div>
      <div class="document-orbit" aria-hidden="true"><span>AI</span><i /><i /><b>REPORT</b></div>
    </header>

    <div v-if="!result" class="medical-record-layout">
      <form class="medical-record-form" @submit.prevent="submitInterpretation">
        <section class="record-form-section">
          <header><div><span>01</span><h3>选择资料类型</h3></div><small>用于选择更合适的解读框架</small></header>
          <div class="document-type-grid">
            <button
              v-for="item in documentTypes"
              :key="item.value"
              type="button"
              :class="{ active: documentType === item.value }"
              @click="documentType = item.value"
            >
              <strong>{{ item.label }}</strong><small>{{ item.description }}</small>
            </button>
          </div>
        </section>

        <section class="record-form-section">
          <header><div><span>02</span><h3>上传一份医疗资料</h3></div><small>建议先遮盖姓名、身份证号、住址、电话与二维码</small></header>
          <MedicalDocumentUploader :file="selectedFile" @select="selectFile" @clear="clearFile" />
        </section>

        <section class="record-form-section">
          <header><div><span>03</span><h3>补充临床背景</h3></div><small>选填，但有助于避免脱离场景解释</small></header>
          <label class="medical-context-field">
            <span>症状与经过（选填）</span>
            <textarea
              v-model="symptomDescription"
              rows="4"
              maxlength="2000"
              placeholder="例如：右上腹间歇不适 2 周，无发热；这份报告是昨天复查的……"
            />
            <small>{{ symptomDescription.length }} / 2000 · 不要填写姓名、证件号和联系方式</small>
          </label>
          <div class="interpretation-focus-field">
            <span>我最想了解</span>
            <div>
              <button v-for="focus in focusOptions" :key="focus" type="button" :class="{ active: interpretationFocus === focus }" @click="applyFocus(focus)">{{ focus }}</button>
            </div>
          </div>
        </section>

        <section class="record-consent-card">
          <div><span>!</span><p><strong>敏感医疗信息授权</strong>医疗健康信息属于敏感个人信息。文档文字会先做常见身份字段脱敏；图片为了识别文字会发送给你配置的视觉模型，因此仍应在上传前遮盖身份信息。</p></div>
          <label><input v-model="consent" type="checkbox" /><span>我上传的是本人资料或已获合法授权，并单独同意为本次辅助解读处理该医疗资料。</span></label>
        </section>

        <p v-if="error" class="medical-record-error"><strong>暂时无法解读</strong>{{ error }}</p>

        <button class="medical-interpret-button" type="submit" :disabled="!canSubmit">
          <span>{{ loading ? '正在提取文字、检索证据并生成解读…' : '开始安全解读' }}</span><b>{{ loading ? 'PROCESSING' : 'INTERPRET →' }}</b>
        </button>
      </form>

      <aside class="medical-record-boundary">
        <p class="science-kicker">CAPABILITY & BOUNDARY</p>
        <h3>系统能做什么</h3>
        <ol>
          <li><span>01</span><div><strong>识别资料文字</strong><p>读取文字型 PDF、文本和清晰报告截图中的项目、数值、所见与结论。</p></div></li>
          <li><span>02</span><div><strong>标记关键内容</strong><p>把报告中的异常、需关注和不确定项分开，不用“正常”掩盖疑问。</p></div></li>
          <li><span>03</span><div><strong>结合本地证据</strong><p>用 BM25、FAISS、RRF 与医疗 Reranker 检索相关资料，再交给模型组织解读。</p></div></li>
          <li><span>04</span><div><strong>准备就医问题</strong><p>把仍需结合病史、查体或复查确认的内容整理成可直接问医生的问题。</p></div></li>
        </ol>
        <div class="raw-image-boundary">
          <span>NOT A RADIOLOGY WORKSTATION</span>
          <strong>不接受 DICOM 或动态超声视频作为自动诊断依据</strong>
          <p>原始 CT、MRI、X 光、B 超切面需要合格的影像科或超声科医生结合完整序列阅片。本功能只解释可读报告文字，不声称替代专业阅片。</p>
        </div>
        <div class="record-process-track"><i>上传</i><b>→</b><i>提取</i><b>→</b><i>脱敏</i><b>→</b><i>检索</i><b>→</b><i>解读</i></div>
      </aside>
    </div>

    <MedicalDocumentResult v-else :result="result" @reset="resetWorkspace" />
  </section>
</template>
