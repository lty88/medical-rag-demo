import type { AtlasBodyRegion, AtlasOrgan, AtlasSystem } from '../types'

// 目录中的器官可能是分组名称；这些真实模型节点需要保留更细的中文结构名。
const preciseStructureNames: Record<string, string> = {
  kidney: '肾脏',
  'renal pelvis': '肾盂',
  ureter: '输尿管',
  urethra: '尿道',
  'urinary bladder': '膀胱',
  'kidney capsule': '肾纤维囊',
  'hilum of kidney': '肾门',
  'renal papilla': '肾乳头',
  'renal pyramid': '肾锥体',
  'renal column': '肾柱',
  'outer cortex of kidney': '肾皮质',
  'fundus of urinary bladder dome': '膀胱顶部',
  'fundus of urinary bladder base': '膀胱底',
  'urinary bladder neck smooth muscle': '膀胱颈平滑肌',
  'trigone of urinary bladder': '膀胱三角',
  'ureteral orifice': '输尿管口',
}

/**
 * 从模型节点中提取明确标注的左右侧，不根据屏幕位置推断人体侧别。
 * @param rawName 原始或经 Three.js 清理后的网格名称
 * @param organs 当前系统的器官目录，用于识别被移除句点的 l/r 后缀
 * @returns 中文侧别前缀；模型未明确标注时返回空字符串
 */
function resolveStructureSide(rawName: string, organs: AtlasOrgan[]): string {
  const target = normalizeStructureName(rawName)
  if (/(?:^|[\s.(])(?:l|left)(?=$|[\s.)])/i.test(target)) return '左侧'
  if (/(?:^|[\s.(])(?:r|right)(?=$|[\s.)])/i.test(target)) return '右侧'
  const bases = [...Object.keys(preciseStructureNames), ...organs.flatMap((organ) => organ.mesh_aliases)]
  for (const base of bases) {
    const name = normalizeStructureName(base)
    if (target === `${name}l`) return '左侧'
    if (target === `${name}r`) return '右侧'
  }
  if (/(?:tooth|incisor|canine|premolar|molar)l$/i.test(target)) return '左侧'
  if (/(?:tooth|incisor|canine|premolar|molar)r$/i.test(target)) return '右侧'
  return ''
}

/**
 * 按已核对的模型节点名称解析精细结构，避免将肾盂等子结构泛化为整个器官。
 * @param rawName 原始或经 Three.js 清理后的网格名称
 * @param side 已识别的中文侧别
 * @returns 精细中文标签；没有精确映射时返回 null
 */
function resolvePreciseStructureLabel(rawName: string, side: string): string | null {
  const target = normalizeStructureName(rawName)
    .replace(/^vh f /, '')
    .replace(/\b(?:left|right)\b/g, '')
    .replace(/(?:[.\s][lr])(?:\s[a-k])?$/, '')
    .trim()
  const name = preciseStructureNames[target]
    ?? (side ? preciseStructureNames[target.replace(/[lr]$/, '')] : undefined)
  return name ? `${side}${name}` : null
}

/**
 * 统一模型节点和医学别名的大小写、空格与技术分隔符。
 * @param value Three.js 网格名称或后端配置的匹配别名
 * @returns 可用于稳定比较的结构名称
 */
export function normalizeStructureName(value: string): string {
  return value
    .toLowerCase()
    .replace(/[_]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

/**
 * 根据 GLB 原始节点名称查找对应的中文身体区域。
 * @param rawName 三维模型中的原始网格名称
 * @param regions 后端返回的细分身体区域目录
 * @returns 匹配到的身体区域，未配置时返回 null
 */
export function findBodyRegion(
  rawName: string,
  regions: AtlasBodyRegion[],
): AtlasBodyRegion | null {
  const target = normalizeStructureName(rawName)
  let partialMatch: { region: AtlasBodyRegion; score: number } | null = null
  for (const region of regions) {
    for (const alias of region.mesh_aliases) {
      const normalizedAlias = normalizeStructureName(alias)
      if (target === normalizedAlias) return region
      if (target.includes(normalizedAlias) && normalizedAlias.length > (partialMatch?.score ?? 0)) {
        partialMatch = { region, score: normalizedAlias.length }
      }
    }
  }
  return partialMatch?.region ?? null
}

/**
 * 将牙齿和牙龈的英文网格名转换为包含上下颌、侧别和牙型的中文名称。
 * @param rawName 口腔三维模型中的原始网格名称
 * @returns 可读牙位名称；不是牙齿或牙龈节点时返回 null
 */
function resolveDentalStructureLabel(rawName: string): string | null {
  const normalized = normalizeStructureName(rawName)
  if (normalized.includes('gingiva')) return '牙龈'
  const toothKeywords = ['incisor', 'canine', 'premolar', 'molar', 'tooth']
  if (!toothKeywords.some((keyword) => normalized.includes(keyword))) return null

  const jaw = normalized.includes('upper')
    ? '上颌'
    : normalized.includes('lower')
      ? '下颌'
      : ''
  const side = resolveStructureSide(rawName, [])
  const toothType = normalized.includes('medial incisor')
    ? '中切牙'
    : normalized.includes('lateral incisor')
      ? '侧切牙'
      : normalized.includes('canine')
        ? '尖牙'
        : normalized.includes('first premolar')
          ? '第一前磨牙'
          : normalized.includes('second premolar')
            ? '第二前磨牙'
            : normalized.includes('first molar')
              ? '第一磨牙'
              : normalized.includes('second molar')
                ? '第二磨牙'
                : normalized.includes('third molar')
                  ? '第三磨牙（智齿）'
                  : normalized.includes('premolar')
                    ? '前磨牙'
                    : normalized.includes('molar')
                      ? '磨牙'
                      : '牙齿'
  const toothPosition = normalized.includes('medial incisor')
    ? 1
    : normalized.includes('lateral incisor')
      ? 2
      : normalized.includes('canine')
        ? 3
        : normalized.includes('first premolar')
          ? 4
          : normalized.includes('second premolar')
            ? 5
            : normalized.includes('first molar')
              ? 6
              : normalized.includes('second molar')
                ? 7
                : normalized.includes('third molar')
                  ? 8
                  : null
  const quadrant = jaw === '上颌'
    ? side === '右侧' ? 1 : side === '左侧' ? 2 : null
    : jaw === '下颌'
      ? side === '左侧' ? 3 : side === '右侧' ? 4 : null
      : null
  const fdiNumber = quadrant && toothPosition ? `${quadrant}${toothPosition}` : ''
  return `${side}${jaw}${toothType}${fdiNumber ? `（FDI ${fdiNumber}）` : ''}` || '牙齿'
}

/**
 * 统一悬浮提示和问诊选择的中文名称；优先精细结构，再使用所属系统的中文目录。
 * @param rawName 三维模型中的原始网格名称
 * @param regions 后端返回的细分身体区域目录
 * @param systems 后端返回的中文系统和器官目录
 * @param systemId 网格实际所属的系统，避免跨系统同名匹配
 * @returns 中文标签；未匹配的结构明确提示待确认，不直接暴露英文或猜测器官
 */
export function resolveStructureLabel(
  rawName: string,
  regions: AtlasBodyRegion[],
  systems: AtlasSystem[] = [],
  systemId?: string,
): string {
  if (!systemId || systemId === 'regional') {
    const region = findBodyRegion(rawName, regions)
    if (region) return region.name
  }
  const system = systems.find((item) => item.id === systemId)
  const organs = system ? system.organs : systems.flatMap((item) => item.organs)
  const side = resolveStructureSide(rawName, organs)
  const dentalLabel = resolveDentalStructureLabel(rawName)
  if (dentalLabel) return dentalLabel
  const preciseLabel = resolvePreciseStructureLabel(rawName, side)
  if (preciseLabel) return preciseLabel
  const organ = findAtlasOrgan(rawName, organs)
  if (organ) {
    const prefix = /左|右/.test(organ.name) ? '' : side
    for (const alias of organ.mesh_aliases) {
      if (normalizeStructureName(rawName) === normalizeStructureName(alias)) return organ.name
    }
    return `${prefix}${organ.name}（所属部位）`
  }
  return `${system?.name ?? '身体'}结构（具体部位待确认）`
}

/**
 * 根据内部解剖层网格名称匹配可加入问诊的器官。
 * @param rawName 三维内部器官网格名称
 * @param organs 当前医学系统中的器官目录
 * @returns 匹配到的器官，未配置时返回 null
 */
export function findAtlasOrgan(rawName: string, organs: AtlasOrgan[]): AtlasOrgan | null {
  const target = normalizeStructureName(rawName)
  let bestMatch: { organ: AtlasOrgan; score: number } | null = null
  for (const organ of organs) {
    for (const alias of organ.mesh_aliases) {
      const normalizedAlias = normalizeStructureName(alias)
      if (
        (target === normalizedAlias || target.includes(normalizedAlias))
        && normalizedAlias.length > (bestMatch?.score ?? 0)
      ) {
        bestMatch = { organ, score: normalizedAlias.length }
      }
    }
  }
  return bestMatch?.organ ?? null
}
