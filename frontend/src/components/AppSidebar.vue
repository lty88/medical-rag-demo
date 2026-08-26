<script setup lang="tsx">
import type { KnowledgeStats, WorkspaceKey, WorkspaceMenuItem } from '../types'

defineProps<{
  active: WorkspaceKey
  items: WorkspaceMenuItem[]
  stats: KnowledgeStats | null
}>()

const emit = defineEmits<{ change: [workspace: WorkspaceKey] }>()

/**
 * 通知应用壳切换到指定医疗工作区。
 * @param workspace 目标工作区标识
 */
function selectWorkspace(workspace: WorkspaceKey) {
  emit('change', workspace)
}
</script>

<template>
  <aside class="med-sidebar">
    <div class="product-mark">
      <span class="pulse-logo"><i /></span>
      <div>
        <strong>VITA·RAG</strong>
        <small>MEDICAL INTELLIGENCE</small>
      </div>
    </div>

    <div class="sidebar-intro">
      <span>CLINICAL RESEARCH OS</span>
      <h1>生命健康<br />智能工作台</h1>
      <p>检索、证据、模型与安全规则协同的医疗科研界面。</p>
    </div>

    <nav class="workspace-menu" aria-label="产品功能菜单">
      <button
        v-for="item in items"
        :key="item.key"
        type="button"
        :class="{ active: active === item.key }"
        @click="selectWorkspace(item.key)"
      >
        <span>{{ item.index }}</span>
        <div>
          <strong>{{ item.label }}</strong>
          <small>{{ item.description }}</small>
        </div>
        <i>↗</i>
      </button>
    </nav>

    <section class="sidebar-runtime">
      <p>RUNTIME MATRIX</p>
      <dl>
        <div>
          <dt>语料规模</dt>
          <dd>{{ stats ? stats.total_documents.toLocaleString() : '—' }}</dd>
        </div>
        <div>
          <dt>向量索引</dt>
          <dd :class="stats?.vector_index_ready ? 'ok' : 'warn'">
            {{ stats?.vector_index_ready ? 'READY' : 'OFFLINE' }}
          </dd>
        </div>
        <div>
          <dt>生成模型</dt>
          <dd :class="stats?.llm_ready ? 'ok' : 'warn'">
            {{ stats?.llm_model ?? 'TEMPLATE' }}
          </dd>
        </div>
      </dl>
    </section>

    <footer class="sidebar-footer">
      <span>RESEARCH USE ONLY</span>
      <small>不提供诊断或处方</small>
    </footer>
  </aside>
</template>
