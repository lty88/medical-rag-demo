export type AnatomySystemId =
  | 'regional'
  | 'nervous'
  | 'respiratory'
  | 'circulatory'
  | 'digestive'
  | 'urinary'
  | 'musculoskeletal'
  | 'integumentary'
  | 'lymphatic'
  | 'reproductive'

export type AnatomyModelId = 'male' | 'female'

export interface AnatomyHoverInfo {
  systemId: AnatomySystemId
  label: string
  rawName: string
  x: number
  y: number
}

export interface AnatomyStructureSelection {
  systemId: AnatomySystemId
  label: string
  rawName: string
}

export interface AnatomySceneOptions {
  modelId: AnatomyModelId
  activeSystemId: string
  onSystemSelect: (systemId: AnatomySystemId) => void
  onStructureSelect: (selection: AnatomyStructureSelection) => void
  onHover: (info: AnatomyHoverInfo | null) => void
  onProgress: (progress: number) => void
  onLayerStatus: (loadedSystemIds: AnatomySystemId[], failedSystemIds: AnatomySystemId[]) => void
  resolveStructureLabel: (rawName: string) => string
}

export interface AnatomySceneController {
  setActiveSystem: (systemId: string) => void
  focusSystem: (systemId: string) => void
  focusStructure: (rawName: string) => void
  setSelectedStructures: (rawNames: string[]) => void
  setAutoRotate: (enabled: boolean) => void
  resize: () => void
  resetView: () => void
  dispose: () => void
}

export interface AnatomySceneExposed {
  resetView: () => void
  focusStructure: (rawName: string) => void
  setAutoRotate: (enabled: boolean) => void
}
