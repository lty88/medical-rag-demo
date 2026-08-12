<script setup lang="tsx">
import type { AnswerContentPart, ConsultationResponse } from '../types'

defineProps<{ result: ConsultationResponse }>()

/**
 * 将答案正文拆分为普通文本和可跳转的证据编号。
 * @param content 后端返回的答案区块正文
 * @returns 保持原始顺序的文本及引用编号片段
 */
function splitCitationMarkers(content: string): AnswerContentPart[] {
  return content.split(/(\[S\d+\])/g).filter(Boolean).map((value) => {
    const match = /^\[(S\d+)\]$/.exec(value)
    return { value, marker: match?.[1] ?? null }
  })
}
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
        <p class="result-summary">
          <template v-for="(part, index) in splitCitationMarkers(result.summary)" :key="`${index}-${part.value}`">
            <a
              v-if="part.marker"
              class="inline-citation"
              :href="`#evidence-${part.marker}`"
              :aria-label="`查看证据 ${part.marker}`"
            >{{ part.value }}</a>
            <template v-else>{{ part.value }}</template>
          </template>
        </p>
      </div>
    </div>

    <div
      v-if="result.generation_mode !== 'not-run'"
      :class="['generation-banner', `generation-${result.generation_mode}`]"
    >
      <span class="generation-symbol" aria-hidden="true">
        {{ result.generation_mode === 'configured-llm' ? 'AI' : 'R' }}
      </span>
      <div>
        <strong>
          {{ result.generation_mode === 'configured-llm' ? 'LLM 证据约束生成' : '证据模板回退' }}
        </strong>
        <p v-if="result.generation_mode === 'configured-llm'">
          {{ result.generation_model }} 已读取下方入选证据；答案中的 [S1] 等编号可直接跳转到出处。
        </p>
        <p v-else>本次未获得有效模型回答，页面展示的是可追溯证据模板，请查看流程中的回退原因。</p>
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
        <p>
          <template v-for="(part, index) in splitCitationMarkers(section.content)" :key="`${index}-${part.value}`">
            <a
              v-if="part.marker"
              class="inline-citation"
              :href="`#evidence-${part.marker}`"
              :aria-label="`查看证据 ${part.marker}`"
            >{{ part.value }}</a>
            <template v-else>{{ part.value }}</template>
          </template>
        </p>
      </article>
    </div>

    <div class="result-meta">
      <p><span>检索模式</span>{{ result.retrieval_mode }}</p>
      <p>
        <span>生成模式</span>
        {{ result.generation_mode === 'configured-llm' ? result.generation_model : result.generation_mode }}
      </p>
      <p><span>隐私处理</span>{{ result.privacy_notice }}</p>
    </div>
    <p class="disclaimer">{{ result.disclaimer }}</p>
  </section>
</template>
