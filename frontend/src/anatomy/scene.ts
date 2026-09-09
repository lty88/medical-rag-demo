import * as THREE from 'three'
import { DRACOLoader } from 'three/examples/jsm/loaders/DRACOLoader.js'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import type {
  AnatomyHoverInfo,
  AnatomyModelId,
  AnatomySceneController,
  AnatomySceneOptions,
  AnatomySystemId,
} from './types'

type AnatomyLayerId = AnatomySystemId
type AnatomyMaterial = THREE.MeshPhysicalMaterial
type AnatomyMesh = THREE.Mesh<THREE.BufferGeometry, AnatomyMaterial>

interface AnatomyLayerConfig {
  id: AnatomyLayerId
  url: string
  color: number
  activeOpacity: number
  inactiveOpacity: number
  interactive: boolean
}

interface LoadedAnatomyLayer {
  config: AnatomyLayerConfig
  root: THREE.Group
  material: AnatomyMaterial
  meshes: AnatomyMesh[]
}

const MALE_ANATOMY_LAYERS: AnatomyLayerConfig[] = [
  {
    id: 'regional',
    url: '/anatomy/regional_male.glb',
    color: 0x47d7dc,
    activeOpacity: 0.32,
    inactiveOpacity: 0.08,
    interactive: true,
  },
  {
    id: 'circulatory',
    url: '/anatomy/cardiovascular_male.glb',
    color: 0xff5f79,
    activeOpacity: 0.92,
    inactiveOpacity: 0.12,
    interactive: true,
  },
  {
    id: 'digestive',
    url: '/anatomy/digestive_male.glb',
    color: 0xe7a74b,
    activeOpacity: 0.9,
    inactiveOpacity: 0.2,
    interactive: true,
  },
  {
    id: 'nervous',
    url: '/anatomy/nervous_male.glb',
    color: 0x70cfff,
    activeOpacity: 0.9,
    inactiveOpacity: 0.09,
    interactive: true,
  },
  {
    id: 'urinary',
    url: '/anatomy/renal_male.glb',
    color: 0xb39aff,
    activeOpacity: 0.94,
    inactiveOpacity: 0.22,
    interactive: true,
  },
  {
    id: 'respiratory',
    url: '/anatomy/respiratory_male.glb',
    color: 0x62e6d4,
    activeOpacity: 0.9,
    inactiveOpacity: 0.22,
    interactive: true,
  },
  {
    id: 'musculoskeletal',
    url: '/anatomy/skeletal_male.glb',
    color: 0xd7e3e8,
    activeOpacity: 0.92,
    inactiveOpacity: 0.08,
    interactive: true,
  },
]

const FEMALE_ANATOMY_LAYERS: AnatomyLayerConfig[] = [
  {
    id: 'circulatory',
    url: '/anatomy/cardiovascular_female.glb',
    color: 0xff5f79,
    activeOpacity: 0.92,
    inactiveOpacity: 0.12,
    interactive: true,
  },
  {
    id: 'digestive',
    url: '/anatomy/digestive_female.glb',
    color: 0xe7a74b,
    activeOpacity: 0.9,
    inactiveOpacity: 0.2,
    interactive: true,
  },
  {
    id: 'integumentary',
    url: '/anatomy/integumentary_female.glb',
    color: 0xf0a6ca,
    activeOpacity: 0.28,
    inactiveOpacity: 0.07,
    interactive: true,
  },
  {
    id: 'lymphatic',
    url: '/anatomy/lymphatic_female.glb',
    color: 0x9ee493,
    activeOpacity: 0.9,
    inactiveOpacity: 0.12,
    interactive: true,
  },
  {
    id: 'urinary',
    url: '/anatomy/renal_female.glb',
    color: 0xb39aff,
    activeOpacity: 0.94,
    inactiveOpacity: 0.2,
    interactive: true,
  },
  {
    id: 'reproductive',
    url: '/anatomy/reproductive_female.glb',
    color: 0xf472b6,
    activeOpacity: 0.96,
    inactiveOpacity: 0.18,
    interactive: true,
  },
  {
    id: 'musculoskeletal',
    url: '/anatomy/skeletal_female.glb',
    color: 0xd7e3e8,
    activeOpacity: 0.92,
    inactiveOpacity: 0.08,
    interactive: true,
  },
]

const ANATOMY_LAYERS_BY_MODEL: Record<AnatomyModelId, AnatomyLayerConfig[]> = {
  male: MALE_ANATOMY_LAYERS,
  female: FEMALE_ANATOMY_LAYERS,
}

/**
 * 创建真实解剖层共享的医学物理材质。
 * @param config 解剖层颜色、透明度和交互配置
 * @returns 可动态高亮的半透明物理材质
 */
function createLayerMaterial(config: AnatomyLayerConfig): AnatomyMaterial {
  const color = new THREE.Color(config.color)
  return new THREE.MeshPhysicalMaterial({
    color,
    emissive: color.clone().multiplyScalar(config.id === 'regional' ? 0.12 : 0.08),
    emissiveIntensity: config.id === 'regional' ? 0.45 : 0.24,
    metalness: 0.01,
    roughness: config.id === 'regional' ? 0.18 : 0.34,
    clearcoat: config.id === 'regional' ? 0.86 : 0.46,
    clearcoatRoughness: 0.22,
    transmission: config.id === 'regional' ? 0.38 : 0,
    thickness: config.id === 'regional' ? 0.7 : 0.15,
    transparent: true,
    opacity: config.inactiveOpacity,
    depthWrite: false,
    side: THREE.DoubleSide,
  })
}

/**
 * 创建深色科研空间中的定位网格、扫描环和背景粒子。
 * @param scene Three.js 三维场景
 */
function createScientificEnvironment(scene: THREE.Scene) {
  const particleCount = 220
  const positions = new Float32Array(particleCount * 3)
  for (let index = 0; index < particleCount; index += 1) {
    positions[index * 3] = (Math.random() - 0.5) * 18
    positions[index * 3 + 1] = (Math.random() - 0.5) * 14
    positions[index * 3 + 2] = -3 - Math.random() * 7
  }
  const particleGeometry = new THREE.BufferGeometry()
  particleGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  const particles = new THREE.Points(
    particleGeometry,
    new THREE.PointsMaterial({
      color: 0x5eead4,
      size: 0.026,
      transparent: true,
      opacity: 0.34,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    }),
  )
  scene.add(particles)

  const ringMaterial = new THREE.MeshBasicMaterial({
    color: 0x3e9ca3,
    transparent: true,
    opacity: 0.18,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  })
  for (const radius of [2.2, 2.8, 3.4]) {
    const ring = new THREE.Mesh(new THREE.TorusGeometry(radius, 0.012, 6, 120), ringMaterial)
    ring.position.y = -5.18
    ring.rotation.x = Math.PI / 2
    scene.add(ring)
  }

  const grid = new THREE.GridHelper(16, 32, 0x28525a, 0x162f36)
  grid.position.y = -5.22
  const gridMaterials = Array.isArray(grid.material) ? grid.material : [grid.material]
  for (const gridMaterial of gridMaterials) {
    gridMaterial.transparent = true
    gridMaterial.opacity = 0.28
  }
  scene.add(grid)
}

/**
 * 将同一坐标系中的全部解剖层统一缩放并居中到观察区域。
 * @param anatomyRoot 全部真实解剖模型的根节点
 */
function normalizeAnatomyScale(anatomyRoot: THREE.Group) {
  anatomyRoot.updateMatrixWorld(true)
  const bounds = new THREE.Box3().setFromObject(anatomyRoot)
  const size = bounds.getSize(new THREE.Vector3())
  const center = bounds.getCenter(new THREE.Vector3())
  if (!Number.isFinite(size.y) || size.y <= 0) {
    throw new Error('真实人体模型的尺寸信息无效')
  }
  const targetHeight = 10.25
  const scale = targetHeight / size.y
  anatomyRoot.scale.setScalar(scale)
  anatomyRoot.position.set(-center.x * scale, -center.y * scale - 0.05, -center.z * scale)
  anatomyRoot.updateMatrixWorld(true)
}

/**
 * 把一个 GLB 解剖文件载入场景并转换为可交互医学材质。
 * @param loader 已配置 Draco 解码器的 GLTFLoader
 * @param config 当前解剖层配置
 * @param resolveStructureLabel 按实际所属系统将模型节点名称转换为中文部位名称的函数
 * @returns 已载入的模型根节点、共享材质及拾取网格
 */
async function loadAnatomyLayer(
  loader: GLTFLoader,
  config: AnatomyLayerConfig,
  resolveStructureLabel: (rawName: string, systemId: AnatomySystemId) => string,
): Promise<LoadedAnatomyLayer> {
  const gltf = await loader.loadAsync(config.url)
  const material = createLayerMaterial(config)
  const root = gltf.scene
  const meshes: AnatomyMesh[] = []
  root.name = `anatomy-${config.id}`

  /**
   * 为真实解剖网格绑定材质、原始定位标识及所属系统对应的中文名称。
   * @param object 当前遍历的模型节点
   */
  function prepareMesh(object: THREE.Object3D) {
    if (!(object instanceof THREE.Mesh)) {
      return
    }
    const mesh = object as AnatomyMesh
    mesh.material = material
    mesh.castShadow = false
    mesh.receiveShadow = false
    mesh.frustumCulled = true
    mesh.userData.systemId = config.id
    mesh.userData.rawName = mesh.name
    mesh.userData.organLabel = resolveStructureLabel(mesh.name, config.id)
    if (config.interactive) {
      meshes.push(mesh)
    }
  }

  root.traverse(prepareMesh)
  return { config, root, material, meshes }
}

/**
 * 释放场景内所有几何体和材质，避免切换菜单后残留显存。
 * @param scene 需要释放的三维场景
 */
function disposeSceneResources(scene: THREE.Scene) {
  const disposedMaterials = new Set<THREE.Material>()

  /**
   * 释放单个三维节点持有的几何体与未释放材质。
   * @param object 当前遍历的三维节点
   */
  function disposeObject(object: THREE.Object3D) {
    if (!(object instanceof THREE.Mesh) && !(object instanceof THREE.Points)) {
      return
    }
    object.geometry?.dispose()
    const materials = Array.isArray(object.material) ? object.material : [object.material]
    for (const material of materials) {
      if (!disposedMaterials.has(material)) {
        material.dispose()
        disposedMaterials.add(material)
      }
    }
  }

  scene.traverse(disposeObject)
}

/**
 * 创建基于真实 GLB 解剖资产的 Three.js 人体场景。
 * @param container 承载 WebGL 画布的页面元素
 * @param options 初始系统、加载进度及交互回调
 * @returns 场景状态更新、尺寸同步、复位与销毁能力
 */
export async function createAnatomyScene(
  container: HTMLElement,
  options: AnatomySceneOptions,
): Promise<AnatomySceneController> {
  const scene = new THREE.Scene()
  scene.fog = new THREE.FogExp2(0x06151f, 0.028)

  const camera = new THREE.PerspectiveCamera(31, 1, 0.01, 100)
  camera.position.set(0, 0, 19.4)

  const renderer = new THREE.WebGLRenderer({
    antialias: true,
    alpha: true,
    powerPreference: 'high-performance',
  })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.setClearColor(0x06151f, 0)
  renderer.outputColorSpace = THREE.SRGBColorSpace
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.22
  renderer.domElement.className = 'three-anatomy-canvas'
  renderer.domElement.setAttribute('aria-label', '可旋转和缩放的高精度三维人体系统模型')
  container.appendChild(renderer.domElement)

  const controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.065
  controls.enablePan = true
  controls.screenSpacePanning = true
  controls.minDistance = 0.28
  controls.maxDistance = 28
  controls.zoomToCursor = true
  controls.minPolarAngle = Math.PI * 0.27
  controls.maxPolarAngle = Math.PI * 0.73
  controls.target.set(0, -0.15, 0)
  controls.autoRotate = false
  controls.mouseButtons.LEFT = THREE.MOUSE.ROTATE
  controls.mouseButtons.MIDDLE = THREE.MOUSE.DOLLY
  controls.mouseButtons.RIGHT = THREE.MOUSE.PAN
  controls.touches.ONE = THREE.TOUCH.ROTATE
  controls.touches.TWO = THREE.TOUCH.DOLLY_PAN

  scene.add(new THREE.HemisphereLight(0xb7fbff, 0x050a10, 2.2))
  const keyLight = new THREE.DirectionalLight(0xb1fff2, 3.8)
  keyLight.position.set(5, 7, 8)
  scene.add(keyLight)
  const fillLight = new THREE.DirectionalLight(0x5f82ff, 2.6)
  fillLight.position.set(-6, 1, 5)
  scene.add(fillLight)
  const rimLight = new THREE.DirectionalLight(0x30c8dd, 3.1)
  rimLight.position.set(3, 2, -7)
  scene.add(rimLight)
  const organLight = new THREE.PointLight(0xff738d, 2.1, 12)
  organLight.position.set(0, 0.8, 4)
  scene.add(organLight)

  createScientificEnvironment(scene)

  const loadingManager = new THREE.LoadingManager()

  /**
   * 将 Three.js 文件加载数量转换为前端百分比。
   * @param _url 当前完成的资源地址
   * @param loaded 已完成资源数量
   * @param total 资源总数量
   */
  function handleLoadProgress(_url: string, loaded: number, total: number) {
    options.onProgress(total > 0 ? Math.round((loaded / total) * 100) : 0)
  }

  loadingManager.onProgress = handleLoadProgress
  const dracoLoader = new DRACOLoader(loadingManager)
  dracoLoader.setDecoderPath('/draco/')
  dracoLoader.setDecoderConfig({ type: 'wasm' })
  const gltfLoader = new GLTFLoader(loadingManager)
  gltfLoader.setDRACOLoader(dracoLoader)

  const anatomyRoot = new THREE.Group()
  anatomyRoot.name = 'high-fidelity-anatomy'
  scene.add(anatomyRoot)

  const loadedLayers = new Map<AnatomyLayerId, LoadedAnatomyLayer>()
  const interactiveMeshes: AnatomyMesh[] = []
  const layerPromises: Promise<LoadedAnatomyLayer>[] = []
  const anatomyLayers = ANATOMY_LAYERS_BY_MODEL[options.modelId]
  for (const config of anatomyLayers) {
    layerPromises.push(loadAnatomyLayer(gltfLoader, config, options.resolveStructureLabel))
  }

  try {
    const layerResults = await Promise.allSettled(layerPromises)
    const failedSystemIds: AnatomySystemId[] = []
    for (const [index, result] of layerResults.entries()) {
      if (result.status === 'rejected') {
        failedSystemIds.push(anatomyLayers[index].id)
        console.warn(
          `[人体三维图谱] ${options.modelId} 模型的 ${anatomyLayers[index].id} 图层加载失败。`,
          result.reason,
        )
        continue
      }
      const layer = result.value
      loadedLayers.set(layer.config.id, layer)
      anatomyRoot.add(layer.root)
      interactiveMeshes.push(...layer.meshes)
    }
    if (!loadedLayers.size) {
      throw new Error(`${options.modelId} 解剖模型没有可用图层`)
    }
    normalizeAnatomyScale(anatomyRoot)
    options.onLayerStatus([...loadedLayers.keys()], failedSystemIds)
    options.onProgress(100)
  }
  catch (error) {
    controls.dispose()
    dracoLoader.dispose()
    disposeSceneResources(scene)
    renderer.dispose()
    renderer.forceContextLoss()
    renderer.domElement.remove()
    throw error
  }

  const raycaster = new THREE.Raycaster()
  const pointer = new THREE.Vector2()
  const pointerDown = new THREE.Vector2()
  const clock = new THREE.Clock()
  let elapsedTime = 0
  let autoRotateEnabled = true
  let focusTransition: {
    startedAt: number
    fromPosition: THREE.Vector3
    toPosition: THREE.Vector3
    fromTarget: THREE.Vector3
    toTarget: THREE.Vector3
  } | null = null
  let activeSystemId = options.activeSystemId
  let animationFrameId = 0
  let hoverFrameId = 0
  let selectionTimerId = 0
  let pendingHoverEvent: PointerEvent | null = null
  const selectedMaterials = new Map<
    AnatomyMesh,
    { base: AnatomyMaterial; highlight: AnatomyMaterial }
  >()
  let disposed = false

  /**
   * 用户开始手动旋转、缩放或平移时终止自动镜头过渡，保证操作立即接管相机。
   */
  function cancelFocusTransition() {
    focusTransition = null
  }

  controls.addEventListener('start', cancelFocusTransition)

  /**
   * 清除当前点击网格的独立高亮材质并恢复所属解剖层材质。
   */
  function clearSelectedStructures() {
    for (const [mesh, materials] of selectedMaterials) {
      mesh.material = materials.base
      materials.highlight.dispose()
    }
    selectedMaterials.clear()
  }

  /**
   * 为用户点击的细分身体网格创建独立高亮，便于确认选择位置。
   * @param mesh 当前射线拾取命中的身体结构网格
   */
  function highlightSelectedStructure(mesh: AnatomyMesh) {
    if (selectedMaterials.has(mesh)) return
    const base = mesh.material
    const highlight = mesh.material.clone()
    highlight.color.set(0x7ff4df)
    highlight.emissive.set(0x32e6c7)
    highlight.emissiveIntensity = 1.7
    highlight.opacity = 0.82
    highlight.depthWrite = true
    highlight.needsUpdate = true
    selectedMaterials.set(mesh, { base, highlight })
    mesh.material = highlight
  }

  /**
   * 根据已选清单同步全部身体区域高亮，使多部位选择在三维模型上持续可见。
   * @param rawNames 已选身体区域对应的 GLB 原始网格名称
   */
  function setSelectedStructures(rawNames: string[]) {
    clearSelectedStructures()
    const selectedNames = new Set(rawNames)
    for (const layer of loadedLayers.values()) {
      for (const mesh of layer.meshes) {
        if (selectedNames.has(String(mesh.userData.rawName ?? mesh.name))) {
          highlightSelectedStructure(mesh)
        }
      }
    }
  }

  /**
   * 更新全部真实解剖层的透明度和发光强度，突出当前系统。
   * @param systemId 当前选中的人体系统标识
   */
  function setActiveSystem(systemId: string) {
    activeSystemId = systemId
    for (const layer of loadedLayers.values()) {
      const isRegional = layer.config.id === 'regional'
      const isActive = layer.config.id === activeSystemId
      layer.material.opacity = isActive
        ? layer.config.activeOpacity
        : layer.config.inactiveOpacity
      layer.material.emissiveIntensity = isActive ? (isRegional ? 0.78 : 1.12) : 0.14
      layer.material.depthWrite = isActive
      layer.material.needsUpdate = true
      layer.root.renderOrder = isActive ? 4 : isRegional ? 1 : 2
    }
  }

  /**
   * 根据三维包围盒计算完整可见距离，并平滑移动相机焦点到局部中心。
   * @param bounds 一个器官、牙位或一组网格的世界坐标包围盒
   * @param padding 镜头边缘留白倍率，数值越大视野越宽
   */
  function focusBounds(bounds: THREE.Box3, padding: number) {
    const size = bounds.getSize(new THREE.Vector3())
    const center = bounds.getCenter(new THREE.Vector3())
    if (!Number.isFinite(size.y) || size.lengthSq() <= 0) return

    const verticalFov = THREE.MathUtils.degToRad(camera.fov)
    const fitHeightDistance = size.y / (2 * Math.tan(verticalFov / 2))
    const horizontalFov = 2 * Math.atan(Math.tan(verticalFov / 2) * camera.aspect)
    const fitWidthDistance = size.x / (2 * Math.tan(horizontalFov / 2))
    const fitDistance = THREE.MathUtils.clamp(
      Math.max(fitHeightDistance, fitWidthDistance, size.z * 1.5) * padding,
      controls.minDistance,
      controls.maxDistance,
    )
    const viewDirection = camera.position.clone().sub(controls.target).normalize()
    if (viewDirection.lengthSq() === 0) viewDirection.set(0, 0, 1)
    focusTransition = {
      startedAt: performance.now(),
      fromPosition: camera.position.clone(),
      toPosition: center.clone().add(viewDirection.multiplyScalar(fitDistance)),
      fromTarget: controls.target.clone(),
      toTarget: center,
    }
  }

  /**
   * 根据三维对象包围盒平滑移动镜头并把观察中心切换到该对象。
   * @param targetObject 要聚焦的系统根节点或精细器官网格
   * @param padding 镜头边缘留白倍率，数值越大视野越宽
   */
  function focusObject(targetObject: THREE.Object3D, padding: number) {
    anatomyRoot.updateMatrixWorld(true)
    focusBounds(new THREE.Box3().setFromObject(targetObject), padding)
  }

  /**
   * 统一三维网格名称的大小写、下划线和空格，供科室别名进行模糊匹配。
   * @param value 模型原始名称或医学结构别名
   * @returns 可进行包含关系比较的标准化名称
   */
  function normalizeMeshLookupName(value: string) {
    return value.toLowerCase().replace(/[_\.]+/g, ' ').replace(/\s+/g, ' ').trim()
  }

  /**
   * 根据真实系统包围盒平滑移动相机，完整展示该系统并保留少量边缘空间。
   * @param systemId 要完整展示的人体系统标识
   */
  function focusSystem(systemId: string) {
    const layer = loadedLayers.get(systemId as AnatomyLayerId)
    if (!layer) return
    focusObject(layer.root, 1.06)
  }

  /**
   * 按原始网格名称定位精细身体结构，并将相机移动到适合局部观察的距离。
   * @param rawName 三维模型中的原始结构名称
   */
  function focusStructure(rawName: string) {
    for (const layer of loadedLayers.values()) {
      const mesh = layer.meshes.find(
        (item) => String(item.userData.rawName ?? item.name) === rawName,
      )
      if (mesh) {
        focusObject(mesh, 1.7)
        return
      }
    }
  }

  /**
   * 聚焦与一组医学别名匹配的全部网格，使科室导航可定位牙列或器官区域。
   * @param aliases 后端科室或器官配置的模型英文别名
   */
  function focusStructureAliases(aliases: string[]) {
    const normalizedAliases = aliases
      .map(normalizeMeshLookupName)
      .filter((alias) => alias.length >= 3)
    if (!normalizedAliases.length) return
    anatomyRoot.updateMatrixWorld(true)
    const bounds = new THREE.Box3()
    let hasMatch = false
    for (const layer of loadedLayers.values()) {
      for (const mesh of layer.meshes) {
        const rawName = String(mesh.userData.rawName ?? mesh.name)
        const normalizedName = normalizeMeshLookupName(rawName)
        const isMatch = normalizedAliases.some(
          (alias) => normalizedName === alias || normalizedName.includes(alias),
        )
        if (!isMatch) continue
        bounds.expandByObject(mesh)
        hasMatch = true
      }
    }
    if (hasMatch) focusBounds(bounds, 1.55)
  }

  /**
   * 根据容器尺寸同步相机比例和 WebGL 画布像素尺寸。
   */
  function resize() {
    const width = Math.max(1, container.clientWidth)
    const height = Math.max(1, container.clientHeight)
    camera.aspect = width / height
    camera.updateProjectionMatrix()
    renderer.setSize(width, height, false)
  }

  /**
   * 将相机恢复到真实人体的正面全身观察位置。
   */
  function resetView() {
    focusTransition = null
    anatomyRoot.rotation.y = 0
    camera.position.set(0, 0, 19.4)
    controls.target.set(0, -0.15, 0)
    controls.update()
  }

  /**
   * 控制真实人体模型是否自动缓慢旋转。
   * @param enabled 是否启用自动旋转
   */
  function setAutoRotate(enabled: boolean) {
    autoRotateEnabled = enabled
  }

  /**
   * 将指针转换到标准设备坐标并返回命中的首个真实器官网格。
   * @param event 画布指针事件
   * @returns 命中的器官网格，未命中时返回 null
   */
  function pickOrgan(event: PointerEvent): AnatomyMesh | null {
    const bounds = renderer.domElement.getBoundingClientRect()
    pointer.x = ((event.clientX - bounds.left) / bounds.width) * 2 - 1
    pointer.y = -((event.clientY - bounds.top) / bounds.height) * 2 + 1
    raycaster.setFromCamera(pointer, camera)
    const activeMeshes = loadedLayers.get(activeSystemId as AnatomyLayerId)?.meshes
    const intersection = raycaster.intersectObjects(
      activeMeshes?.length ? activeMeshes : interactiveMeshes,
      false,
    )[0]
    return (intersection?.object as AnatomyMesh | undefined) ?? null
  }

  /**
   * 记录按下位置，用于区分点击器官和拖拽旋转。
   * @param event 指针按下事件
   */
  function handlePointerDown(event: PointerEvent) {
    pointerDown.set(event.clientX, event.clientY)
  }

  /**
   * 执行一次节流后的器官射线拾取并更新悬浮标签。
   */
  function updateHoveredOrgan() {
    hoverFrameId = 0
    const event = pendingHoverEvent
    pendingHoverEvent = null
    if (!event) {
      return
    }
    const mesh = pickOrgan(event)
    renderer.domElement.style.cursor = mesh ? 'pointer' : 'grab'
    if (!mesh) {
      options.onHover(null)
      return
    }
    const bounds = renderer.domElement.getBoundingClientRect()
    options.onHover({
      systemId: mesh.userData.systemId as AnatomySystemId,
      label: String(mesh.userData.organLabel ?? 'Anatomical structure'),
      rawName: String(mesh.userData.rawName ?? mesh.name),
      x: event.clientX - bounds.left,
      y: event.clientY - bounds.top,
    } satisfies AnatomyHoverInfo)
  }

  /**
   * 在指针移动时按动画帧节流真实器官拾取，避免高面数模型卡顿。
   * @param event 指针移动事件
   */
  function handlePointerMove(event: PointerEvent) {
    pendingHoverEvent = event
    if (!hoverFrameId) {
      hoverFrameId = window.requestAnimationFrame(updateHoveredOrgan)
    }
  }

  /**
   * 在非拖拽操作结束时选中当前真实器官所属系统。
   * @param event 指针释放事件
   */
  function handlePointerUp(event: PointerEvent) {
    const movement = pointerDown.distanceTo(new THREE.Vector2(event.clientX, event.clientY))
    if (movement > 5) {
      return
    }
    window.clearTimeout(selectionTimerId)
    const clientX = event.clientX
    const clientY = event.clientY
    selectionTimerId = window.setTimeout(() => {
      const syntheticEvent = new PointerEvent('pointerup', { clientX, clientY })
      const mesh = pickOrgan(syntheticEvent)
      if (!mesh) return
      highlightSelectedStructure(mesh)
      options.onSystemSelect(mesh.userData.systemId as AnatomySystemId)
      options.onStructureSelect({
        systemId: mesh.userData.systemId as AnatomySystemId,
        label: String(mesh.userData.organLabel ?? 'Anatomical structure'),
        rawName: String(mesh.userData.rawName ?? mesh.name),
      })
    }, 220)
  }

  /**
   * 双击真实身体结构时取消单击选择计时，并将镜头直接定位到该结构。
   * @param event 画布双击事件
   */
  function handleDoubleClick(event: MouseEvent) {
    window.clearTimeout(selectionTimerId)
    const pointerEvent = new PointerEvent('pointerup', {
      clientX: event.clientX,
      clientY: event.clientY,
    })
    const mesh = pickOrgan(pointerEvent)
    if (!mesh) return
    focusObject(mesh, 1.7)
  }

  /**
   * 指针离开画布时清理器官悬浮状态。
   */
  function handlePointerLeave() {
    options.onHover(null)
    renderer.domElement.style.cursor = 'grab'
  }

  /**
   * 持续驱动呼吸明暗、循环脉冲、相机阻尼与三维渲染。
   */
  function animate() {
    if (disposed) {
      return
    }
    const deltaTime = Math.min(clock.getDelta(), 0.05)
    elapsedTime += deltaTime
    if (autoRotateEnabled && !focusTransition) {
      anatomyRoot.rotation.y += deltaTime * 0.2
    }
    if (focusTransition) {
      const progress = THREE.MathUtils.clamp(
        (performance.now() - focusTransition.startedAt) / 650,
        0,
        1,
      )
      const easedProgress = 1 - (1 - progress) ** 3
      camera.position.lerpVectors(
        focusTransition.fromPosition,
        focusTransition.toPosition,
        easedProgress,
      )
      controls.target.lerpVectors(
        focusTransition.fromTarget,
        focusTransition.toTarget,
        easedProgress,
      )
      if (progress >= 1) focusTransition = null
    }
    const respiratoryLayer = loadedLayers.get('respiratory')
    if (respiratoryLayer) {
      const breathing = 1 + Math.sin(elapsedTime * 1.45) * 0.004
      respiratoryLayer.root.scale.setScalar(breathing)
    }
    const circulatoryLayer = loadedLayers.get('circulatory')
    if (circulatoryLayer && activeSystemId === 'circulatory') {
      const pulse = Math.max(0, Math.sin(elapsedTime * 7.2)) ** 6
      circulatoryLayer.material.emissiveIntensity = 1.05 + pulse * 0.38
    }
    controls.update()
    renderer.render(scene, camera)
    animationFrameId = window.requestAnimationFrame(animate)
  }

  /**
   * 停止动画、解绑事件并释放 Draco、WebGL 与模型显存资源。
   */
  function dispose() {
    disposed = true
    window.cancelAnimationFrame(animationFrameId)
    window.cancelAnimationFrame(hoverFrameId)
    window.clearTimeout(selectionTimerId)
    renderer.domElement.removeEventListener('pointerdown', handlePointerDown)
    renderer.domElement.removeEventListener('pointermove', handlePointerMove)
    renderer.domElement.removeEventListener('pointerup', handlePointerUp)
    renderer.domElement.removeEventListener('pointerleave', handlePointerLeave)
    renderer.domElement.removeEventListener('dblclick', handleDoubleClick)
    controls.removeEventListener('start', cancelFocusTransition)
    clearSelectedStructures()
    controls.dispose()
    dracoLoader.dispose()
    disposeSceneResources(scene)
    renderer.dispose()
    renderer.forceContextLoss()
    renderer.domElement.remove()
  }

  renderer.domElement.addEventListener('pointerdown', handlePointerDown)
  renderer.domElement.addEventListener('pointermove', handlePointerMove)
  renderer.domElement.addEventListener('pointerup', handlePointerUp)
  renderer.domElement.addEventListener('pointerleave', handlePointerLeave)
  renderer.domElement.addEventListener('dblclick', handleDoubleClick)
  resize()
  resetView()
  setActiveSystem(activeSystemId)
  focusSystem(activeSystemId)
  animate()

  return {
    setActiveSystem,
    focusSystem,
    focusStructure,
    focusStructureAliases,
    setSelectedStructures,
    setAutoRotate,
    resize,
    resetView,
    dispose,
  }
}
