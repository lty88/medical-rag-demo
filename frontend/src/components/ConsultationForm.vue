<script setup lang="tsx">
import { ref, watch } from 'vue'
import type { AtlasConsultContext, ConsultationFormState, ScenarioPreset } from '../types'

const props = defineProps<{
  loading: boolean
  initialDraft: ConsultationFormState
  atlasContext: AtlasConsultContext | null
}>()
const emit = defineEmits<{
  submit: [form: ConsultationFormState]
  updateDraft: [form: ConsultationFormState]
  clearAtlasContext: []
}>()

const scenarios: ScenarioPreset[] = [
  { label: '空腹腹痛', description: '常见症状检索', value: { symptoms: '饿了就上腹部疼，吃点东西后会缓解，已经一周。', age: 28, sex: 'male', pregnant: false, duration: '一周' } },
  { label: '咳嗽血痰', description: '观察分诊规则', value: { symptoms: '咳嗽两天，今天痰里出现鲜红色血丝，想知道要注意什么。', age: 30, sex: 'male', pregnant: false, duration: '2天' } },
  { label: '用药咨询', description: '观察权限校验', value: { symptoms: '怀孕12周，发热一天，应该吃什么药、用多少剂量？', age: 31, sex: 'female', pregnant: true, duration: '1天', temperature: 38.2 } },
]

const form = ref<ConsultationFormState>({ ...props.initialDraft })
const profileExpanded = ref(false)

/**
 * 将表单每次编辑后的快照同步到父级，供工作区切换时恢复。
 * @param value 当前问诊表单内容
 */
function publishDraft(value: ConsultationFormState) {
  emit('updateDraft', { ...value })
}

watch(form, publishDraft, { deep: true })

/**
 * 使用预设医学场景更新当前咨询表单。
 * @param scenario 包含症状与人群信息的预设场景
 */
function applyScenario(scenario: ScenarioPreset) {
  form.value = { ...form.value, ...scenario.value }
}

/**
 * 展开或收起影响医学判断的人群资料字段。
 */
function toggleProfile() {
  profileExpanded.value = !profileExpanded.value
}

/**
 * 提交当前表单快照，避免后续编辑影响正在处理的请求。
 */
function handleSubmit() {
  emit('submit', { ...form.value })
}

/**
 * 检查用户是否已在图谱引导语之后补充真实症状。
 * @returns 当前症状文本是否足以提交问诊
 */
function hasUsableSymptoms() {
  const symptoms = form.value.symptoms.trim()
  return Boolean(symptoms) && !/^我想咨询与“.+”相关的不适：$/.test(symptoms)
}

/**
 * 移除图谱导航上下文，同时保留用户已经输入的症状内容。
 */
function clearAtlasContext() {
  emit('clearAtlasContext')
}
</script>

<template>
  <section class="consult-composer panel">
    <header class="composer-heading">
      <div><span>CONSULTATION INPUT</span><h3>描述当前健康问题</h3></div>
      <span class="privacy-chip">先脱敏 · 后处理</span>
    </header>

    <section v-if="atlasContext" class="atlas-consult-context" aria-label="健康可视化带入信息">
      <div>
        <span>来自健康可视化</span>
        <strong>{{ atlasContext.system_name }} / {{ atlasContext.organ_name }}</strong>
      </div>
      <p>已带入器官导航线索。它不会被当作你的真实症状，请在下方补充实际不适。</p>
      <ul v-if="atlasContext.complaints.length">
        <li v-for="complaint in atlasContext.complaints" :key="complaint.region_id">
          <b>{{ complaint.region_name }}</b>
          <span>
            {{ [
              complaint.symptoms.map((symptom) => symptom.label).join('、'),
              complaint.description,
            ].filter(Boolean).join('；') }}
          </span>
        </li>
      </ul>
      <button type="button" @click="clearAtlasContext">移除该导航上下文</button>
    </section>

    <div class="scenario-pills">
      <button v-for="scenario in scenarios" :key="scenario.label" type="button" @click="applyScenario(scenario)">
        <strong>{{ scenario.label }}</strong><small>{{ scenario.description }}</small>
      </button>
    </div>

    <form @submit.prevent="handleSubmit">
      <label class="composer-textarea">
        <span>症状描述 <b>REQUIRED</b></span>
        <textarea
          v-model.trim="form.symptoms"
          rows="7"
          minlength="2"
          maxlength="2000"
          required
          :autofocus="Boolean(atlasContext)"
          placeholder="从什么时候开始？哪里不舒服？严重程度如何？有没有伴随症状？"
        />
        <small>{{ form.symptoms.length }} / 2000</small>
      </label>

      <button class="profile-toggle" type="button" @click="toggleProfile">
        <span><b>人群条件</b><small>年龄、性别、持续时间会参与证据过滤</small></span>
        <i>{{ profileExpanded ? '−' : '+' }}</i>
      </button>

      <div v-if="profileExpanded" class="profile-fields">
        <label><span>年龄</span><input v-model.number="form.age" type="number" min="0" max="120" step="0.1" required /></label>
        <label><span>性别</span><select v-model="form.sex"><option value="unknown">未说明</option><option value="female">女</option><option value="male">男</option><option value="other">其他</option></select></label>
        <label><span>持续时间</span><input v-model.trim="form.duration" maxlength="100" placeholder="例如：2天" /></label>
        <label><span>体温 ℃</span><input v-model.number="form.temperature" type="number" min="30" max="45" step="0.1" placeholder="可选" /></label>
        <label><span>地区</span><select v-model="form.region"><option value="CN">中国大陆</option><option value="GLOBAL">其他地区</option></select></label>
        <label class="pregnancy-field" :class="{ disabled: form.sex === 'male' }"><input v-model="form.pregnant" type="checkbox" :disabled="form.sex === 'male'" /><span>处于孕期</span></label>
      </div>

      <label class="additional-field"><span>病史 / 过敏 / 正在使用的药物</span><textarea v-model.trim="form.additional_info" rows="2" maxlength="1000" placeholder="选填，但用药问题建议补充" /></label>

      <div class="composer-footer">
        <span><i /> 急症危险信号将在检索前检查</span>
        <button type="submit" :disabled="loading || !hasUsableSymptoms()">
          {{ loading ? '安全链路处理中…' : '开始证据问诊' }} <b>→</b>
        </button>
      </div>
    </form>
  </section>
</template>
