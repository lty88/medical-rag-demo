<script setup lang="tsx">
import { ref } from 'vue'
import type { ConsultationFormState, ScenarioPreset } from '../types'

defineProps<{ loading: boolean }>()
const emit = defineEmits<{ submit: [form: ConsultationFormState] }>()

const scenarios: ScenarioPreset[] = [
  {
    label: '普通咨询',
    description: '观察完整检索和引用链路',
    value: {
      symptoms: '头痛两天，休息后稍有缓解，没有肢体无力，想了解还需要观察什么。',
      age: 28,
      sex: 'female',
      pregnant: false,
      duration: '2天',
    },
  },
  {
    label: '急症阻断',
    description: '观察检索前的硬中止',
    value: {
      symptoms: '突然胸痛，伴随大汗和呼吸困难，疼痛向左臂放射。',
      age: 56,
      sex: 'male',
      pregnant: false,
      duration: '20分钟',
    },
  },
  {
    label: '治疗拒绝',
    description: '观察证据权限与校验失败',
    value: {
      symptoms: '怀孕12周，发热一天，应该吃什么药、用多少剂量？',
      age: 31,
      sex: 'female',
      pregnant: true,
      duration: '1天',
      temperature: 38.2,
    },
  },
]

const form = ref<ConsultationFormState>({
  symptoms: '',
  age: 30,
  sex: 'unknown',
  pregnant: false,
  region: 'CN',
  duration: '',
  temperature: null,
  additional_info: '',
})

/**
 * 使用预设场景覆盖对应表单字段，方便观察不同安全分支。
 * @param scenario 要载入的预设场景
 */
function applyScenario(scenario: ScenarioPreset) {
  form.value = { ...form.value, ...scenario.value }
}

/**
 * 复制当前表单快照并提交给父组件。
 */
function handleSubmit() {
  emit('submit', { ...form.value })
}
</script>

<template>
  <section class="panel consultation-panel">
    <div class="panel-heading">
      <div>
        <p class="eyebrow">01 / 输入</p>
        <h2>症状与基本信息</h2>
      </div>
      <span class="local-badge">先脱敏 · 后处理</span>
    </div>

    <div class="scenario-grid" aria-label="预设场景">
      <button
        v-for="scenario in scenarios"
        :key="scenario.label"
        class="scenario-button"
        type="button"
        @click="applyScenario(scenario)"
      >
        <strong>{{ scenario.label }}</strong>
        <span>{{ scenario.description }}</span>
      </button>
    </div>

    <form class="consultation-form" @submit.prevent="handleSubmit">
      <label class="field field-wide">
        <span>症状描述 <b>必填</b></span>
        <textarea
          v-model.trim="form.symptoms"
          rows="5"
          minlength="2"
          maxlength="2000"
          required
          placeholder="请描述从什么时候开始、主要感受、严重程度和伴随症状。不要填写姓名、身份证或详细地址。"
        />
        <small>{{ form.symptoms.length }} / 2000</small>
      </label>

      <div class="field-grid">
        <label class="field">
          <span>年龄</span>
          <input v-model.number="form.age" type="number" min="0" max="120" step="0.1" required />
        </label>
        <label class="field">
          <span>性别</span>
          <select v-model="form.sex">
            <option value="unknown">未说明</option>
            <option value="female">女</option>
            <option value="male">男</option>
            <option value="other">其他</option>
          </select>
        </label>
        <label class="field">
          <span>持续时间</span>
          <input v-model.trim="form.duration" maxlength="100" placeholder="例如：2天" />
        </label>
        <label class="field">
          <span>体温（℃）</span>
          <input v-model.number="form.temperature" type="number" min="30" max="45" step="0.1" placeholder="可选" />
        </label>
        <label class="field">
          <span>地区</span>
          <select v-model="form.region">
            <option value="CN">中国大陆</option>
            <option value="GLOBAL">其他地区</option>
          </select>
        </label>
        <label class="field checkbox-field" :class="{ disabled: form.sex === 'male' }">
          <input v-model="form.pregnant" type="checkbox" :disabled="form.sex === 'male'" />
          <span>处于孕期</span>
        </label>
      </div>

      <label class="field field-wide">
        <span>补充信息</span>
        <textarea
          v-model.trim="form.additional_info"
          rows="2"
          maxlength="1000"
          placeholder="慢性病、过敏史或正在使用的药物（可选）"
        />
      </label>

      <button class="primary-button" type="submit" :disabled="loading || !form.symptoms.trim()">
        <span v-if="loading" class="spinner" aria-hidden="true" />
        {{ loading ? '正在经过安全链路…' : '开始安全检索' }}
      </button>
    </form>
  </section>
</template>
