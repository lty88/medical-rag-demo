import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import { resolveStructureLabel } from '../src/anatomy/regions.ts'

const systems = [
  {
    id: 'urinary', name: '泌尿系统', organs: [
      { name: '肾脏和肾盂', mesh_aliases: ['kidney', 'renal pelvis'] },
      { name: '输尿管', mesh_aliases: ['ureter'] },
      { name: '膀胱', mesh_aliases: ['urinary bladder'] },
    ],
  },
  {
    id: 'digestive', name: '消化系统', organs: [
      { name: '胃', mesh_aliases: ['stomach'] },
      { name: '肝脏', mesh_aliases: ['liver'] },
      { name: '大肠和阑尾', mesh_aliases: ['colon', 'appendix'] },
    ],
  },
]

/** 验证截图中的英文名称及原始左右侧节点都转换为中文，不混淆左右肾。 */
function checkSelectedNames() {
  const cases = [
    ['Kidneyl', '左侧肾脏'], ['Kidneyr', '右侧肾脏'],
    ['Kidney.l', '左侧肾脏'], ['Kidney.r', '右侧肾脏'],
    ['Urinary bladder', '膀胱'], ['Ureterr', '右侧输尿管'],
    ['Renal pelvis.l', '左侧肾盂'], ['Renal pelvisr', '右侧肾盂'],
    ['VH_F_renal_papilla_L_a', '左侧肾乳头'],
    ['VH_F_right_ureter', '右侧输尿管'],
    ['VH_F_kidney_capsule_R', '右侧肾纤维囊'],
  ]
  for (const [rawName, expected] of cases) {
    assert.equal(resolveStructureLabel(rawName, [], systems, 'urinary'), expected)
  }
}

/** 验证非泌尿系统复用中文目录、未识别节点明确待确认，且肝脏名称不会误判为右侧。 */
function checkCatalogFallback() {
  assert.equal(resolveStructureLabel('Stomach', [], systems, 'digestive'), '胃')
  assert.equal(resolveStructureLabel('Liver', [], systems, 'digestive'), '肝脏')
  assert.equal(resolveStructureLabel('Ascending colon', [], systems, 'digestive'), '大肠和阑尾（所属部位）')
  assert.equal(resolveStructureLabel('unknown_mesh', [], systems, 'digestive'), '消化系统结构（具体部位待确认）')
  assert.equal(resolveStructureLabel('Stomach', [], systems, 'urinary'), '泌尿系统结构（具体部位待确认）')
  const regions = [{ name: '左侧腰部', mesh_aliases: ['surface_waist_l'] }]
  assert.equal(resolveStructureLabel('surface_waist_l', regions, systems, 'regional'), '左侧腰部')
}

/** 验证牙位侧别在 Three.js 删除句点后仍保留，不影响现有精细牙位标签。 */
function checkDentalLabels() {
  for (const rawName of ['Upper first molar tooth.l', 'Upper first molar toothl']) {
    assert.equal(resolveStructureLabel(rawName, [], systems, 'digestive'), '左侧上颌第一磨牙（FDI 26）')
  }
}

/** 检查真实 GLB 的 JSON 节点而不解码三维几何，验证男女泌尿模型的精细中文名称覆盖。 */
function checkRenalAssets() {
  for (const file of ['renal_male.glb', 'renal_female.glb']) {
    const buffer = readFileSync(new URL(`../public/anatomy/${file}`, import.meta.url))
    const gltf = JSON.parse(buffer.subarray(20, 20 + buffer.readUInt32LE(12)).toString())
    for (const node of gltf.nodes) {
      if (node.mesh === undefined) continue
      // GLTFLoader 的节点名称清理会移除句点；两种名称都要支持。
      for (const rawName of [node.name, node.name.replace(/\./g, '')]) {
        const label = resolveStructureLabel(rawName, [], systems, 'urinary')
        assert.match(label, /[\u4e00-\u9fff]/, rawName)
        assert.doesNotMatch(label, /所属部位|待确认|[a-z]/i, rawName)
      }
    }
  }
}

test('已选部位和左右侧中文名称', checkSelectedNames)
test('中文目录复用及安全兜底', checkCatalogFallback)
test('精细牙位名称兼容', checkDentalLabels)
test('真实男女泌尿模型节点覆盖', checkRenalAssets)
