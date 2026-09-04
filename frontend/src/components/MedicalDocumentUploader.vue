<script setup lang="tsx">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps<{ file: File | null }>()
const emit = defineEmits<{
  select: [file: File]
  clear: []
}>()

const inputRef = ref<HTMLInputElement | null>(null)
const dragActive = ref(false)
const localError = ref('')
const previewUrl = ref('')

const isImage = computed(() => Boolean(props.file?.type.startsWith('image/')))

/**
 * 将文件字节数转换为便于用户理解的容量文本。
 * @param bytes 文件字节数
 * @returns KB 或 MB 格式的容量说明
 */
function formatFileSize(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  return `${Math.max(1, Math.round(bytes / 1024))} KB`
}

/**
 * 打开系统文件选择器。
 */
function openPicker() {
  inputRef.value?.click()
}

/**
 * 校验浏览器端可提前识别的文件类型和 12 MB 体积限制。
 * @param file 等待上传的本地文件
 * @returns 文件是否满足前端基础限制
 */
function validateFile(file: File): boolean {
  const extension = file.name.slice(file.name.lastIndexOf('.')).toLowerCase()
  const allowed = ['.pdf', '.txt', '.md', '.png', '.jpg', '.jpeg', '.webp']
  if (!allowed.includes(extension)) {
    localError.value = '支持 PDF、TXT、Markdown、PNG、JPG、WebP；暂不支持 DICOM 和视频。'
    return false
  }
  if (file.size > 12 * 1024 * 1024) {
    localError.value = '单个文件不能超过 12 MB。'
    return false
  }
  localError.value = ''
  return true
}

/**
 * 接收经过基础校验的文件并通知父组件更新表单。
 * @param file 用户选择或拖入的文件
 */
function selectFile(file: File) {
  if (validateFile(file)) emit('select', file)
}

/**
 * 读取文件输入框的首个文件。
 * @param event 原生 input change 事件
 */
function handleInput(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) selectFile(file)
  target.value = ''
}

/**
 * 接收拖放文件并恢复拖放区状态。
 * @param event 浏览器文件拖放事件
 */
function handleDrop(event: DragEvent) {
  dragActive.value = false
  const file = event.dataTransfer?.files?.[0]
  if (file) selectFile(file)
}

/**
 * 清除当前文件和本地校验错误。
 */
function clearFile() {
  localError.value = ''
  emit('clear')
}

/**
 * 释放旧预览地址并为图片文件生成新的临时预览。
 * @param file 当前选中的上传文件
 */
function updatePreview(file: File | null) {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = file?.type.startsWith('image/') ? URL.createObjectURL(file) : ''
}

watch(() => props.file, updatePreview, { immediate: true })

onBeforeUnmount(() => {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
})
</script>

<template>
  <div class="medical-upload-control">
    <input
      ref="inputRef"
      class="medical-upload-input"
      type="file"
      accept=".pdf,.txt,.md,.png,.jpg,.jpeg,.webp"
      @change="handleInput"
    />
    <div
      v-if="!file"
      :class="['medical-dropzone', { active: dragActive }]"
      role="button"
      tabindex="0"
      @click="openPicker"
      @keydown.enter="openPicker"
      @keydown.space.prevent="openPicker"
      @dragenter.prevent="dragActive = true"
      @dragover.prevent="dragActive = true"
      @dragleave.prevent="dragActive = false"
      @drop.prevent="handleDrop"
    >
      <span class="upload-scan-symbol"><i /><b>+</b></span>
      <strong>拖入资料，或点击选择文件</strong>
      <p>病历、检验单、彩超 / B 超报告、CT / MRI 报告、病理报告</p>
      <small>PDF · PNG · JPG · WEBP · TXT · 最大 12 MB</small>
    </div>

    <article v-else class="selected-medical-file">
      <div v-if="isImage" class="medical-file-preview">
        <img :src="previewUrl" alt="待解读医疗资料预览" />
        <span>仅供上传前核对</span>
      </div>
      <div v-else class="medical-file-icon"><span>{{ file.name.split('.').pop()?.toUpperCase() }}</span></div>
      <div class="medical-file-copy">
        <small>SELECTED DOCUMENT</small>
        <strong>{{ file.name }}</strong>
        <p>{{ formatFileSize(file.size) }} · 提交后仅在本次请求中处理</p>
      </div>
      <button type="button" aria-label="移除当前文件" @click="clearFile">移除</button>
    </article>

    <p v-if="localError" class="upload-local-error">{{ localError }}</p>
  </div>
</template>
