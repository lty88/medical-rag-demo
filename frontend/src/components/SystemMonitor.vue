<script setup lang="tsx">
import type { KnowledgeStats } from '../types'

defineProps<{ stats: KnowledgeStats | null }>()
const emit = defineEmits<{ refresh: [] }>()
</script>

<template>
  <section class="monitor-workspace">
    <header class="workspace-hero compact-hero">
      <div><p class="science-kicker">OBSERVABILITY / MODEL RUNTIME</p><h2>索引、模型与安全组件监测</h2><p>这里展示配置与加载状态，不把“已配置”伪装成实时可用性探活。</p></div>
      <button class="refresh-button" type="button" @click="emit('refresh')">刷新状态 ↻</button>
    </header>

    <div class="monitor-grid">
      <article :class="['monitor-card', { healthy: stats?.vector_index_ready }]">
        <header><span>VECTOR ENGINE</span><i /></header><strong>FAISS</strong><p>{{ stats?.vector_mode ?? '服务未连接' }}</p><footer><span>DOCUMENTS</span><b>{{ stats?.vector_document_count.toLocaleString() ?? '—' }}</b></footer>
      </article>
      <article :class="['monitor-card', { healthy: stats?.reranker_model }]">
        <header><span>RANKING ENGINE</span><i /></header><strong>Cross-Encoder</strong><p>{{ stats?.reranker_mode ?? '服务未连接' }}</p><footer><span>MODEL</span><b>{{ stats?.reranker_model ?? '—' }}</b></footer>
      </article>
      <article :class="['monitor-card', { healthy: stats?.llm_ready }]">
        <header><span>GENERATION ENGINE</span><i /></header><strong>LLM</strong><p>{{ stats?.llm_ready ? '接口配置完整；实际可用性以单次请求为准。' : '当前使用证据模板回退。' }}</p><footer><span>MODEL</span><b>{{ stats?.llm_model ?? 'TEMPLATE' }}</b></footer>
      </article>
      <article :class="['monitor-card', { healthy: stats }]">
        <header><span>SAFETY GATE</span><i /></header><strong>10 stages</strong><p>隐私、分诊、过滤、引用、数字与生成权限校验。</p><footer><span>POLICY</span><b>ENFORCED</b></footer>
      </article>
    </div>

    <section class="pipeline-blueprint">
      <header><span>ONLINE REQUEST BLUEPRINT</span><h3>一次咨询如何经过系统</h3></header>
      <div class="blueprint-track">
        <article><b>01</b><strong>Privacy</strong><small>直接身份信息脱敏</small></article><i>→</i>
        <article><b>02</b><strong>Triage</strong><small>危险信号前置中止</small></article><i>→</i>
        <article><b>03</b><strong>Retrieval</strong><small>BM25 + FAISS</small></article><i>→</i>
        <article><b>04</b><strong>Ranking</strong><small>RRF + Reranker</small></article><i>→</i>
        <article><b>05</b><strong>Generation</strong><small>证据约束 LLM</small></article><i>→</i>
        <article><b>06</b><strong>Validation</strong><small>引用与权限校验</small></article>
      </div>
    </section>

    <section class="monitor-boundary"><span>PRODUCTION READINESS</span><div><article><i class="done" /><p><strong>已实现</strong>混合检索、精排、LLM 回退、安全校验、请求日志</p></article><article><i /><p><strong>仍需建设</strong>鉴权、审计存储、限流、指标采集、告警与医疗合规评审</p></article></div></section>
  </section>
</template>
