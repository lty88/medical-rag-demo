<script setup lang="tsx">
import type { AnatomyModelId, AtlasModelProfile } from '../types'

defineProps<{
  models: AtlasModelProfile[]
  activeModelId: AnatomyModelId
}>()

const emit = defineEmits<{
  select: [modelId: AnatomyModelId]
}>()

/**
 * 请求切换人体解剖参考模型，由父组件统一重置系统和选择状态。
 * @param modelId 男性全身或女性腹盆躯干模型标识
 */
function selectModel(modelId: AnatomyModelId) {
  emit('select', modelId)
}
</script>

<template>
  <div class="anatomy-model-switch" aria-label="解剖参考模型">
    <p>ANATOMY REFERENCE</p>
    <div>
      <button
        v-for="model in models"
        :key="model.id"
        type="button"
        :class="{ active: activeModelId === model.id }"
        :aria-pressed="activeModelId === model.id"
        @click="selectModel(model.id)"
      >
        <i>{{ model.id === 'female' ? '♀' : '♂' }}</i>
        <span>
          <strong>{{ model.name }}</strong>
          <small>{{ model.coverage }}</small>
        </span>
      </button>
    </div>
    <p class="anatomy-model-description">
      {{ models.find((model) => model.id === activeModelId)?.description }}
    </p>
  </div>
</template>
