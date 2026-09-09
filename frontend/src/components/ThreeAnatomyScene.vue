<script setup lang="tsx">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { createAnatomyScene } from '../anatomy/scene'
import { resolveStructureLabel as resolveRegionLabel } from '../anatomy/regions'
import type {
  AnatomyHoverInfo,
  AnatomyModelId,
  AnatomySceneController,
  AnatomySceneExposed,
  AnatomyStructureSelection,
  AnatomySystemId,
} from '../anatomy/types'
import type { AtlasBodyRegion, AtlasSystem } from '../types'

const props = defineProps<{
  modelId: AnatomyModelId
  activeSystemId: string
  focusVersion: number
  regions: AtlasBodyRegion[]
  systems: AtlasSystem[]
  selectedStructureNames: string[]
  autoRotate: boolean
}>()
const emit = defineEmits<{
  select: [systemId: string]
  selectStructure: [selection: AnatomyStructureSelection]
}>()

const containerRef = ref<HTMLElement | null>(null)
const hoverInfo = ref<AnatomyHoverInfo | null>(null)
const isReady = ref(false)
const hasError = ref(false)
const loadingProgress = ref(0)
const loadedSystemIds = ref<AnatomySystemId[]>([])
const failedSystemIds = ref<AnatomySystemId[]>([])

let controller: AnatomySceneController | null = null
let resizeObserver: ResizeObserver | null = null
let isDisposed = false
let pendingStructureName = ''
let pendingStructureAliases: string[] = []

/**
 * 将三维场景点击的系统标识传递给人体图谱页面。
 * @param systemId 被点击器官所属的系统标识
 */
function handleSystemSelect(systemId: AnatomySystemId) {
  emit('select', systemId)
}

/**
 * 将三维模型点击的精细身体结构传递给人体图谱页面。
 * @param selection 系统、中文标签与原始网格名称
 */
function handleStructureSelect(selection: AnatomyStructureSelection) {
  emit('selectStructure', selection)
}

/**
 * 把 GLB 技术节点名转换为普通用户可读的中文部位名称。
 * @param rawName 三维模型原始网格名称
 * @param systemId 网格实际所属系统，用于查找对应的中文器官目录
 * @returns 匹配后的中文身体区域名称
 */
function resolveStructureLabel(rawName: string, systemId: AnatomySystemId) {
  return resolveRegionLabel(rawName, props.regions, props.systems, systemId)
}

/**
 * 同步当前鼠标指向的器官信息，用于显示浮动标签。
 * @param info 器官名称、系统标识及画布内坐标
 */
function handleOrganHover(info: AnatomyHoverInfo | null) {
  hoverInfo.value = info
}

/**
 * 在容器尺寸变化后同步 Three.js 相机和画布尺寸。
 */
function handleResize() {
  controller?.resize()
}

/**
 * 更新真实 GLB 解剖层的整体加载进度。
 * @param progress 当前加载百分比
 */
function handleLoadProgress(progress: number) {
  loadingProgress.value = progress
}

/**
 * 记录当前性别模型成功与失败的解剖图层，允许部分资源缺失时继续使用。
 * @param loadedIds 已成功载入的系统标识
 * @param failedIds 加载失败的系统标识
 */
function handleLayerStatus(loadedIds: AnatomySystemId[], failedIds: AnatomySystemId[]) {
  loadedSystemIds.value = loadedIds
  failedSystemIds.value = failedIds
}

/**
 * 异步初始化高精度人体场景并建立尺寸观察器；失败时切换为二维安全降级图。
 */
async function initializeScene() {
  if (!containerRef.value) {
    return
  }
  try {
    const nextController = await createAnatomyScene(containerRef.value, {
      modelId: props.modelId,
      activeSystemId: props.activeSystemId,
      onSystemSelect: handleSystemSelect,
      onStructureSelect: handleStructureSelect,
      onHover: handleOrganHover,
      onProgress: handleLoadProgress,
      onLayerStatus: handleLayerStatus,
      resolveStructureLabel,
    })
    if (isDisposed) {
      nextController.dispose()
      return
    }
    controller = nextController
    controller.setSelectedStructures(props.selectedStructureNames)
    controller.setAutoRotate(props.autoRotate)
    if (pendingStructureName) {
      controller.focusStructure(pendingStructureName)
      pendingStructureName = ''
    }
    if (pendingStructureAliases.length) {
      controller.focusStructureAliases(pendingStructureAliases)
      pendingStructureAliases = []
    }
    resizeObserver = new ResizeObserver(handleResize)
    resizeObserver.observe(containerRef.value)
    isReady.value = true
  }
  catch (error) {
    hasError.value = true
    console.warn('[人体三维图谱] WebGL 初始化失败，已切换二维降级视图。', error)
  }
}

/**
 * 读取父组件当前选中的人体系统标识。
 * @returns 当前系统标识
 */
function getActiveSystemId() {
  return props.activeSystemId
}

/**
 * 将外部菜单选择同步到三维器官材质高亮状态。
 * @param systemId 新选中的人体系统标识
 */
function syncActiveSystem(systemId: string) {
  controller?.setActiveSystem(systemId)
  controller?.focusSystem(systemId)
}

/**
 * 读取系统菜单的重复聚焦请求版本号。
 * @returns 每次点击系统菜单都会递增的版本号
 */
function getFocusVersion() {
  return props.focusVersion
}

/**
 * 即使系统标识未变化，也重新将相机定位并缩放到整个系统。
 */
function refocusActiveSystem() {
  controller?.focusSystem(props.activeSystemId)
}

/**
 * 读取父组件中全部已选三维网格名称。
 * @returns 当前多部位选择对应的原始模型节点名称
 */
function getSelectedStructureNames() {
  return props.selectedStructureNames
}

/**
 * 将多部位选择同步为 Three.js 模型上的持续高亮。
 * @param rawNames 已选身体区域的原始模型节点名称
 */
function syncSelectedStructures(rawNames: string[]) {
  controller?.setSelectedStructures(rawNames)
}

/**
 * 读取父组件中的自动旋转开关状态。
 * @returns 当前是否启用自动旋转
 */
function getAutoRotate() {
  return props.autoRotate
}

/**
 * 将界面旋转开关同步到 Three.js 动画控制器。
 * @param enabled 是否启用人体模型自动旋转
 */
function syncAutoRotate(enabled: boolean) {
  controller?.setAutoRotate(enabled)
}

/**
 * 将三维相机恢复到正面全身视角。
 */
function resetView() {
  controller?.resetView()
}

/**
 * 将三维镜头定位到指定原始网格，便于观察已选择的局部身体结构。
 * @param rawName 三维模型中的原始结构名称
 */
function focusStructure(rawName: string) {
  if (controller) {
    controller.focusStructure(rawName)
    return
  }
  pendingStructureName = rawName
}

/**
 * 将三维镜头定位到符合一组医学别名的结构集合。
 * @param aliases 科室或器官配置的英文模型别名
 */
function focusStructureAliases(aliases: string[]) {
  if (controller) {
    controller.focusStructureAliases(aliases)
    return
  }
  pendingStructureAliases = [...aliases]
}

/**
 * 设置三维人体是否保持缓慢自动旋转。
 * @param enabled 是否启用自动旋转
 */
function setAutoRotate(enabled: boolean) {
  controller?.setAutoRotate(enabled)
}

/**
 * 释放尺寸监听器、动画循环及 WebGL 显存资源。
 */
function disposeScene() {
  isDisposed = true
  resizeObserver?.disconnect()
  resizeObserver = null
  controller?.dispose()
  controller = null
}

watch(getActiveSystemId, syncActiveSystem)
watch(getFocusVersion, refocusActiveSystem)
watch(getSelectedStructureNames, syncSelectedStructures, { deep: true })
watch(getAutoRotate, syncAutoRotate)
onMounted(initializeScene)
onBeforeUnmount(disposeScene)

defineExpose<AnatomySceneExposed>({
  resetView,
  focusStructure,
  focusStructureAliases,
  setAutoRotate,
})
</script>

<template>
  <div class="three-anatomy-stage">
    <div ref="containerRef" class="three-anatomy-host" />

    <div v-if="!isReady && !hasError" class="three-anatomy-loading" aria-live="polite">
      <i />
      <span>正在载入{{ modelId === 'female' ? '女性腹盆躯干' : '男性全身' }}模型 · {{ loadingProgress }}%</span>
      <small>医学分层 GLB · Draco 压缩</small>
    </div>

    <div v-if="hasError" class="three-anatomy-fallback">
      <img
        v-if="modelId === 'male'"
        src="/assets/human-anatomy-atlas.png"
        alt="人体正面解剖结构二维降级视图"
      >
      <span>
        {{ modelId === 'female'
          ? '女性解剖资源尚未完整载入，请切换男性全身参考或检查静态模型文件'
          : '当前设备未启用 WebGL，已展示二维安全视图' }}
      </span>
    </div>

    <div v-if="isReady && failedSystemIds.length" class="three-anatomy-partial" role="status">
      已载入 {{ loadedSystemIds.length }} 层，{{ failedSystemIds.length }} 层资源暂不可用
    </div>

    <div
      v-if="hoverInfo && !hasError"
      class="three-organ-tooltip"
      :style="{ left: `${hoverInfo.x}px`, top: `${hoverInfo.y}px` }"
    >
      <i />
      <span>{{ hoverInfo.label }}</span>
      <small>点击选择 · 双击局部放大</small>
    </div>
  </div>
</template>
