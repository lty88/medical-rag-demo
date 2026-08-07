<script setup lang="tsx">
const stages = [
  { index: '01', title: '隐私与分诊', detail: '危险信号命中即停止' },
  { index: '02', title: '全量双路召回', detail: 'BM25 + 医疗 FAISS' },
  { index: '03', title: '混排与精排', detail: 'RRF + Cross-Encoder' },
  { index: '04', title: '人群过滤', detail: '年龄 · 孕期 · 地区' },
  { index: '05', title: '约束生成', detail: '只使用入选证据' },
  { index: '06', title: '安全校验', detail: '引用 · 数字 · 权限' },
]
</script>

<template>
  <section class="architecture-strip" aria-label="系统处理架构">
    <article v-for="(stage, index) in stages" :key="stage.index" class="architecture-stage">
      <span class="stage-index">{{ stage.index }}</span>
      <div>
        <strong>{{ stage.title }}</strong>
        <small>{{ stage.detail }}</small>
      </div>
      <span v-if="index < stages.length - 1" class="stage-arrow" aria-hidden="true">→</span>
    </article>
  </section>
</template>
