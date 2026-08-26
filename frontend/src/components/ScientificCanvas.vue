<script setup lang="tsx">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { WorkspaceKey } from '../types'

interface Particle {
  x: number
  y: number
  radius: number
  velocityX: number
  velocityY: number
  phase: number
}

interface CanvasPalette {
  primary: string
  secondary: string
  glow: string
}

const props = defineProps<{ mode: WorkspaceKey }>()
const canvasRef = ref<HTMLCanvasElement | null>(null)

let context: CanvasRenderingContext2D | null = null
let animationFrame = 0
let resizeObserver: ResizeObserver | null = null
let particles: Particle[] = []
let width = 0
let height = 0
let pixelRatio = 1
let startedAt = 0
let reduceMotion = false

const palettes: Record<WorkspaceKey, CanvasPalette> = {
  consult: { primary: '117, 225, 209', secondary: '125, 211, 252', glow: '94, 234, 212' },
  atlas: { primary: '94, 234, 212', secondary: '251, 113, 133', glow: '125, 211, 252' },
  research: { primary: '125, 211, 252', secondary: '167, 139, 250', glow: '117, 225, 209' },
  knowledge: { primary: '251, 191, 36', secondary: '117, 225, 209', glow: '125, 211, 252' },
  monitor: { primary: '117, 225, 209', secondary: '251, 113, 133', glow: '251, 191, 36' },
}

/**
 * 创建适配当前画布面积的生命粒子集合。
 */
function createParticles() {
  const count = Math.max(20, Math.min(58, Math.round((width * height) / 32000)))
  particles = Array.from({ length: count }, (_, index) => ({
    x: Math.random() * width,
    y: Math.random() * height,
    radius: 0.8 + Math.random() * 1.8,
    velocityX: (Math.random() - 0.5) * 0.16,
    velocityY: (Math.random() - 0.5) * 0.16,
    phase: index * 0.47 + Math.random() * Math.PI,
  }))
}

/**
 * 根据容器尺寸与设备像素比调整 Canvas 清晰度。
 */
function resizeCanvas() {
  const canvas = canvasRef.value
  if (!canvas) return
  const bounds = canvas.getBoundingClientRect()
  pixelRatio = Math.min(window.devicePixelRatio || 1, 2)
  width = Math.max(1, bounds.width)
  height = Math.max(1, bounds.height)
  canvas.width = Math.round(width * pixelRatio)
  canvas.height = Math.round(height * pixelRatio)
  context = canvas.getContext('2d')
  context?.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0)
  createParticles()
  if (reduceMotion && startedAt) renderFrame(window.performance.now())
}

/**
 * 绘制模拟科研测量背景的细网格和移动扫描线。
 * @param time 当前动画经过的秒数
 * @param palette 当前工作区配色
 */
function drawMeasurementGrid(time: number, palette: CanvasPalette) {
  if (!context) return
  context.save()
  context.strokeStyle = `rgba(${palette.primary}, 0.035)`
  context.lineWidth = 1
  const gridSize = 42
  const offset = (time * 4) % gridSize
  for (let x = -gridSize + offset; x < width; x += gridSize) {
    context.beginPath()
    context.moveTo(x, 0)
    context.lineTo(x, height)
    context.stroke()
  }
  for (let y = -gridSize + offset; y < height; y += gridSize) {
    context.beginPath()
    context.moveTo(0, y)
    context.lineTo(width, y)
    context.stroke()
  }
  const scanY = reduceMotion ? height * 0.36 : (time * 24) % Math.max(height, 1)
  const gradient = context.createLinearGradient(0, scanY - 34, 0, scanY + 34)
  gradient.addColorStop(0, `rgba(${palette.primary}, 0)`)
  gradient.addColorStop(0.5, `rgba(${palette.primary}, 0.055)`)
  gradient.addColorStop(1, `rgba(${palette.primary}, 0)`)
  context.fillStyle = gradient
  context.fillRect(0, scanY - 34, width, 68)
  context.restore()
}

/**
 * 绘制带邻近连线的细胞或数据粒子。
 * @param time 当前动画经过的秒数
 * @param palette 当前工作区配色
 */
function drawParticles(time: number, palette: CanvasPalette) {
  if (!context) return
  for (const particle of particles) {
    if (!reduceMotion) {
      particle.x += particle.velocityX
      particle.y += particle.velocityY
      if (particle.x < -10) particle.x = width + 10
      if (particle.x > width + 10) particle.x = -10
      if (particle.y < -10) particle.y = height + 10
      if (particle.y > height + 10) particle.y = -10
    }
    const pulse = 0.55 + Math.sin(time * 0.8 + particle.phase) * 0.25
    context.beginPath()
    context.fillStyle = `rgba(${palette.primary}, ${0.12 + pulse * 0.15})`
    context.arc(particle.x, particle.y, particle.radius + pulse, 0, Math.PI * 2)
    context.fill()
  }

  context.lineWidth = 0.6
  for (let first = 0; first < particles.length; first += 1) {
    for (let second = first + 1; second < particles.length; second += 1) {
      const left = particles[first]
      const right = particles[second]
      if (!left || !right) continue
      const distance = Math.hypot(left.x - right.x, left.y - right.y)
      if (distance > 105) continue
      context.beginPath()
      context.strokeStyle = `rgba(${palette.secondary}, ${(1 - distance / 105) * 0.055})`
      context.moveTo(left.x, left.y)
      context.lineTo(right.x, right.y)
      context.stroke()
    }
  }
}

/**
 * 绘制具有医学语义的心电样生命信号曲线。
 * @param time 当前动画经过的秒数
 * @param palette 当前工作区配色
 */
function drawBioSignal(time: number, palette: CanvasPalette) {
  if (!context) return
  const baseline = Math.min(height * 0.24, 190)
  const amplitude = 22
  const speedOffset = reduceMotion ? 0 : (time * 54) % 150
  context.save()
  context.beginPath()
  for (let x = -150; x <= width + 150; x += 2) {
    const cycle = ((x + speedOffset) % 150 + 150) % 150
    let value = 0
    if (cycle > 42 && cycle <= 53) value = -(cycle - 42) / 11 * 5
    if (cycle > 53 && cycle <= 61) value = -5 + (cycle - 53) / 8 * 39
    if (cycle > 61 && cycle <= 68) value = 34 - (cycle - 61) / 7 * 51
    if (cycle > 68 && cycle <= 77) value = -17 + (cycle - 68) / 9 * 17
    if (cycle > 96 && cycle <= 118) value = Math.sin((cycle - 96) / 22 * Math.PI) * 8
    const y = baseline - value / 34 * amplitude
    if (x === -150) context.moveTo(x, y)
    else context.lineTo(x, y)
  }
  context.strokeStyle = `rgba(${palette.glow}, 0.22)`
  context.lineWidth = 1.2
  context.shadowColor = `rgba(${palette.glow}, 0.4)`
  context.shadowBlur = 8
  context.stroke()
  context.restore()
}

/**
 * 绘制象征生命科学研究的 DNA 双螺旋和碱基连接。
 * @param time 当前动画经过的秒数
 * @param palette 当前工作区配色
 */
function drawDnaHelix(time: number, palette: CanvasPalette) {
  if (!context || width < 600) return
  const centerX = width - 110
  const startY = height * 0.34
  const helixHeight = Math.min(310, height * 0.38)
  const phaseOffset = reduceMotion ? 0 : time * 0.42
  context.save()
  for (let strand = 0; strand < 2; strand += 1) {
    context.beginPath()
    for (let index = 0; index <= 80; index += 1) {
      const ratio = index / 80
      const phase = ratio * Math.PI * 5 + phaseOffset + strand * Math.PI
      const x = centerX + Math.sin(phase) * 33
      const y = startY + ratio * helixHeight
      if (index === 0) context.moveTo(x, y)
      else context.lineTo(x, y)
    }
    context.strokeStyle = `rgba(${strand ? palette.secondary : palette.primary}, 0.13)`
    context.lineWidth = 1.1
    context.stroke()
  }
  for (let index = 0; index <= 20; index += 1) {
    const ratio = index / 20
    const phase = ratio * Math.PI * 5 + phaseOffset
    const x1 = centerX + Math.sin(phase) * 33
    const x2 = centerX + Math.sin(phase + Math.PI) * 33
    const y = startY + ratio * helixHeight
    context.beginPath()
    context.strokeStyle = `rgba(${palette.glow}, 0.08)`
    context.moveTo(x1, y)
    context.lineTo(x2, y)
    context.stroke()
  }
  context.restore()
}

/**
 * 绘制科研数据标记和随工作区变化的数值标签。
 * @param time 当前动画经过的秒数
 * @param palette 当前工作区配色
 */
function drawDataReadouts(time: number, palette: CanvasPalette) {
  if (!context || width < 760) return
  const currentContext = context
  const labels: Record<WorkspaceKey, string[]> = {
    consult: ['TRIAGE  ACTIVE', 'RAG  HYBRID', 'CITATION  VERIFY'],
    atlas: ['SYSTEM  MAP', 'ORGAN  LAYER', 'ANATOMY  EDU'],
    research: ['BM25  100', 'FAISS  100', 'RERANK  040'],
    knowledge: ['PROVENANCE', 'VERSION  CTRL', 'POLICY  DENY'],
    monitor: ['INDEX  READY', 'MODEL  ONLINE', 'SAFETY  10/10'],
  }
  currentContext.save()
  currentContext.font = '10px ui-monospace, SFMono-Regular, Menlo, monospace'
  currentContext.textAlign = 'left'
  labels[props.mode].forEach((label, index) => {
    const opacity = 0.08 + Math.sin(time * 0.6 + index) * 0.018
    currentContext.fillStyle = `rgba(${palette.primary}, ${opacity})`
    currentContext.fillText(label, 32, height - 88 + index * 18)
  })
  currentContext.restore()
}

/**
 * 执行单帧绘制并申请下一动画帧。
 * @param timestamp 浏览器提供的高精度时间戳
 */
function renderFrame(timestamp: number) {
  if (!context) return
  if (!startedAt) startedAt = timestamp
  const time = (timestamp - startedAt) / 1000
  const palette = palettes[props.mode]
  context.clearRect(0, 0, width, height)
  drawMeasurementGrid(time, palette)
  drawParticles(time, palette)
  drawBioSignal(time, palette)
  drawDnaHelix(time, palette)
  drawDataReadouts(time, palette)
  if (!reduceMotion) animationFrame = window.requestAnimationFrame(renderFrame)
}

/**
 * 重新开始绘制，确保主题切换后立即更新 Canvas 配色。
 */
function restartAnimation() {
  window.cancelAnimationFrame(animationFrame)
  startedAt = 0
  animationFrame = window.requestAnimationFrame(renderFrame)
}

/**
 * 页面进入后台时暂停动画，恢复可见后继续绘制。
 */
function handleVisibilityChange() {
  if (document.hidden) {
    window.cancelAnimationFrame(animationFrame)
    return
  }
  restartAnimation()
}

onMounted(() => {
  reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  resizeCanvas()
  if (canvasRef.value) {
    resizeObserver = new ResizeObserver(resizeCanvas)
    resizeObserver.observe(canvasRef.value)
  }
  document.addEventListener('visibilitychange', handleVisibilityChange)
  restartAnimation()
})

watch(() => props.mode, restartAnimation)

onBeforeUnmount(() => {
  window.cancelAnimationFrame(animationFrame)
  resizeObserver?.disconnect()
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
</script>

<template>
  <canvas ref="canvasRef" class="scientific-canvas" aria-hidden="true" />
</template>
