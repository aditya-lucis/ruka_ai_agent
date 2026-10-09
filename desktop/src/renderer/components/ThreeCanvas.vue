<template>
  <div ref="containerRef" class="absolute inset-0 pointer-events-none overflow-hidden z-0">
    <!-- Atmospheric Ambient Gradient Layers -->
    <div class="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-purple-900/25 via-slate-950/60 to-[#07050e] pointer-events-none"></div>
    <div class="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-purple-600/10 rounded-full blur-[120px] pointer-events-none"></div>
    
    <!-- Three.js Canvas -->
    <canvas ref="canvasRef" class="w-full h-full block relative z-10"></canvas>
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

let magicCircleGroup: THREE.Group;
let outerRingMesh: THREE.LineSegments;
let innerRuneMesh: THREE.Mesh;
let particlesMesh: THREE.Points;

let targetMouseX = 0;
let targetMouseY = 0;
let currentMouseX = 0;
let currentMouseY = 0;

// Soft glowing round particle texture
function createParticleTexture(): THREE.CanvasTexture {
  const size = 64;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d')!;

  const gradient = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  gradient.addColorStop(0, 'rgba(255, 255, 255, 1)');
  gradient.addColorStop(0.25, 'rgba(216, 180, 254, 0.9)');
  gradient.addColorStop(0.6, 'rgba(168, 85, 247, 0.4)');
  gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');

  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, size, size);

  const texture = new THREE.CanvasTexture(canvas);
  texture.needsUpdate = true;
  return texture;
}

// Arcane Ritual Ring Texture
function createArcaneCircleTexture(): THREE.CanvasTexture {
  const size = 1024;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d')!;

  ctx.clearRect(0, 0, size, size);
  const cx = size / 2;
  const cy = size / 2;

  // Outer ambient aura
  const gradient = ctx.createRadialGradient(cx, cy, 250, cx, cy, 500);
  gradient.addColorStop(0, 'rgba(168, 85, 247, 0.35)');
  gradient.addColorStop(0.6, 'rgba(147, 51, 234, 0.15)');
  gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
  ctx.fillStyle = gradient;
  ctx.beginPath();
  ctx.arc(cx, cy, 500, 0, Math.PI * 2);
  ctx.fill();

  ctx.strokeStyle = '#c084fc';
  ctx.lineWidth = 3.5;
  ctx.shadowColor = '#e9d5ff';
  ctx.shadowBlur = 18;

  // Outer primary ring
  ctx.beginPath();
  ctx.arc(cx, cy, 470, 0, Math.PI * 2);
  ctx.stroke();

  // Secondary fine ring
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(cx, cy, 435, 0, Math.PI * 2);
  ctx.stroke();

  // 12 Astrological ray ticks
  for (let i = 0; i < 12; i++) {
    const angle = (i * Math.PI) / 6;
    const x1 = cx + Math.cos(angle) * 425;
    const y1 = cy + Math.sin(angle) * 425;
    const x2 = cx + Math.cos(angle) * 480;
    const y2 = cy + Math.sin(angle) * 480;
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.stroke();
  }

  // Middle ring with geometric runes
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  ctx.arc(cx, cy, 360, 0, Math.PI * 2);
  ctx.stroke();

  // Inner ring
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(cx, cy, 280, 0, Math.PI * 2);
  ctx.stroke();

  // Octagram stars (two concentric squares rotated)
  ctx.strokeStyle = 'rgba(233, 213, 255, 0.55)';
  ctx.lineWidth = 2;
  const points = 8;
  for (let pass = 0; pass < 2; pass++) {
    ctx.beginPath();
    for (let i = 0; i <= points; i++) {
      const angle = (i * Math.PI * 4) / points + (pass * Math.PI) / 8;
      const r = pass === 0 ? 350 : 275;
      const x = cx + Math.cos(angle) * r;
      const y = cy + Math.sin(angle) * r;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }

  // Crescent Moon motif at 12 o'clock
  ctx.fillStyle = '#f8fafc';
  ctx.shadowColor = '#c084fc';
  ctx.shadowBlur = 25;
  ctx.beginPath();
  ctx.arc(cx, cy - 470, 26, 0, Math.PI * 2);
  ctx.fill();

  ctx.globalCompositeOperation = 'destination-out';
  ctx.beginPath();
  ctx.arc(cx + 12, cy - 470, 22, 0, Math.PI * 2);
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

  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
  camera.position.z = 48;

  renderer = new THREE.WebGLRenderer({
    canvas: canvasRef.value,
    alpha: true,
    antialias: true,
    powerPreference: 'high-performance',
  });
  renderer.setSize(width, height);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

  // Magic Circle Group (Placed cleanly behind Ruka's head area)
  magicCircleGroup = new THREE.Group();
  magicCircleGroup.position.set(0, 4.5, -3);
  scene.add(magicCircleGroup);

  const texture = createArcaneCircleTexture();
  const circleGeom = new THREE.PlaneGeometry(38, 38);
  const circleMat = new THREE.MeshBasicMaterial({
    map: texture,
    transparent: true,
    opacity: 0.88,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });
  innerRuneMesh = new THREE.Mesh(circleGeom, circleMat);
  magicCircleGroup.add(innerRuneMesh);

  // Wireframe ring for delicate 3D depth
  const ringGeom = new THREE.RingGeometry(18, 19.5, 72);
  const ringEdges = new THREE.EdgesGeometry(ringGeom);
  const ringMat = new THREE.LineBasicMaterial({
    color: 0x8b5cf6,
    transparent: true,
    opacity: 0.4,
    blending: THREE.AdditiveBlending,
  });
  outerRingMesh = new THREE.LineSegments(ringEdges, ringMat);
  magicCircleGroup.add(outerRingMesh);

  // 3. Floating Astral Particles with Soft Round Glow
  const particleCount = 220;
  const particleGeom = new THREE.BufferGeometry();
  const positions = new Float32Array(particleCount * 3);
  const colors = new Float32Array(particleCount * 3);

  const particleColors = [
    new THREE.Color(0xa855f7), // purple
    new THREE.Color(0xc084fc), // lavender
    new THREE.Color(0x38bdf8), // cyan/astral
    new THREE.Color(0xfcd34d), // amber starlight
  ];

  for (let i = 0; i < particleCount; i++) {
    positions[i * 3] = (Math.random() - 0.5) * 85;
    positions[i * 3 + 1] = (Math.random() - 0.5) * 55;
    positions[i * 3 + 2] = (Math.random() - 0.5) * 30;

    const col = particleColors[Math.floor(Math.random() * particleColors.length)];
    colors[i * 3] = col.r;
    colors[i * 3 + 1] = col.g;
    colors[i * 3 + 2] = col.b;
  }

  particleGeom.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  particleGeom.setAttribute('color', new THREE.BufferAttribute(colors, 3));

  const particleTexture = createParticleTexture();
  const particleMat = new THREE.PointsMaterial({
    size: 1.6,
    map: particleTexture,
    vertexColors: true,
    transparent: true,
    opacity: 0.75,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });

  particlesMesh = new THREE.Points(particleGeom, particleMat);
  scene.add(particlesMesh);

  const clock = new THREE.Clock();

  function animate() {
    animationFrameId = requestAnimationFrame(animate);
    const elapsedTime = clock.getElapsedTime();

    if (innerRuneMesh) {
      innerRuneMesh.rotation.z = elapsedTime * 0.05;
    }
    if (outerRingMesh) {
      outerRingMesh.rotation.z = -elapsedTime * 0.035;
    }

    // Dynamic Pulsation
    const targetScale = props.isSpeaking
      ? 1 + Math.sin(elapsedTime * 6) * 0.04
      : props.isRecording
      ? 1 + Math.sin(elapsedTime * 8) * 0.03
      : 1 + Math.sin(elapsedTime * 1.5) * 0.012;

    magicCircleGroup.scale.set(targetScale, targetScale, 1);

    // Drifting particles
    const posAttr = particleGeom.attributes.position as THREE.BufferAttribute;
    for (let i = 0; i < particleCount; i++) {
      let y = posAttr.getY(i);
      y += 0.018 + (i % 3) * 0.008;
      if (y > 28) y = -28;
      posAttr.setY(i, y);

      let x = posAttr.getX(i);
      x += Math.sin(elapsedTime * 0.8 + i) * 0.005;
      posAttr.setX(i, x);
    }
    posAttr.needsUpdate = true;

    // Smooth Parallax
    currentMouseX += (targetMouseX - currentMouseX) * 0.04;
    currentMouseY += (targetMouseY - currentMouseY) * 0.04;

    camera.position.x = currentMouseX * 2.2;
    camera.position.y = currentMouseY * 1.5;
    camera.lookAt(0, 1.5, 0);

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
  targetMouseX = normX * 0.5;
  targetMouseY = normY * 0.5;
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
