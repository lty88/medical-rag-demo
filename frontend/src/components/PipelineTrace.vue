<script setup lang="tsx">
import type { PipelineStep } from '../types'

defineProps<{ steps: PipelineStep[] }>()

/**
 * 把后端步骤状态转换为简短中文标签。
 * @param status 后端流水线状态
 * @returns 对应的中文展示文本
 */
function statusLabel(status: PipelineStep['status']): string {
  return {
    pending: '等待',
    running: '运行中',
    passed: '通过',
    blocked: '阻断',
    fallback: '轻量回退',
  }[status]
}
</script>

<template>
  <section class="panel trace-panel">
    <div class="panel-heading compact">
      <div>
        <p class="eyebrow">02 / 过程</p>
        <h2>安全链路轨迹</h2>
      </div>
      <span class="step-count">{{ steps.length }} steps</span>
    </div>
    <ol class="trace-list">
      <li v-for="(step, index) in steps" :key="step.key" :class="`trace-${step.status}`">
        <div class="trace-rail">
          <span class="trace-dot">{{ index + 1 }}</span>
          <span v-if="index < steps.length - 1" class="trace-line" />
        </div>
        <div class="trace-copy">
          <div class="trace-title-row">
            <strong>
              {{ step.label }}
              <span v-if="step.key === 'generation'" class="trace-ai-label">LLM</span>
            </strong>
            <span class="status-chip">{{ statusLabel(step.status) }}</span>
          </div>
          <p>{{ step.detail }}</p>
          <small>{{ step.duration_ms }} ms</small>
        </div>
      </li>
    </ol>
  </section>
</template>
