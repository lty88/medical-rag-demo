<script setup lang="tsx">
import type { Citation } from '../types'

defineProps<{
  citations: Citation[]
  generationMode: 'configured-llm' | 'evidence-template' | 'not-run'
}>()
</script>

<template>
  <section class="panel evidence-panel">
    <div class="panel-heading compact">
      <div>
        <p class="eyebrow">04 / 证据</p>
        <h2>引用与生成权限</h2>
      </div>
      <span class="step-count">{{ citations.length }} sources</span>
    </div>

    <div v-if="citations.length" class="evidence-list">
      <article
        v-for="citation in citations"
        :id="`evidence-${citation.marker}`"
        :key="citation.marker"
        class="evidence-card"
      >
        <header>
          <span class="citation-marker">{{ citation.marker }}</span>
          <div class="evidence-badges">
            <span v-if="generationMode === 'configured-llm'" class="llm-evidence-badge">
              已送入 LLM
            </span>
            <span :class="['trust-badge', `trust-${citation.trust_level}`]">
              {{ citation.trust_level }}
            </span>
          </div>
        </header>
        <h3>{{ citation.title }}</h3>
        <p>{{ citation.excerpt }}</p>
        <footer>
          <span>{{ citation.source }}</span>
          <span :class="citation.allow_treatment_generation ? 'permission-yes' : 'permission-no'">
            {{ citation.allow_treatment_generation ? '可参与治疗生成' : '仅允许检索' }}
          </span>
        </footer>
        <a
          v-if="citation.source_url"
          :href="citation.source_url"
          target="_blank"
          rel="noreferrer"
        >查看来源 ↗</a>
      </article>
    </div>
    <div v-else class="empty-state small">
      <span>∅</span>
      <p>该分支没有进入证据检索。</p>
    </div>
  </section>
</template>
