<script setup lang="tsx">
import { ref } from 'vue'
import { ChatApiError, clearChatSession, createChatSession, sendChatMessage } from '../api/client'
import type { ChatSession } from '../typings/api/chat'
import type { ChatDisplayMessage } from './chat/types'
import ChatMessages from './chat/ChatMessages.vue'
import ChatComposer from './chat/ChatComposer.vue'

const session = ref<ChatSession | null>(null)
const messages = ref<ChatDisplayMessage[]>([])
const draft = ref('')
const pending = ref('')
const busy = ref(false)
const error = ref('')
const expired = ref(false)
const confirmClear = ref(false)
const memoryTurns = ref(0)
let retryInput = ''
let retryId = ''

/**
 * 发送当前草稿；失败保留原文及重试标识，成功后同步页面与服务端的会话状态。
 */
async function sendMessage() {
  const text = draft.value.trim()
  if (busy.value || expired.value || !text) return
  busy.value = true
  pending.value = text
  error.value = ''
  confirmClear.value = false
  try {
    if (!session.value) session.value = await createChatSession()
    if (!retryId || retryInput !== text) {
      retryId = crypto.randomUUID()
      retryInput = text
    }
    const response = await sendChatMessage({
      session_id: session.value.session_id, message: text, request_id: retryId,
    })
    messages.value = [
      ...messages.value,
      { id: `${retryId}:user`, role: 'user' as const, content: text },
      { id: `${retryId}:assistant`, role: 'assistant' as const, content: response.reply },
    ].slice(-80)
    memoryTurns.value = response.memory_turns
    draft.value = ''
    retryId = retryInput = ''
  } catch (requestError) {
    expired.value = requestError instanceof ChatApiError && requestError.status === 410
    error.value = requestError instanceof Error ? requestError.message : '请求失败，请稍后重试。'
  } finally {
    pending.value = ''
    busy.value = false
  }
}

/**
 * 清空真实服务端记忆后再移除页面记录；过期会话重新开始时保留未发送草稿。
 */
async function resetConversation() {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    if (session.value && !expired.value) {
      try {
        await clearChatSession(session.value.session_id)
      } catch (requestError) {
        if (!(requestError instanceof ChatApiError && requestError.status === 410)) throw requestError
        expired.value = true
      }
    }
    if (!expired.value) draft.value = ''
    // 清空成功的会话可复用，避免每次重置占用新的服务端容量。
    if (expired.value) session.value = null
    messages.value = []
    memoryTurns.value = 0
    expired.value = false
    retryId = retryInput = ''
    confirmClear.value = false
  } catch (requestError) {
    error.value = requestError instanceof Error ? requestError.message : '清空失败，请重试。'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section class="free-chat-workspace">
    <header class="workspace-hero chat-hero">
      <div><p class="science-kicker">DIRECT CONVERSATION / LANGCHAIN</p><h2>自由对话</h2>
        <p>直接与大模型交流，支持连续追问。独立会话，不使用医疗知识库或其他模块的个人资料。</p>
      </div>
      <button class="chat-reset" :disabled="busy || (!session && !messages.length)" @click="confirmClear = true">清空对话与记忆</button>
    </header>

    <div class="chat-policy">
      <span>{{ session?.model ?? '使用后端配置的 LLM' }}</span>
      <span>短期记忆 {{ memoryTurns }} / {{ session?.memory_limit_turns ?? 12 }} 轮</span>
      <span>闲置 {{ Math.round((session?.expires_in_seconds ?? 1800) / 60) }} 分钟过期</span>
      <span>RAG 未启用</span>
    </div>
    <p class="chat-notice">消息及有限历史会发送给已配置的模型服务商。请勿输入姓名、证件号等敏感信息。
      此入口不执行医疗检索、急症规则或引用校验，回答可能有误，不能替代医生。</p>

    <div v-if="confirmClear" class="chat-confirm" role="alert">
      <span>确定清空当前聊天记录和服务端短期记忆？此操作无法撤回。</span>
      <button :disabled="busy" @click="resetConversation">确认清空</button>
      <button :disabled="busy" @click="confirmClear = false">取消</button>
    </div>
    <div v-if="error" class="request-error" role="alert">
      <strong>{{ expired ? '需要开始新对话' : '操作未完成' }}</strong><span>{{ error }}</span>
      <button v-if="expired" class="chat-reset" :disabled="busy" @click="resetConversation">新对话并保留草稿</button>
    </div>
    <div class="chat-panel">
      <ChatMessages :messages="messages" :pending="pending" />
      <ChatComposer v-model="draft" :busy="busy" :disabled="expired" @send="sendMessage" />
    </div>
    <p class="chat-footnote">切换菜单保留本页对话；刷新或关闭页面后不恢复。服务端仅在进程内保存最近完整问答，最多
      {{ session?.memory_limit_turns ?? 12 }} 轮、{{ (session?.memory_max_characters ?? 24000).toLocaleString() }} 字符，超限移除最早问答，不生成长期记忆。
      页面最多显示最近 40 轮，显示的旧记录不一定仍在模型上下文中。</p>
  </section>
</template>

<style scoped>
.free-chat-workspace { max-width: 1180px; margin: 0 auto; }
.chat-hero { display: flex; justify-content: space-between; align-items: center; gap: 24px; }
.chat-hero h2 { font-size: clamp(28px, 3vw, 40px); }
.chat-hero p { line-height: 1.8; }
.chat-reset, .chat-confirm button { padding: 10px 16px; border: 1px solid #41615f; color: #cce4e0; background: #102830; border-radius: 8px; cursor: pointer; flex-shrink: 0; }
button:disabled { opacity: .5; cursor: not-allowed; }
.chat-policy { display: flex; flex-wrap: wrap; gap: 10px; margin: 18px 0; }
.chat-policy span { padding: 7px 12px; border-radius: 6px; border: 1px solid #2d4a53; color: #84dacd; font-size: 14px; }
.chat-notice, .chat-footnote { color: #a3bab9; font-size: 14px; line-height: 1.9; }
.chat-panel { border: 1px solid #2d4a53; border-radius: 16px; overflow: hidden; background: #0a1a24ed; margin: 20px 0; }
.chat-confirm { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; border: 1px solid #947735; color: #eedaa8; border-radius: 10px; padding: 16px; }
@media (max-width: 760px) { .chat-hero { align-items: flex-start; flex-direction: column; } }
</style>
