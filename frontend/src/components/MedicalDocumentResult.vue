<script setup lang="tsx">
import type { MedicalDocumentInterpretationResponse } from '../types'

defineProps<{ result: MedicalDocumentInterpretationResponse }>()
const emit = defineEmits<{ reset: [] }>()

/**
 * 将关键发现等级转换为面向患者的中文标签。
 * @param level 后端返回的发现等级
 * @returns 适合结果卡片展示的中文文本
 */
function findingLevelLabel(level: MedicalDocumentInterpretationResponse['findings'][number]['level']): string {
  return {
    normal: '报告未标异常',
    attention: '建议关注',
    urgent: '尽快就医',
    uncertain: '需要确认',
  }[level]
}

/**
 * 将整体紧急程度转换为患者可理解的行动标签。
 * @param urgency 解读结果的整体紧急程度
 * @returns 中文行动标签
 */
function urgencyLabel(urgency: MedicalDocumentInterpretationResponse['urgency']): string {
  return {
    routine: '常规沟通',
    attention: '建议关注',
    urgent: '尽快线下就医',
    insufficient: '资料不足',
  }[urgency]
}
</script>

<template>
  <section class="medical-interpretation-result">
    <header class="interpretation-result-heading">
      <div>
        <p class="science-kicker">INTERPRETATION · {{ result.request_id }}</p>
        <h2>{{ result.title }}</h2>
        <p>{{ result.summary }}</p>
      </div>
      <div :class="['interpretation-urgency', `urgency-${result.urgency}`]">
        <span>{{ urgencyLabel(result.urgency) }}</span>
        <small>{{ result.extraction_mode === 'vision' ? '图片文字识别' : '文档文字提取' }}</small>
      </div>
    </header>

    <div v-if="result.red_flags.length" class="interpretation-alert">
      <strong>需要优先处理</strong>
      <ul><li v-for="item in result.red_flags" :key="item">{{ item }}</li></ul>
      <p>如有明显不适、报告注明危急值或症状正在加重，请直接联系开单医生或前往急诊。</p>
    </div>

    <section class="interpretation-block">
      <header><span>01 / 报告关键项</span><b>{{ result.findings.length }} FINDINGS</b></header>
      <div class="medical-finding-grid">
        <article v-for="finding in result.findings" :key="`${finding.name}-${finding.original_text}`" :class="`finding-${finding.level}`">
          <div><strong>{{ finding.name }}</strong><span>{{ findingLevelLabel(finding.level) }}</span></div>
          <blockquote v-if="finding.original_text">“{{ finding.original_text }}”</blockquote>
          <p>{{ finding.explanation }}</p>
        </article>
      </div>
    </section>

    <section class="interpretation-block">
      <header><span>02 / 通俗解读</span><b>PLAIN LANGUAGE</b></header>
      <div class="interpretation-section-list">
        <article v-for="section in result.sections" :key="section.title">
          <h3>{{ section.title }}</h3>
          <p>{{ section.content }}</p>
        </article>
      </div>
    </section>

    <div class="interpretation-two-column">
      <section class="interpretation-block compact">
        <header><span>03 / 建议问医生</span><b>VISIT PREP</b></header>
        <ol><li v-for="item in result.questions_for_doctor" :key="item">{{ item }}</li></ol>
        <p v-if="!result.questions_for_doctor.length" class="result-empty-copy">暂无额外问题。</p>
      </section>
      <section class="interpretation-block compact limitation-block">
        <header><span>04 / 解读限制</span><b>BOUNDARY</b></header>
        <ul><li v-for="item in result.limitations" :key="item">{{ item }}</li></ul>
      </section>
    </div>

    <section class="interpretation-block evidence-block">
      <header><span>05 / 本地 RAG 证据</span><b>{{ result.evidence.length }} SOURCES</b></header>
      <p class="interpretation-retrieval-mode">{{ result.retrieval_mode }}</p>
      <div v-if="result.evidence.length" class="interpretation-evidence-list">
        <article v-for="item in result.evidence" :key="item.marker">
          <span>{{ item.marker }}</span>
          <div><strong>{{ item.title }}</strong><p>{{ item.excerpt }}</p><small>{{ item.source }} · {{ item.trust_level }}</small></div>
          <a v-if="item.source_url" :href="item.source_url" target="_blank" rel="noreferrer">原文 ↗</a>
        </article>
      </div>
      <p v-else class="result-empty-copy">本地知识库没有找到足够匹配的辅助证据，请以报告医生解释为准。</p>
    </section>

    <footer class="interpretation-footer">
      <div><strong>{{ result.disclaimer }}</strong><p>{{ result.privacy_notice }}</p></div>
      <button type="button" @click="emit('reset')">解读另一份资料</button>
    </footer>
  </section>
</template>
