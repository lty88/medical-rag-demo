<script setup lang="tsx">
import { nextTick, ref, watch } from 'vue'
import type { ChatDisplayMessage } from './types'

const props = defineProps<{ messages: ChatDisplayMessage[]; pending: string }>()
const endRef = ref<HTMLElement | null>(null)

/** 滚动至刚收到的回答或等待状态，不移动整个工作区页面。 */
async function scrollToLatest() {
  await nextTick()
  const container = endRef.value?.parentElement
  if (container) container.scrollTop = container.scrollHeight
}

watch(() => [props.messages.length, props.pending], scrollToLatest)
</script>

<template>
  <div class="chat-messages" role="log" aria-label="自由对话记录" aria-live="polite" :aria-busy="!!pending">
    <div v-if="!messages.length && !pending" class="chat-empty">
      <span>一段对话，从一个问题开始</span>
      <p>可以讨论学习、写作或一般知识，再连续追问。这里不会读取你的问诊、报告或人体图谱数据。</p>
    </div>
    <article v-for="message in messages" :key="message.id" :class="['chat-message', message.role]">
      <strong>{{ message.role === 'user' ? '你' : 'AI 助手' }}</strong>
      <div>{{ message.content }}</div>
    </article>
    <template v-if="pending">
      <article class="chat-message user"><strong>你</strong><div>{{ pending }}</div></article>
      <article class="chat-message assistant"><strong>AI 助手</strong><div>正在生成回答，请稍候…</div></article>
    </template>
    <div ref="endRef" />
  </div>
</template>

<style scoped>
.chat-messages { min-height: 300px; max-height: 58vh; overflow-y: auto; padding: 24px; scroll-behavior: smooth; }
.chat-empty { max-width: 600px; margin: 60px auto; text-align: center; color: #a5c5c4; }
.chat-empty span { color: #e5f6f4; font-size: 24px; font-weight: 600; }
.chat-empty p { line-height: 1.9; }
.chat-message { max-width: 90%; width: fit-content; margin: 0 0 22px; padding: 18px 22px; border: 1px solid #25434b; border-radius: 14px; background: #10232d; }
.chat-message.user { margin-left: auto; background: #113b3d; border-color: #286260; }
.chat-message strong { display: block; color: #74e0d0; font-size: 14px; margin-bottom: 10px; }
.chat-message div { white-space: pre-wrap; overflow-wrap: anywhere; color: #e4eeef; font-size: 17px; line-height: 1.85; }
@media (max-width: 640px) { .chat-messages { padding: 12px; } .chat-message { max-width: 100%; padding: 14px; } }
@media (prefers-reduced-motion: reduce) { .chat-messages { scroll-behavior: auto; } }
</style>
