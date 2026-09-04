import type { AtlasBodyRegion, AtlasOrgan } from '../types'

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
  const side = /(?:\.l|\bleft\b)/i.test(rawName)
    ? '左侧'
    : /(?:\.r|\bright\b)/i.test(rawName)
      ? '右侧'
      : ''
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
 * 将技术网格名称转换为悬浮标签使用的中文部位名称。
 * @param rawName 三维模型中的原始网格名称
 * @param regions 后端返回的细分身体区域目录
 * @returns 中文身体区域名或清理后的原始结构名
 */
export function resolveStructureLabel(rawName: string, regions: AtlasBodyRegion[]): string {
  const region = findBodyRegion(rawName, regions)
  if (region) return region.name
  const dentalLabel = resolveDentalStructureLabel(rawName)
  if (dentalLabel) return dentalLabel
  return rawName.replace(/[_\.]+/g, ' ').replace(/\s+/g, ' ').trim() || '细分身体区域'
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
