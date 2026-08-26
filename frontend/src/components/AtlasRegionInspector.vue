<script setup lang="tsx">
import type {
  AtlasBodyRegion,
  AtlasComplaintSelection,
  AtlasOrgan,
  AtlasSymptomOption,
  AtlasSystem,
} from '../types'

const props = defineProps<{
  activeSystem: AtlasSystem
  activeOrgan: AtlasOrgan | null
  activeRegion: AtlasBodyRegion | null
  selectedComplaints: AtlasComplaintSelection[]
}>()

const emit = defineEmits<{
  selectOrgan: [organId: string]
  toggleSymptom: [region: AtlasBodyRegion, symptom: AtlasSymptomOption]
  toggleOrganSymptom: [organ: AtlasOrgan, symptom: AtlasSymptomOption]
  updateDescription: [regionId: string, description: string]
  removeComplaint: [regionId: string]
  focusComplaint: [regionId: string]
  startConsult: []
}>()

/**
 * 判断当前身体区域是否已经勾选某个症状表现。
 * @param regionId 身体区域标识
 * @param symptomId 症状选项标识
 * @returns 该症状是否处于已选状态
 */
function isSymptomSelected(regionId: string, symptomId: string) {
  return props.selectedComplaints
    .find((complaint) => complaint.region_id === regionId)
    ?.symptoms.some((symptom) => symptom.id === symptomId) ?? false
}

/**
 * 判断某个身体部位或器官是否已经加入多选清单。
 * @param complaintId 身体区域标识或器官复合标识
 * @returns 当前部位是否处于已选状态
 */
function isComplaintSelected(complaintId: string) {
  return props.selectedComplaints.some((complaint) => complaint.region_id === complaintId)
}

/**
 * 生成与父组件一致的器官症状卡片标识。
 * @param systemId 器官所属系统标识
 * @param organId 器官标识
 * @returns 器官在多选清单中的复合标识
 */
function buildOrganComplaintId(systemId: string, organId: string) {
  return `organ:${systemId}:${organId}`
}

/**
 * 判断所有已选身体部位是否至少标注了一种具体不适。
 * @returns 是否可以携带完整的部位和症状进入智能问诊
 */
function canStartConsult() {
  if (!props.selectedComplaints.length) return false
  return props.selectedComplaints.every((complaint) => (
    complaint.symptoms.length > 0 || Boolean(complaint.description.trim())
  ))
}

/**
 * 从文本框输入事件中读取症状描述并同步到对应身体部位。
 * @param regionId 当前编辑的身体区域标识
 * @param event 文本框原生输入事件
 */
function updateDescription(regionId: string, event: Event) {
  const target = event.target as HTMLTextAreaElement
  emit('updateDescription', regionId, target.value)
}

/**
 * 判断某个已选部位是否已有固定症状或自由文字描述。
 * @param complaint 当前已选择的身体部位
 * @returns 该部位是否已有可带入问诊的症状信息
 */
function hasComplaintDetail(complaint: AtlasComplaintSelection) {
  return complaint.symptoms.length > 0 || Boolean(complaint.description.trim())
}
</script>

<template>
  <aside class="atlas-inspector">
    <template v-if="activeSystem.id === 'regional'">
      <p class="science-kicker">REGIONAL ANATOMY / MULTI-SELECT</p>
      <h3>指出哪里不舒服</h3>
      <p class="system-summary">直接点击三维人体的具体位置。可继续旋转到背面，也可以连续选择多个部位。</p>

      <article v-if="activeRegion" class="region-detail-card">
        <span>当前定位 · {{ activeRegion.group }}</span>
        <h4>{{ activeRegion.name }}</h4>
        <p class="region-location"><b>怎么找到：</b>{{ activeRegion.location }}</p>
        <p>{{ activeRegion.summary }}</p>

        <div class="region-symptom-picker">
          <strong>这里怎么不舒服？可多选</strong>
          <button
            v-for="symptom in activeRegion.symptom_options"
            :key="symptom.id"
            type="button"
            :class="{ active: isSymptomSelected(activeRegion.id, symptom.id) }"
            :aria-pressed="isSymptomSelected(activeRegion.id, symptom.id)"
            @click="emit('toggleSymptom', activeRegion, symptom)"
          >
            <i>{{ isSymptomSelected(activeRegion.id, symptom.id) ? '✓' : '+' }}</i>
            {{ symptom.label }}
          </button>
        </div>
      </article>

      <div v-else class="region-empty-state">
        <i>⌖</i>
        <strong>请在人体上点击具体位置</strong>
        <span>例如左上腹、右膝盖、后颈或手腕，不需要知道医学名称。</span>
      </div>

    </template>

    <template v-else>
      <p class="science-kicker">{{ activeSystem.english_name }}</p>
      <h3>{{ activeSystem.name }}</h3>
      <p class="system-summary">{{ activeSystem.summary }}</p>
      <div class="organ-tabs">
        <button
          v-for="organ in activeSystem.organs"
          :key="organ.id"
          type="button"
          :class="{
            active: activeOrgan?.id === organ.id,
            selected: isComplaintSelected(buildOrganComplaintId(activeSystem.id, organ.id)),
          }"
          :aria-pressed="isComplaintSelected(buildOrganComplaintId(activeSystem.id, organ.id))"
          @click="emit('selectOrgan', organ.id)"
        >
          {{ organ.name }}
          <i v-if="isComplaintSelected(buildOrganComplaintId(activeSystem.id, organ.id))">✓</i>
        </button>
      </div>
      <article v-if="activeOrgan" class="organ-observation">
        <span>SELECTED ORGAN</span>
        <h4>{{ activeOrgan.name }}</h4>
        <p>{{ activeOrgan.summary }}</p>
        <div><b>需要关注</b>{{ activeOrgan.observation }}</div>
      </article>
      <div v-if="activeOrgan?.symptom_options.length" class="region-symptom-picker organ-symptom-picker">
        <strong>{{ activeOrgan.name }}怎么不舒服？可多选</strong>
        <button
          v-for="symptom in activeOrgan.symptom_options"
          :key="symptom.id"
          type="button"
          :class="{
            active: isSymptomSelected(
              buildOrganComplaintId(activeSystem.id, activeOrgan.id),
              symptom.id,
            ),
          }"
          :aria-pressed="isSymptomSelected(
            buildOrganComplaintId(activeSystem.id, activeOrgan.id),
            symptom.id,
          )"
          @click="emit('toggleOrganSymptom', activeOrgan, symptom)"
        >
          <i>{{ isSymptomSelected(
            buildOrganComplaintId(activeSystem.id, activeOrgan.id),
            symptom.id,
          ) ? '✓' : '+' }}</i>
          {{ symptom.label }}
        </button>
      </div>
      <section class="atlas-scope-card">
        <span>当前视图用途</span>
        <dl>
          <div><dt>结构认知</dt><dd>SUPPORTED</dd></div>
          <div><dt>症状导航</dt><dd>SUPPORTED</dd></div>
          <div><dt>个体诊断</dt><dd>NOT ALLOWED</dd></div>
        </dl>
      </section>
    </template>

    <section class="selected-region-list persistent-selection-list">
      <header>
        <span>已选择的部位与器官 · 最多 12 个</span>
        <b>{{ selectedComplaints.length }}</b>
      </header>
      <div v-if="!selectedComplaints.length" class="selection-list-empty">
        点击人体部位、内部器官，或上方器官标签后，会在这里生成独立症状卡片。
      </div>
      <article v-for="complaint in selectedComplaints" :key="complaint.region_id">
        <header>
          <button type="button" @click="emit('focusComplaint', complaint.region_id)">
            <strong>{{ complaint.region_name }}</strong>
            <small>返回查看部位说明与快捷症状</small>
          </button>
          <button type="button" aria-label="移除这个部位" @click="emit('removeComplaint', complaint.region_id)">×</button>
        </header>
        <div v-if="complaint.symptoms.length" class="complaint-symptom-tags">
          <span v-for="symptom in complaint.symptoms" :key="symptom.id">{{ symptom.label }}</span>
        </div>
        <label>
          <span>单独描述这个部位的症状</span>
          <textarea
            :value="complaint.description"
            rows="3"
            maxlength="500"
            :placeholder="`例如：${complaint.region_name}从昨晚开始隐隐痛，按压时更明显…`"
            @input="updateDescription(complaint.region_id, $event)"
          />
          <small>{{ complaint.description.length }} / 500</small>
        </label>
      </article>
    </section>
    <p v-if="selectedComplaints.some((complaint) => !hasComplaintDetail(complaint))" class="atlas-selection-hint">
      请为每个部位选择快捷症状，或者在对应卡片中输入具体描述。
    </p>

    <button
      class="atlas-consult-button"
      type="button"
      :disabled="!canStartConsult()"
      @click="emit('startConsult')"
    >
      一键带入 {{ selectedComplaints.length || 1 }} 个部位到智能问诊 <span>→</span>
    </button>
  </aside>
</template>
