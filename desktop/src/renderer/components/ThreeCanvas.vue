<template>
  <div ref="containerRef" class="absolute inset-0 pointer-events-none overflow-hidden z-0">
    <canvas ref="canvasRef" class="w-full h-full block"></canvas>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import * as THREE from 'three';

const props = withDefaults(
  defineProps<{
    isSpeaking?: boolean;
    isRecording?: boolean;
    mouseParallax?: { x: number; y: number };
  }>(),
  {
    isSpeaking: false,
    isRecording: false,
    mouseParallax: () => ({ x: 0, y: 0 }),
  }
);

const containerRef = ref<HTMLDivElement | null>(null);
const canvasRef = ref<HTMLCanvasElement | null>(null);

let scene: THREE.Scene;
let camera: THREE.PerspectiveCamera;
let renderer: THREE.WebGLRenderer;
let animationFrameId: number;

// Groups
let magicCircleGroup: THREE.Group;
let outerRingMesh: THREE.LineSegments;
let middleRingMesh: THREE.LineSegments;
let innerRuneMesh: THREE.Mesh;
let particlesMesh: THREE.Points;

// Mouse coordinates target
let targetMouseX = 0;
let targetMouseY = 0;
let currentMouseX = 0;
let currentMouseY = 0;

function createArcaneCircleTexture(): THREE.CanvasTexture {
  const size = 512;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d')!;

  ctx.clearRect(0, 0, size, size);
  const cx = size / 2;
  const cy = size / 2;

  // Outer glow
  const gradient = ctx.createRadialGradient(cx, cy, 140, cx, cy, 250);
  gradient.addColorStop(0, 'rgba(168, 85, 247, 0.45)');
  gradient.addColorStop(0.7, 'rgba(139, 92, 246, 0.2)');
  gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
  ctx.fillStyle = gradient;
  ctx.beginPath();
  ctx.arc(cx, cy, 250, 0, Math.PI * 2);
  ctx.fill();

  // Concentric thin rune rings
  ctx.strokeStyle = '#c084fc';
  ctx.lineWidth = 2.5;
  ctx.shadowColor = '#d8b4fe';
  ctx.shadowBlur = 12;

  // Outer primary ring
  ctx.beginPath();
  ctx.arc(cx, cy, 230, 0, Math.PI * 2);
  ctx.stroke();

  // Middle segmented ring
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.arc(cx, cy, 200, 0, Math.PI * 2);
  ctx.stroke();

  // 12 Astrological ticks / spikes
  for (let i = 0; i < 12; i++) {
    const angle = (i * Math.PI) / 6;
    const x1 = cx + Math.cos(angle) * 195;
    const y1 = cy + Math.sin(angle) * 195;
    const x2 = cx + Math.cos(angle) * 235;
    const y2 = cy + Math.sin(angle) * 235;
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.stroke();
  }

  // Inner ring
  ctx.beginPath();
  ctx.arc(cx, cy, 160, 0, Math.PI * 2);
  ctx.stroke();

  // Concentric stars (Hexagram or Octagram)
  ctx.strokeStyle = 'rgba(216, 180, 254, 0.6)';
  ctx.lineWidth = 1.2;
  const points = 8;
  for (let pass = 0; pass < 2; pass++) {
    ctx.beginPath();
    for (let i = 0; i <= points; i++) {
      const angle = (i * Math.PI * 4) / points + (pass * Math.PI) / 8;
      const r = pass === 0 ? 155 : 125;
      const x = cx + Math.cos(angle) * r;
      const y = cy + Math.sin(angle) * r;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }

  // Crescent Moon motif at apex (12 o'clock)
  ctx.fillStyle = '#f8fafc';
  ctx.shadowColor = '#c084fc';
  ctx.shadowBlur = 16;
  ctx.beginPath();
  ctx.arc(cx, cy - 232, 14, 0, Math.PI * 2);
  ctx.fill();

  ctx.globalCompositeOperation = 'destination-out';
  ctx.beginPath();
  ctx.arc(cx + 6, cy - 232, 12, 0, Math.PI * 2);
  ctx.fill();
  ctx.globalCompositeOperation = 'source-over';

  const texture = new THREE.CanvasTexture(canvas);
  texture.needsUpdate = true;
  return texture;
}

function initThree() {
  if (!canvasRef.value || !containerRef.value) return;

  const width = containerRef.value.clientWidth || window.innerWidth;
  const height = containerRef.value.clientHeight || window.innerHeight;

  // Scene & Camera
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
  camera.position.z = 50;

  // Renderer
  renderer = new THREE.WebGLRenderer({
    canvas: canvasRef.value,
    alpha: true,
    antialias: true,
    powerPreference: 'high-performance',
  });
  renderer.setSize(width, height);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

  // Magic Circle Group (Centered slightly above middle where Ruka is placed)
  magicCircleGroup = new THREE.Group();
  magicCircleGroup.position.set(0, 3.5, -2);
  scene.add(magicCircleGroup);

  // 1. Plane with Arcane Texture
  const texture = createArcaneCircleTexture();
  const circleGeom = new THREE.PlaneGeometry(36, 36);
  const circleMat = new THREE.MeshBasicMaterial({
    map: texture,
    transparent: true,
    opacity: 0.85,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });
  innerRuneMesh = new THREE.Mesh(circleGeom, circleMat);
  magicCircleGroup.add(innerRuneMesh);

  // 2. Geometry Wireframe Rings for 3D depth
  const ringGeom = new THREE.RingGeometry(16, 17.5, 64);
  const ringEdges = new THREE.EdgesGeometry(ringGeom);
  const ringMat = new THREE.LineBasicMaterial({
    color: 0x9333ea,
    transparent: true,
    opacity: 0.45,
    blending: THREE.AdditiveBlending,
  });
  outerRingMesh = new THREE.LineSegments(ringEdges, ringMat);
  magicCircleGroup.add(outerRingMesh);

  // 3. Floating Astral Dust & Particles
  const particleCount = 280;
  const particleGeom = new THREE.BufferGeometry();
  const positions = new Float32Array(particleCount * 3);
  const colors = new Float32Array(particleCount * 3);
  const scales = new Float32Array(particleCount);

  const colorChoices = [
    new THREE.Color(0xa855f7), // purple
    new THREE.Color(0xc084fc), // lavender
    new THREE.Color(0x38bdf8), // cyan
    new THREE.Color(0xfef08a), // gold
  ];

  for (let i = 0; i < particleCount; i++) {
    positions[i * 3] = (Math.random() - 0.5) * 80;
    positions[i * 3 + 1] = (Math.random() - 0.5) * 55;
    positions[i * 3 + 2] = (Math.random() - 0.5) * 35;

    const chosenColor = colorChoices[Math.floor(Math.random() * colorChoices.length)];
    colors[i * 3] = chosenColor.r;
    colors[i * 3 + 1] = chosenColor.g;
    colors[i * 3 + 2] = chosenColor.b;

    scales[i] = Math.random() * 2 + 1;
  }

  particleGeom.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  particleGeom.setAttribute('color', new THREE.BufferAttribute(colors, 3));

  const particleMat = new THREE.PointsMaterial({
    size: 0.75,
    vertexColors: true,
    transparent: true,
    opacity: 0.75,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });

  particlesMesh = new THREE.Points(particleGeom, particleMat);
  scene.add(particlesMesh);

  // Animate Loop
  const clock = new THREE.Clock();

  function animate() {
    animationFrameId = requestAnimationFrame(animate);
    const elapsedTime = clock.getElapsedTime();

    // Rotate magic circle
    if (innerRuneMesh) {
      innerRuneMesh.rotation.z = elapsedTime * 0.08;
    }
    if (outerRingMesh) {
      outerRingMesh.rotation.z = -elapsedTime * 0.05;
    }

    // Reactivity to speaking or recording
    const targetScale = props.isSpeaking
      ? 1 + Math.sin(elapsedTime * 6) * 0.05
      : props.isRecording
      ? 1 + Math.sin(elapsedTime * 10) * 0.04
      : 1 + Math.sin(elapsedTime * 1.5) * 0.015;

    magicCircleGroup.scale.set(targetScale, targetScale, 1);

    // Particles upward drift
    const posAttr = particleGeom.attributes.position as THREE.BufferAttribute;
    for (let i = 0; i < particleCount; i++) {
      let y = posAttr.getY(i);
      y += 0.025 + (i % 3) * 0.01;
      if (y > 28) y = -28;
      posAttr.setY(i, y);

      // Subtle horizontal oscillation
      let x = posAttr.getX(i);
      x += Math.sin(elapsedTime + i) * 0.008;
      posAttr.setX(i, x);
    }
    posAttr.needsUpdate = true;

    // Smooth Mouse Parallax tracking
    currentMouseX += (targetMouseX - currentMouseX) * 0.05;
    currentMouseY += (targetMouseY - currentMouseY) * 0.05;

    camera.position.x = currentMouseX * 3;
    camera.position.y = currentMouseY * 2;
    camera.lookAt(0, 2, 0);

    renderer.render(scene, camera);
  }

  animate();
}

function handleResize() {
  if (!containerRef.value || !renderer || !camera) return;
  const width = containerRef.value.clientWidth;
  const height = containerRef.value.clientHeight;
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  renderer.setSize(width, height);
}

function handleMouseMove(e: MouseEvent) {
  const normX = (e.clientX / window.innerWidth) * 2 - 1;
  const normY = -(e.clientY / window.innerHeight) * 2 + 1;
  targetMouseX = normX * 0.6;
  targetMouseY = normY * 0.6;
}

onMounted(() => {
  initThree();
  window.addEventListener('resize', handleResize);
  window.addEventListener('mousemove', handleMouseMove);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  window.removeEventListener('mousemove', handleMouseMove);
  if (animationFrameId) cancelAnimationFrame(animationFrameId);
  renderer?.dispose();
});
</script>
