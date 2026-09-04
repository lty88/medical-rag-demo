<script setup lang="tsx">
import { computed, ref } from 'vue'
import type { AtlasDepartment, AtlasSystem } from '../types'

const props = defineProps<{
  systems: AtlasSystem[]
  departments: AtlasDepartment[]
  activeSystemId: string
  activeDepartmentId: string
  disclaimer: string
}>()

const emit = defineEmits<{
  selectSystem: [systemId: string]
  selectDepartment: [department: AtlasDepartment]
}>()

const navigationMode = ref<'anatomy' | 'department'>('anatomy')
const departmentKeyword = ref('')

// 过滤科室导航项，根据关键词和科室属性进行匹配。
const filteredDepartments = computed(() => {
  const keyword = departmentKeyword.value.trim().toLowerCase()
  if (!keyword) return props.departments
  return props.departments.filter((department) => (
    [
      department.name,
      department.english_name,
      department.group,
      department.summary,
      ...department.common_reasons,
    ].some((value) => value.toLowerCase().includes(keyword))
  ))
})

// 对科室导航项进行分组，根据科室组别。
const groupedDepartments = computed(() => {
  const groups = new Map<string, AtlasDepartment[]>()
  for (const department of filteredDepartments.value) {
    groups.set(department.group, [...(groups.get(department.group) ?? []), department])
  }
  return [...groups.entries()].map(([name, departments]) => ({ name, departments }))
})

/**
 * 切换解剖图层或初诊科室导航模式。
 * @param mode 用户要查看的导航模式
 */
function switchNavigationMode(mode: 'anatomy' | 'department') {
  navigationMode.value = mode
}

/**
 * 读取科室搜索框内容并更新筛选关键词。
 * @param event 搜索框原生输入事件
 */
function updateDepartmentKeyword(event: Event) {
  departmentKeyword.value = (event.target as HTMLInputElement).value
}

/**
 * 选择一个解剖图层并通知页面同步三维场景。
 * @param systemId 人体解剖系统标识
 */
function selectSystem(systemId: string) {
  emit('selectSystem', systemId)
}

/**
 * 选择初诊科室并通知页面定位对应器官或身体区域。
 * @param department 包含三维聚焦信息的科室导航项
 */
function selectDepartment(department: AtlasDepartment) {
  emit('selectDepartment', department)
}
</script>

<template>
  <aside class="atlas-system-list atlas-navigation-panel">
    <nav class="atlas-navigation-tabs" aria-label="健康图谱导航方式">
      <button
        type="button"
        :class="{ active: navigationMode === 'anatomy' }"
        @click="switchNavigationMode('anatomy')"
      >
        3D 解剖图层
      </button>
      <button
        type="button"
        :class="{ active: navigationMode === 'department' }"
        @click="switchNavigationMode('department')"
      >
        初诊科室
      </button>
    </nav>

    <template v-if="navigationMode === 'anatomy'">
      <p class="atlas-navigation-label">ANATOMY LAYERS</p>
      <div class="atlas-layer-list">
        <button
          v-for="system in systems"
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
      </div>
    </template>

    <template v-else>
      <p class="atlas-navigation-label">OUTPATIENT GUIDE</p>
      <label class="department-search">
        <span>按科室或症状查找</span>
        <input
          :value="departmentKeyword"
          type="search"
          placeholder="例如：牙痛、眼痛、腹痛"
          @input="updateDepartmentKeyword"
        >
      </label>
      <div class="department-directory">
        <section v-for="group in groupedDepartments" :key="group.name">
          <h3>{{ group.name }}</h3>
          <button
            v-for="department in group.departments"
            :key="department.id"
            type="button"
            :class="{ active: activeDepartmentId === department.id }"
            @click="selectDepartment(department)"
          >
            <span>
              <strong>{{ department.name }}</strong>
              <small>{{ department.summary }}</small>
            </span>
            <b>{{ department.official_code }}</b>
          </button>
        </section>
        <p v-if="!groupedDepartments.length" class="department-empty">
          暂未找到匹配科室，可切换全科医疗科或直接在人体上选择部位。
        </p>
      </div>
    </template>

    <div class="atlas-boundary">
      <span>初诊导航边界</span>
      <p>科室名称和分科范围会因医院而异，急症危险信号优先于科室选择。</p>
      <p>{{ disclaimer }}</p>
    </div>
  </aside>
</template>
