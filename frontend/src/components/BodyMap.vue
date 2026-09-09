<script setup lang="tsx">
import { defineAsyncComponent, ref } from 'vue'
import type {
  BodyMapExposed,
  AnatomyModelId,
  AnatomySceneExposed,
  AnatomyStructureSelection,
} from '../anatomy/types'
import type { AtlasBodyRegion, AtlasSystem } from '../types'

/**
 * 按需加载 Three.js 人体场景，避免普通问诊页面提前下载三维渲染代码。
 * @returns 三维人体场景组件
 */
async function loadThreeAnatomyScene() {
  return import('./ThreeAnatomyScene.vue')
}

const ThreeAnatomyScene = defineAsyncComponent(loadThreeAnatomyScene)

const props = defineProps<{
  systems: AtlasSystem[]
  modelId: AnatomyModelId
  modelName: string
  structureCount: number
  coverage: string
  regions: AtlasBodyRegion[]
  activeSystemId: string
  focusVersion: number
  selectedStructureNames: string[]
}>()

const emit = defineEmits<{
  select: [systemId: string]
  selectStructure: [selection: AnatomyStructureSelection]
}>()
const sceneRef = ref<AnatomySceneExposed | null>(null)
const isAutoRotating = ref(true)
const isPointerInside = ref(false)

/**
 * 选择三维人体中的系统并同步右侧医学说明。
 * @param systemId 人体系统标识
 */
function selectSystem(systemId: string) {
  emit('select', systemId)
}

/**
 * 转发三维人体点击的细分区域，供右侧面板展示并加入多部位选择。
 * @param selection 当前点击的系统和模型网格信息
 */
function selectStructure(selection: AnatomyStructureSelection) {
  emit('selectStructure', selection)
}

/**
 * 切换人体模型的自动旋转状态，保留用户手动拖拽能力。
 */
function toggleAutoRotate() {
  isAutoRotating.value = !isAutoRotating.value
  sceneRef.value?.setAutoRotate(isAutoRotating.value && !isPointerInside.value)
}

/**
 * 鼠标进入人体观察区域时临时暂停旋转，方便定位和点击细分部位。
 */
function pauseAutoRotateOnHover() {
  isPointerInside.value = true
  sceneRef.value?.setAutoRotate(false)
}

/**
 * 鼠标离开人体观察区域后，根据用户的旋转开关恢复动画。
 */
function resumeAutoRotateAfterHover() {
  isPointerInside.value = false
  sceneRef.value?.setAutoRotate(isAutoRotating.value)
}

/**
 * 将三维人体相机恢复到正面全身观察视角。
 */
function resetView() {
  sceneRef.value?.resetView()
}

/**
 * 聚焦最后选择的三维身体结构，未选择真实网格时不改变当前镜头。
 */
function focusSelectedStructure() {
  const rawName = [...props.selectedStructureNames].reverse().find(Boolean)
  if (rawName) sceneRef.value?.focusStructure(rawName)
}

/**
 * 将镜头定位到一个已知的原始三维网格。
 * @param rawName 三维模型节点的原始名称
 */
function focusStructure(rawName: string) {
  sceneRef.value?.focusStructure(rawName)
}

/**
 * 将镜头定位到与医学别名匹配的一组器官或牙位结构。
 * @param aliases 器官或科室配置的模型英文别名
 */
function focusAliases(aliases: string[]) {
  sceneRef.value?.focusStructureAliases(aliases)
}

defineExpose<BodyMapExposed>({ focusStructure, focusAliases })
</script>

<template>
  <div
    class="body-map"
    aria-label="Three.js 交互式三维人体系统图谱"
    @pointerenter="pauseAutoRotateOnHover"
    @pointerleave="resumeAutoRotateAfterHover"
  >
    <div class="body-grid" />
    <div class="anatomy-status">
      <i /> {{ modelName }} · {{ structureCount }} 个结构 · {{ coverage }}
    </div>

    <ThreeAnatomyScene
      :key="modelId"
      ref="sceneRef"
      :model-id="modelId"
      :active-system-id="activeSystemId"
      :focus-version="focusVersion"
      :regions="regions"
      :systems="systems"
      :selected-structure-names="selectedStructureNames"
      :auto-rotate="isAutoRotating && !isPointerInside"
      @select="selectSystem"
      @select-structure="selectStructure"
    />

    <div class="anatomy-controls" aria-label="三维视图控制">
      <button
        type="button"
        :class="{ active: isAutoRotating }"
        :aria-pressed="isAutoRotating"
        @click="toggleAutoRotate"
      >
        <i>↻</i>{{ isAutoRotating ? (isPointerInside ? '悬停已暂停' : '自动旋转中') : '自动旋转' }}
      </button>
      <button type="button" @click="resetView"><i>⌖</i>正面复位</button>
      <button
        type="button"
        :disabled="!selectedStructureNames.length"
        @click="focusSelectedStructure"
      >
        <i>◎</i>聚焦选中部位
      </button>
    </div>

    <div class="anatomy-interaction-hint">
      <span>左键旋转</span><i />
      <span>右键拖动</span><i />
      <span>指向部位滚轮缩放</span><i />
      <span>双击局部放大</span>
    </div>

    <a
      class="anatomy-credit"
      href="/anatomy/NOTICE"
      target="_blank"
      rel="noreferrer"
    >
      {{ modelId === 'female' ? 'NIH HRA / Visible Human Female · CC BY 4.0' : 'Z-Anatomy / BodyParts3D · CC BY-SA 4.0' }} ↗
    </a>

    <div class="body-axis"><span>CRANIAL</span><i /><span>CAUDAL</span></div>
    <div class="body-map-legend">
      <button
        v-for="system in systems"
        :key="system.id"
        type="button"
        :class="{ active: activeSystemId === system.id }"
        :style="{ '--system-color': system.color }"
        @click="selectSystem(system.id)"
      >
        <i />{{ system.name }}
      </button>
    </div>
  </div>
</template>
