<script setup lang="tsx">
import type { ConsultationResponse } from '../types'

defineProps<{ result: ConsultationResponse }>()
</script>

<template>
  <section :class="['panel', 'result-panel', `urgency-${result.urgency}`]">
    <div class="result-header">
      <div class="result-icon" aria-hidden="true">
        {{ result.urgency === 'emergency' ? '!' : result.blocked ? '×' : '✓' }}
      </div>
      <div>
        <p class="eyebrow">03 / 输出 · {{ result.request_id }}</p>
        <h2>{{ result.title }}</h2>
        <p class="result-summary">{{ result.summary }}</p>
      </div>
    </div>

    <div v-if="result.red_flags.length" class="alert-box danger">
      <strong>命中的危险信号</strong>
      <ul>
        <li v-for="flag in result.red_flags" :key="flag">{{ flag }}</li>
      </ul>
    </div>

    <div v-if="result.validation_issues.length" class="alert-box warning">
      <strong>校验阻断原因</strong>
      <ul>
        <li v-for="issue in result.validation_issues" :key="issue">{{ issue }}</li>
      </ul>
    </div>

    <div class="answer-sections">
      <article v-for="section in result.sections" :key="section.title">
        <h3>{{ section.title }}</h3>
        <p>{{ section.content }}</p>
      </article>
    </div>

    <div class="result-meta">
      <p><span>检索模式</span>{{ result.retrieval_mode }}</p>
      <p><span>隐私处理</span>{{ result.privacy_notice }}</p>
    </div>
    <p class="disclaimer">{{ result.disclaimer }}</p>
  </section>
</template>
