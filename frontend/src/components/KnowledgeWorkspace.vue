<script setup lang="tsx">
import { computed } from 'vue'
import type { KnowledgeStats } from '../types'

const props = defineProps<{ stats: KnowledgeStats | null }>()

const sourceEntries = computed(() => Object.entries(props.stats?.source_counts ?? {}).sort((a, b) => b[1] - a[1]))
const trustEntries = computed(() => Object.entries(props.stats?.trust_counts ?? {}).sort((a, b) => b[1] - a[1]))

/**
 * 计算某类知识在全部语料中的占比。
 * @param count 当前分类文档数量
 * @returns 保留一位小数的百分比文本
 */
function percentage(count: number): string {
  const total = props.stats?.total_documents ?? 0
  return total ? `${((count / total) * 100).toFixed(1)}%` : '0%'
}
</script>

<template>
  <section class="knowledge-workspace">
    <header class="workspace-hero compact-hero">
      <div><p class="science-kicker">KNOWLEDGE GOVERNANCE</p><h2>医疗知识资产与生成权限</h2><p>数量决定覆盖率，来源、版本和权限决定系统可以说到什么程度。</p></div>
      <div class="knowledge-total"><span>{{ stats?.total_documents.toLocaleString() ?? '—' }}</span><small>DOCUMENTS</small></div>
    </header>

    <div class="knowledge-metrics">
      <article><span>KEYWORD INDEX</span><strong>{{ stats?.keyword_document_count.toLocaleString() ?? '—' }}</strong><small>SQLite FTS5 / BM25</small></article>
      <article><span>VECTOR INDEX</span><strong>{{ stats?.vector_document_count.toLocaleString() ?? '—' }}</strong><small>{{ stats?.vector_index_ready ? '全量覆盖' : '未就绪' }}</small></article>
      <article><span>GENERATION POLICY</span><strong>DENY</strong><small>默认不允许治疗生成</small></article>
      <article><span>LLM BINDING</span><strong>{{ stats?.llm_ready ? 'ON' : 'OFF' }}</strong><small>{{ stats?.llm_model ?? '证据模板' }}</small></article>
    </div>

    <div class="knowledge-grid">
      <section class="knowledge-panel source-distribution">
        <header><div><span>DATA PROVENANCE</span><h3>数据来源分布</h3></div><small>{{ sourceEntries.length }} SOURCES</small></header>
        <div v-if="sourceEntries.length" class="distribution-list">
          <article v-for="([source, count], index) in sourceEntries" :key="source">
            <span>{{ String(index + 1).padStart(2, '0') }}</span>
            <div><strong>{{ source }}</strong><i><b :style="{ width: percentage(count) }" /></i></div>
            <dl><dt>{{ count.toLocaleString() }}</dt><dd>{{ percentage(count) }}</dd></dl>
          </article>
        </div>
        <p v-else class="panel-empty">等待知识库统计数据。</p>
      </section>

      <section class="knowledge-panel trust-distribution">
        <header><div><span>EVIDENCE LEVEL</span><h3>证据可信等级</h3></div></header>
        <div class="trust-rings">
          <article v-for="([trust, count], index) in trustEntries" :key="trust" :style="{ '--ring-index': index }">
            <div><span>{{ percentage(count) }}</span></div><strong>{{ trust }}</strong><small>{{ count.toLocaleString() }} 条</small>
          </article>
        </div>
        <div class="policy-note"><b>生成权限与可信等级不是同一概念</b><p>Huatuo 等二级问答可以参与召回，但不能因为相关度高就自动成为治疗依据。</p></div>
      </section>
    </div>

    <section class="governance-layers">
      <header><span>GOVERNANCE PIPELINE</span><h3>知识进入回答前的四层治理</h3></header>
      <div><article><b>01</b><strong>来源追溯</strong><p>保存数据来源、URL 与许可证。</p></article><article><b>02</b><strong>版本约束</strong><p>地区、指南版本与更新时间过滤。</p></article><article><b>03</b><strong>人群兼容</strong><p>年龄、孕期和适用人群校验。</p></article><article><b>04</b><strong>生成权限</strong><p>治疗和剂量仅接受授权证据。</p></article></div>
    </section>
  </section>
</template>
