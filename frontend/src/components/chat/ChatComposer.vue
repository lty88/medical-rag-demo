<script setup lang="tsx">
defineProps<{ modelValue: string; busy: boolean; disabled: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: string]; send: [] }>()

/**
 * 同步当前输入草稿，不写入浏览器持久化存储。
 * @param event 文本输入事件
 */
function updateDraft(event: Event) {
  emit('update:modelValue', (event.target as HTMLTextAreaElement).value)
}

/**
 * 使用 Ctrl/Command + Enter 提交，避开中文输入法组合输入过程。
 * @param event 键盘事件
 */
function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && (event.ctrlKey || event.metaKey) && !event.isComposing) {
    event.preventDefault()
    emit('send')
  }
}
</script>

<template>
  <form class="chat-composer" @submit.prevent="emit('send')">
    <label for="free-chat-input">你的消息</label>
    <textarea id="free-chat-input" :value="modelValue" :disabled="busy || disabled" rows="4" maxlength="4000"
      placeholder="输入问题，或接着上一轮继续问…" @input="updateDraft" @keydown="handleKeydown" />
    <footer><span>{{ modelValue.length }} / 4000 · Ctrl / ⌘ + Enter 发送</span>
      <button type="submit" :disabled="busy || disabled || !modelValue.trim()">{{ busy ? '等待回答…' : '发送消息 ↗' }}</button>
    </footer>
  </form>
</template>

<style scoped>
.chat-composer { padding: 22px 24px; border-top: 1px solid #25434b; }
label { display: block; margin-bottom: 12px; color: #c8dedb; }
textarea { width: 100%; resize: vertical; min-height: 100px; background: #071720; color: #e4eeef; border: 1px solid #35575c; border-radius: 10px; padding: 14px; font: inherit; font-size: 17px; line-height: 1.6; }
textarea:focus-visible { outline: 2px solid #73e0d0; outline-offset: 2px; }
footer { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-top: 14px; }
footer span { color: #97b5b3; font-size: 13px; }
button { background: #73e0d0; color: #06262c; border: 0; border-radius: 8px; padding: 12px 24px; font-weight: 700; cursor: pointer; }
button:disabled { opacity: .5; cursor: not-allowed; }
@media (max-width: 640px) { .chat-composer { padding: 16px; } footer { align-items: stretch; flex-direction: column; } }
</style>
