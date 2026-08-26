<script setup lang="tsx">
import { ref } from 'vue'
import { searchResearchEvidence } from '../api/client'
import type { ResearchSearchResponse } from '../types'

const query = ref('')
const topK = ref(8)
const loading = ref(false)
const error = ref('')
const response = ref<ResearchSearchResponse | null>(null)

const suggestedQueries = [
  '空腹时上腹痛，进食后缓解可能与哪些情况相关',
  '持续咳嗽伴痰中带血需要关注哪些危险信号',
  '偏头痛与普通头痛在症状描述上有什么区别',
]

/**
 * 使用建议问题填充检索输入框。
 * @param value 可直接执行混合检索的医学问题
 */
function applySuggestion(value: string) {
  query.value = value
}

/**
 * 提交研究问题并读取不经过 LLM 的混合检索证据。
 */
async function submitSearch() {
  if (query.value.trim().length < 2) return
  loading.value = true
  error.value = ''
  try {
    response.value = await searchResearchEvidence({
      query: query.value.trim(),
      top_k: topK.value,
    })
  } catch (requestError) {
    error.value = requestError instanceof Error ? requestError.message : '证据检索失败。'
  } finally {
    loading.value = false
  }
}

/**
 * 把检索或精排分数格式化为适合研究界面的短小数。
 * @param score 后端返回的阶段分数
 * @returns 保留四位小数的文本
 */
function formatScore(score: number): string {
  return score.toFixed(4)
}
</script>

<template>
  <section class="research-workspace">
    <header class="workspace-hero research-hero">
      <div>
        <p class="science-kicker">EVIDENCE DISCOVERY / NO GENERATION</p>
        <h2>直接检查模型看到的证据</h2>
        <p>该工作区只执行关键词召回、向量召回、RRF 与医疗精排，不调用 LLM，不生成诊断结论。</p>
      </div>
      <div class="research-seal"><span>4</span><small>RANKING STAGES</small></div>
    </header>

    <form class="research-query-panel" @submit.prevent="submitSearch">
      <div class="query-label"><span>RESEARCH QUESTION</span><small>中文自然语言 · 最多 500 字</small></div>
      <div class="research-query-row">
        <textarea
          v-model.trim="query"
          rows="3"
          maxlength="500"
          placeholder="输入疾病、症状、药品或希望核查的医学问题…"
        />
        <div>
          <label>返回数量<select v-model.number="topK"><option :value="5">5</option><option :value="8">8</option><option :value="12">12</option><option :value="20">20</option></select></label>
          <button type="submit" :disabled="loading || query.length < 2">
            {{ loading ? '正在精排…' : '执行证据检索' }}
          </button>
        </div>
      </div>
      <div class="query-suggestions">
        <button v-for="item in suggestedQueries" :key="item" type="button" @click="applySuggestion(item)">{{ item }}</button>
      </div>
    </form>

    <div v-if="error" class="request-error"><strong>检索失败</strong><span>{{ error }}</span></div>

    <section v-if="response" class="research-results">
      <header>
        <div><span>REQUEST {{ response.request_id }}</span><h3>{{ response.total }} 条精排证据</h3></div>
        <dl><div><dt>总耗时</dt><dd>{{ response.duration_ms }} ms</dd></div><div><dt>生成调用</dt><dd>0</dd></div></dl>
      </header>
      <p class="research-mode">{{ response.retrieval_mode }}</p>

      <div class="research-result-list">
        <article v-for="(item, index) in response.results" :key="item.id">
          <div class="result-rank"><span>{{ String(index + 1).padStart(2, '0') }}</span><small>RANK</small></div>
          <div class="research-evidence-copy">
            <div class="evidence-meta">
              <span>{{ item.source }}</span>
              <span>{{ item.source_type }}</span>
              <span :class="`trust-${item.trust_level}`">{{ item.trust_level }}</span>
              <b>{{ item.allow_treatment_generation ? '治疗证据允许' : '仅参与检索' }}</b>
            </div>
            <h4>{{ item.title }}</h4>
            <p v-if="item.question" class="source-question">{{ item.question }}</p>
            <p>{{ item.excerpt }}</p>
            <a v-if="item.source_url" :href="item.source_url" target="_blank" rel="noreferrer">查看原始来源 ↗</a>
          </div>
          <dl class="score-matrix">
            <div><dt>BM25</dt><dd>{{ formatScore(item.bm25_score) }}</dd></div>
            <div><dt>VECTOR</dt><dd>{{ formatScore(item.vector_score) }}</dd></div>
            <div><dt>RRF</dt><dd>{{ formatScore(item.rrf_score) }}</dd></div>
            <div class="score-primary"><dt>RERANK</dt><dd>{{ formatScore(item.rerank_score) }}</dd></div>
          </dl>
        </article>
      </div>
    </section>

    <section v-else-if="!loading" class="research-empty">
      <div class="radar-orbit"><i /><i /><span /></div>
      <h3>等待研究问题</h3>
      <p>结果将展示每条文档在四个阶段的分数，方便判断问题出在数据、召回还是精排。</p>
    </section>
  </section>
</template>
