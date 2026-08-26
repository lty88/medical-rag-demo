<script setup lang="tsx">
import { computed, ref, watch } from 'vue'
import { findAtlasOrgan, findBodyRegion } from '../anatomy/regions'
import type { AnatomyStructureSelection } from '../anatomy/types'
import AtlasRegionInspector from './AtlasRegionInspector.vue'
import AnatomyModelSwitch from './AnatomyModelSwitch.vue'
import BodyMap from './BodyMap.vue'
import type {
  AtlasBodyRegion,
  AnatomyModelId,
  AtlasComplaintSelection,
  AtlasConsultContext,
  AtlasOrgan,
  AtlasSymptomOption,
  BodyAtlasResponse,
} from '../types'

const props = defineProps<{ atlas: BodyAtlasResponse | null }>()
const emit = defineEmits<{ startConsult: [context: AtlasConsultContext] }>()

const activeSystemId = ref('regional')
const activeModelId = ref<AnatomyModelId>('male')
const activeOrganId = ref('')
const activeRegionId = ref('')
const selectedComplaints = ref<AtlasComplaintSelection[]>([])
const maximumSelectedRegions = 12
const systemFocusVersion = ref(0)

const activeSystem = computed(
  () => visibleSystems.value.find((system) => system.id === activeSystemId.value) ?? null,
)
const activeModel = computed(
  () => props.atlas?.models.find((model) => model.id === activeModelId.value) ?? null,
)
const visibleSystems = computed(
  () => props.atlas?.systems.filter(
    (system) => system.available_models.includes(activeModelId.value),
  ).map((system) => ({
    ...system,
    organs: system.organs.filter(
      (organ) => organ.available_models.includes(activeModelId.value),
    ),
  })) ?? [],
)
const activeOrgan = computed(
  () => activeSystem.value?.organs.find((organ) => organ.id === activeOrganId.value)
    ?? activeSystem.value?.organs[0]
    ?? null,
)
const activeRegion = computed(
  () => props.atlas?.body_regions.find((region) => region.id === activeRegionId.value) ?? null,
)

/**
 * 切换人体系统并默认选择该系统的第一个器官。
 * @param systemId 人体系统标识
 */
function selectSystem(systemId: string) {
  activeSystemId.value = systemId
  systemFocusVersion.value += 1
  const system = props.atlas?.systems.find((item) => item.id === systemId)
  activeOrganId.value = system?.organs[0]?.id ?? ''
}

/**
 * 切换医学解剖参考模型，并清理不能跨模型可靠映射的网格选择。
 * @param modelId 男性全身或女性腹盆躯干模型标识
 */
function selectModel(modelId: AnatomyModelId) {
  if (activeModelId.value === modelId) return
  activeModelId.value = modelId
  selectedComplaints.value = []
  activeRegionId.value = ''
  const firstSystemId = props.atlas?.models
    .find((model) => model.id === modelId)
    ?.available_system_ids[0] ?? ''
  selectSystem(firstSystemId)
}

/**
 * 选择当前人体系统中的器官；再次点击已选器官时从多选清单移除。
 * @param organId 器官标识
 */
function selectOrgan(organId: string) {
  activeOrganId.value = organId
  const organ = activeSystem.value?.organs.find((item) => item.id === organId)
  if (organ && activeSystem.value) {
    const complaintId = buildOrganComplaintId(activeSystem.value.id, organ.id)
    if (selectedComplaints.value.some((item) => item.region_id === complaintId)) {
      removeComplaint(complaintId)
    }
    else {
      addComplaint(complaintId, organ.name, '')
    }
  }
}

/**
 * 生成不会与体表区域冲突的器官多选标识。
 * @param systemId 器官所属系统标识
 * @param organId 器官标识
 * @returns 用于症状卡片的稳定复合标识
 */
function buildOrganComplaintId(systemId: string, organId: string) {
  return `organ:${systemId}:${organId}`
}

/**
 * 将体表部位或内部器官加入多选症状清单。
 * @param regionId 身体部位或器官复合标识
 * @param regionName 面向用户展示的中文名称
 * @param structureLabel 对应的原始三维网格名称
 */
function addComplaint(regionId: string, regionName: string, structureLabel: string) {
  if (selectedComplaints.value.some((item) => item.region_id === regionId)) return
  if (selectedComplaints.value.length >= maximumSelectedRegions) return
  selectedComplaints.value = [
    ...selectedComplaints.value,
    {
      region_id: regionId,
      region_name: regionName,
      structure_label: structureLabel,
      symptoms: [],
      description: '',
    },
  ]
}

/**
 * 将点击的三维模型网格解析为中文身体区域，并切换其多选状态。
 * @param selection 三维场景返回的系统和原始网格名称
 */
function selectStructure(selection: AnatomyStructureSelection) {
  if (!props.atlas) return
  if (selection.systemId === 'regional') {
    const region = findBodyRegion(selection.rawName, props.atlas.body_regions)
    if (!region) return
    activeSystemId.value = 'regional'
    activeRegionId.value = region.id
    if (selectedComplaints.value.some((item) => item.region_id === region.id)) {
      removeComplaint(region.id)
      return
    }
    addComplaint(region.id, region.name, selection.rawName)
    return
  }
  const system = props.atlas.systems.find((item) => item.id === selection.systemId)
  if (!system) return
  const organ = findAtlasOrgan(selection.rawName, system.organs) ?? system.organs[0]
  if (!organ) return
  activeSystemId.value = system.id
  activeOrganId.value = organ.id
  const complaintId = buildOrganComplaintId(system.id, organ.id)
  if (selectedComplaints.value.some((item) => item.region_id === complaintId)) {
    removeComplaint(complaintId)
    return
  }
  addComplaint(complaintId, organ.name, selection.rawName)
}

/**
 * 为某个身体区域勾选或取消一个通俗症状表现。
 * @param region 当前身体区域
 * @param symptom 用户点击的症状选项
 */
function toggleRegionSymptom(region: AtlasBodyRegion, symptom: AtlasSymptomOption) {
  const current = selectedComplaints.value.find((item) => item.region_id === region.id)
  if (!current) {
    if (selectedComplaints.value.length >= maximumSelectedRegions) return
    selectedComplaints.value = [
      ...selectedComplaints.value,
      {
        region_id: region.id,
        region_name: region.name,
        structure_label: '',
        symptoms: [symptom],
        description: '',
      },
    ]
    return
  }
  const selected = current.symptoms.some((item) => item.id === symptom.id)
  selectedComplaints.value = selectedComplaints.value.map((item) => (
    item.region_id === region.id
      ? {
          ...item,
          symptoms: selected
            ? item.symptoms.filter((option) => option.id !== symptom.id)
            : [...item.symptoms, symptom],
        }
      : item
  ))
}

/**
 * 为内部器官勾选或取消快捷症状，并确保器官已加入多选清单。
 * @param organ 当前系统中选中的内部器官
 * @param symptom 用户点击的症状选项
 */
function toggleOrganSymptom(organ: AtlasOrgan, symptom: AtlasSymptomOption) {
  if (!activeSystem.value) return
  const complaintId = buildOrganComplaintId(activeSystem.value.id, organ.id)
  addComplaint(complaintId, organ.name, '')
  const current = selectedComplaints.value.find((item) => item.region_id === complaintId)
  if (!current) return
  const selected = current.symptoms.some((item) => item.id === symptom.id)
  selectedComplaints.value = selectedComplaints.value.map((item) => (
    item.region_id === complaintId
      ? {
          ...item,
          symptoms: selected
            ? item.symptoms.filter((option) => option.id !== symptom.id)
            : [...item.symptoms, symptom],
        }
      : item
  ))
}

/**
 * 更新某个已选身体部位的用户自由症状描述。
 * @param regionId 身体区域标识
 * @param description 用户对该部位不适的具体描述
 */
function updateComplaintDescription(regionId: string, description: string) {
  selectedComplaints.value = selectedComplaints.value.map((item) => (
    item.region_id === regionId ? { ...item, description } : item
  ))
}

/**
 * 从待问诊清单移除一个身体部位。
 * @param regionId 要移除的身体区域标识
 */
function removeComplaint(regionId: string) {
  selectedComplaints.value = selectedComplaints.value.filter((item) => item.region_id !== regionId)
  if (activeRegionId.value === regionId) activeRegionId.value = ''
}

/**
 * 从已选清单重新打开某个身体部位的说明与症状选项。
 * @param regionId 要查看的身体区域标识
 */
function focusComplaint(regionId: string) {
  if (regionId.startsWith('organ:')) {
    const [, systemId, organId] = regionId.split(':')
    activeSystemId.value = systemId ?? activeSystemId.value
    activeOrganId.value = organId ?? ''
    return
  }
  activeSystemId.value = 'regional'
  activeRegionId.value = regionId
}

/**
 * 将当前系统和器官的导航信息发送到智能问诊工作区。
 */
function startConsult() {
  if (!activeSystem.value) return
  if (!selectedComplaints.value.length) return
  const isRegional = activeSystem.value.id === 'regional'
  const focusedName = isRegional
    ? activeRegion.value?.name ?? '身体部位'
    : activeOrgan.value?.name ?? activeSystem.value.name
  emit('startConsult', {
    anatomy_model: activeModelId.value,
    system_id: activeSystem.value.id,
    system_name: activeSystem.value.name,
    organ_id: isRegional
      ? activeRegion.value?.id ?? 'regional-selection'
      : activeOrgan.value?.id ?? activeSystem.value.id,
    organ_name: selectedComplaints.value.length > 1
      ? `${selectedComplaints.value.length} 个身体部位`
      : focusedName,
    organ_summary: isRegional
      ? activeRegion.value?.summary ?? activeSystem.value.summary
      : activeOrgan.value?.summary ?? activeSystem.value.summary,
    observation: isRegional
      ? '用户通过人体图谱主动定位了不舒服的身体部位。'
      : activeOrgan.value?.observation ?? activeSystem.value.summary,
    complaints: selectedComplaints.value.map((item) => ({
      ...item,
      symptoms: item.symptoms.map((symptom) => ({ ...symptom })),
    })),
  })
}

watch(
  () => props.atlas,
  (value) => {
    if (value && !value.models.some((model) => model.id === activeModelId.value)) {
      activeModelId.value = value.default_model
    }
    if (value && !value.systems.some((system) => system.id === activeSystemId.value)) {
      selectSystem(value.systems[0]?.id ?? '')
    }
  },
)
</script>

<template>
  <section class="atlas-workspace">
    <header class="atlas-heading">
      <div>
        <p class="science-kicker">HUMAN SYSTEMS / INTERACTIVE ATLAS</p>
        <h2>{{ atlas?.title ?? '人体系统交互图谱' }}</h2>
        <p>{{ atlas?.description ?? '正在读取人体系统数据…' }}</p>
      </div>
      <AnatomyModelSwitch
        v-if="atlas"
        :models="atlas.models"
        :active-model-id="activeModelId"
        @select="selectModel"
      />
    </header>

    <div v-if="atlas" class="atlas-layout">
      <aside class="atlas-system-list">
        <p>SYSTEM LAYERS</p>
        <button
          v-for="system in visibleSystems"
          :key="system.id"
          type="button"
          :class="{ active: activeSystemId === system.id }"
          :style="{ '--system-color': system.color }"
          @click="selectSystem(system.id)"
        >
          <i />
          <span><strong>{{ system.name }}</strong><small>{{ system.english_name }}</small></span>
          <b>↗</b>
        </button>
        <div class="atlas-boundary">
          <span>SAFETY BOUNDARY</span>
          <p>{{ atlas.disclaimer }}</p>
        </div>
      </aside>

      <BodyMap
        v-if="activeModel"
        :systems="visibleSystems"
        :model-id="activeModelId"
        :model-name="activeModel.name"
        :structure-count="activeModel.structure_count"
        :coverage="activeModel.coverage"
        :regions="atlas.body_regions"
        :active-system-id="activeSystemId"
        :focus-version="systemFocusVersion"
        :selected-structure-names="selectedComplaints.map((item) => item.structure_label).filter(Boolean)"
        @select="selectSystem"
        @select-structure="selectStructure"
      />

      <AtlasRegionInspector
        v-if="activeSystem"
        :active-system="activeSystem"
        :active-organ="activeOrgan"
        :active-region="activeRegion"
        :selected-complaints="selectedComplaints"
        @select-organ="selectOrgan"
        @toggle-symptom="toggleRegionSymptom"
        @toggle-organ-symptom="toggleOrganSymptom"
        @update-description="updateComplaintDescription"
        @remove-complaint="removeComplaint"
        @focus-complaint="focusComplaint"
        @start-consult="startConsult"
      />
    </div>

    <div v-else class="workspace-empty">人体系统数据暂不可用，请确认后端服务。</div>
  </section>
</template>
