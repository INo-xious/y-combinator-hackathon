'use client';

import React, { useRef, useMemo, useEffect } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Float, MeshDistortMaterial } from '@react-three/drei';
import { EffectComposer, Bloom, ChromaticAberration } from '@react-three/postprocessing';
import * as THREE from 'three';
import { BlendFunction } from 'postprocessing';

// Pure deterministic pseudo-random helper
function pureRandom(seed: number) {
  const x = Math.sin(seed + 1) * 10000;
  return x - Math.floor(x);
}

// Camera targets and scene configurations at key scroll progress steps
const cameraKeyframes = [
  { progress: 0.0, pos: [0, 0, 5.2], lookAt: [0, 0, 0], color1: '#3b82f6', distort: 0.22, speed: 1.5 },   // Hero: Electric Blue Central Orb
  { progress: 0.18, pos: [1.8, -0.6, 4.0], lookAt: [-0.4, 0.2, 0], color1: '#ef4444', distort: 0.55, speed: 3.5 }, // Problem: Zoom in, red/distorted
  { progress: 0.35, pos: [-2.2, 0.8, 4.8], lookAt: [0.3, -0.2, 0], color1: '#8b5cf6', distort: 0.20, speed: 1.2 }, // Solution: Indigo organized path
  { progress: 0.52, pos: [0, 3.2, 3.8], lookAt: [0, -0.5, 0], color1: '#06b6d4', distort: 0.15, speed: 1.0 },   // Features: Cyan looking down
  { progress: 0.70, pos: [2.5, 0.5, 5.0], lookAt: [-0.5, 0, 0], color1: '#10b981', distort: 0.25, speed: 1.8 },   // Demo/Architecture: Emerald
  { progress: 0.88, pos: [-1.8, -1.2, 4.2], lookAt: [0.4, 0.4, 0], color1: '#ec4899', distort: 0.30, speed: 2.0 }, // Performance: Magenta
  { progress: 1.0, pos: [0, 0, 6.2], lookAt: [0, 0, 0], color1: '#3b82f6', distort: 0.25, speed: 1.5 }    // CTA: Pull back Blue/Cyan
];

function getInterpolatedState(progress: number) {
  const p = Math.max(0, Math.min(1, progress));
  
  let i = 0;
  for (; i < cameraKeyframes.length - 1; i++) {
    if (p <= cameraKeyframes[i + 1].progress) break;
  }
  
  const kf1 = cameraKeyframes[i];
  const kf2 = cameraKeyframes[i + 1];
  
  const range = kf2.progress - kf1.progress;
  const factor = range === 0 ? 0 : (p - kf1.progress) / range;
  
  const px = kf1.pos[0] + (kf2.pos[0] - kf1.pos[0]) * factor;
  const py = kf1.pos[1] + (kf2.pos[1] - kf1.pos[1]) * factor;
  const pz = kf1.pos[2] + (kf2.pos[2] - kf1.pos[2]) * factor;
  
  const lx = kf1.lookAt[0] + (kf2.lookAt[0] - kf1.lookAt[0]) * factor;
  const ly = kf1.lookAt[1] + (kf2.lookAt[1] - kf1.lookAt[1]) * factor;
  const lz = kf1.lookAt[2] + (kf2.lookAt[2] - kf1.lookAt[2]) * factor;

  const c1 = new THREE.Color(kf1.color1);
  const c2 = new THREE.Color(kf2.color1);
  const color = c1.clone().lerp(c2, factor);

  const distort = kf1.distort + (kf2.distort - kf1.distort) * factor;
  const speed = kf1.speed + (kf2.speed - kf1.speed) * factor;
  
  return {
    pos: [px, py, pz] as [number, number, number],
    lookAt: [lx, ly, lz] as [number, number, number],
    color,
    distort,
    speed
  };
}

/**
 * NeuralNodes — Pulsing glowing network points.
 */
function NeuralNodes({ 
  count = 120, 
  scrollProgress 
}: { 
  count?: number; 
  scrollProgress: React.MutableRefObject<number>;
}) {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const dummyRef = useRef<THREE.Object3D | null>(null);
  const matRef = useRef<THREE.MeshBasicMaterial>(null);
  
  const positions = useMemo(() => {
    const pos = [];
    for (let i = 0; i < count; i++) {
      const phi = Math.acos(1 - 2 * (i + 0.5) / count);
      const theta = Math.PI * (1 + Math.sqrt(5)) * i;
      
      const randVal1 = pureRandom(i * 12.3);
      const randVal2 = pureRandom(i * 45.6);
      
      const radius = 2.2 + (randVal1 - 0.5) * 0.8;
      const x = radius * Math.sin(phi) * Math.cos(theta);
      const y = radius * Math.sin(phi) * Math.sin(theta);
      const z = radius * Math.cos(phi);
      
      pos.push({ x, y, z, scale: 0.02 + randVal2 * 0.04, speed: 0.3 + randVal1 * 0.7 });
    }
    return pos;
  }, [count]);

  useFrame((state) => {
    if (!meshRef.current) return;
    const time = state.clock.elapsedTime;

    if (!dummyRef.current) {
      dummyRef.current = new THREE.Object3D();
    }
    const dummy = dummyRef.current;

    if (matRef.current) {
      const targetState = getInterpolatedState(scrollProgress.current);
      matRef.current.color.copy(targetState.color);
    }

    positions.forEach((pos, i) => {
      const floatX = pos.x + Math.sin(time * pos.speed + i) * 0.05;
      const floatY = pos.y + Math.cos(time * pos.speed * 0.7 + i * 0.5) * 0.05;
      const floatZ = pos.z + Math.sin(time * pos.speed * 0.5 + i * 0.3) * 0.05;
      
      dummy.position.set(floatX, floatY, floatZ);
      dummy.scale.setScalar(pos.scale * (1 + Math.sin(time * 2 + i) * 0.3));
      dummy.updateMatrix();
      meshRef.current!.setMatrixAt(i, dummy.matrix);
    });
    
    meshRef.current.instanceMatrix.needsUpdate = true;
  });

  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, count]}>
      <sphereGeometry args={[1, 8, 8]} />
      <meshBasicMaterial ref={matRef} transparent opacity={0.65} />
    </instancedMesh>
  );
}

/**
 * NeuralConnections — Lines connecting nearby node structures.
 */
function NeuralConnections({ 
  count = 120, 
  scrollProgress 
}: { 
  count?: number; 
  scrollProgress: React.MutableRefObject<number>;
}) {
  const geometryRef = useRef<THREE.BufferGeometry>(null);
  const matRef = useRef<THREE.LineBasicMaterial>(null);
  
  const linePositions = useMemo(() => {
    const nodePositions: { x: number; y: number; z: number }[] = [];
    for (let i = 0; i < count; i++) {
      const phi = Math.acos(1 - 2 * (i + 0.5) / count);
      const theta = Math.PI * (1 + Math.sqrt(5)) * i;
      const randVal = pureRandom(i * 78.9);
      const radius = 2.2 + (randVal - 0.5) * 0.8;
      nodePositions.push({
        x: radius * Math.sin(phi) * Math.cos(theta),
        y: radius * Math.sin(phi) * Math.sin(theta),
        z: radius * Math.cos(phi),
      });
    }
    
    const vertices: number[] = [];
    const threshold = 1.4;
    
    for (let i = 0; i < nodePositions.length; i++) {
      for (let j = i + 1; j < nodePositions.length; j++) {
        const dx = nodePositions[i].x - nodePositions[j].x;
        const dy = nodePositions[i].y - nodePositions[j].y;
        const dz = nodePositions[i].z - nodePositions[j].z;
        const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
        if (dist < threshold) {
          vertices.push(
            nodePositions[i].x, nodePositions[i].y, nodePositions[i].z,
            nodePositions[j].x, nodePositions[j].y, nodePositions[j].z,
          );
        }
      }
    }
    
    return new Float32Array(vertices);
  }, [count]);

  useEffect(() => {
    if (geometryRef.current) {
      geometryRef.current.setAttribute(
        'position',
        new THREE.BufferAttribute(linePositions, 3)
      );
    }
  }, [linePositions]);

  useFrame(() => {
    if (matRef.current) {
      const targetState = getInterpolatedState(scrollProgress.current);
      matRef.current.color.copy(targetState.color);
    }
  });

  return (
    <lineSegments>
      <bufferGeometry ref={geometryRef} />
      <lineBasicMaterial ref={matRef} transparent opacity={0.07} />
    </lineSegments>
  );
}

/**
 * CoreOrb — Organic morphing central visual core.
 */
function CoreOrb({ 
  scrollProgress, 
  scrollVelocity 
}: { 
  scrollProgress: React.MutableRefObject<number>; 
  scrollVelocity: React.MutableRefObject<number>;
}) {
  const meshRef = useRef<THREE.Mesh>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const materialRef = useRef<any>(null);

  useFrame((state) => {
    if (!meshRef.current) return;
    meshRef.current.rotation.x = state.clock.elapsedTime * 0.08;
    meshRef.current.rotation.y = state.clock.elapsedTime * 0.12;

    const targetState = getInterpolatedState(scrollProgress.current);

    if (materialRef.current) {
      materialRef.current.color.copy(targetState.color);
      materialRef.current.emissive.copy(targetState.color);
      materialRef.current.distort = targetState.distort;
      materialRef.current.speed = targetState.speed + scrollVelocity.current * 10.0;
    }
  });

  return (
    <Float speed={1.8} rotationIntensity={0.2} floatIntensity={0.4}>
      <mesh ref={meshRef}>
        <icosahedronGeometry args={[1.25, 4]} />
        <MeshDistortMaterial
          ref={materialRef}
          emissiveIntensity={0.4}
          roughness={0.15}
          metalness={0.85}
          distort={0.22}
          speed={1.5}
          transparent
          opacity={0.32}
        />
      </mesh>
    </Float>
  );
}

/**
 * DynamicPointLight — Point light updating color inside frame callback.
 */
function DynamicPointLight({ 
  scrollProgress 
}: { 
  scrollProgress: React.MutableRefObject<number>;
}) {
  const lightRef = useRef<THREE.PointLight>(null);

  useFrame(() => {
    if (lightRef.current) {
      const targetState = getInterpolatedState(scrollProgress.current);
      lightRef.current.color.copy(targetState.color);
    }
  });

  return <pointLight ref={lightRef} position={[5, 5, 5]} intensity={0.9} />;
}

/**
 * CameraController — lerps camera and implements mouse parallax.
 */
function CameraController({ 
  mouseX, 
  mouseY, 
  scrollProgress
}: { 
  mouseX: number; 
  mouseY: number; 
  scrollProgress: React.MutableRefObject<number>;
}) {
  const currentLookAt = useRef(new THREE.Vector3(0, 0, 0));
  const targetLookAtRef = useRef<THREE.Vector3 | null>(null);

  useFrame((state) => {
    const cam = state.camera;
    const targetState = getInterpolatedState(scrollProgress.current);

    // Camera target coords based on scroll + mouse parallax
    const targetX = targetState.pos[0] + mouseX * 1.2;
    const targetY = targetState.pos[1] - mouseY * 0.8;
    const targetZ = targetState.pos[2];

    // Lerp camera position using setter to avoid mutating properties directly
    cam.position.set(
      cam.position.x + (targetX - cam.position.x) * 0.04,
      cam.position.y + (targetY - cam.position.y) * 0.04,
      cam.position.z + (targetZ - cam.position.z) * 0.04
    );

    // Lerp camera lookAt
    if (!targetLookAtRef.current) {
      targetLookAtRef.current = new THREE.Vector3();
    }
    targetLookAtRef.current.set(...targetState.lookAt);
    currentLookAt.current.lerp(targetLookAtRef.current, 0.04);
    cam.lookAt(currentLookAt.current);
  });

  return null;
}

/**
 * SceneContent — fixed background content scene. Declared outside of render.
 */
function SceneContent({ 
  mouseX, 
  mouseY, 
  scrollProgress, 
  scrollVelocity 
}: { 
  mouseX: number; 
  mouseY: number; 
  scrollProgress: React.MutableRefObject<number>;
  scrollVelocity: React.MutableRefObject<number>;
}) {
  const groupRef = useRef<THREE.Group>(null);

  useFrame(() => {
    if (groupRef.current) {
      // Spin matching scroll velocity
      groupRef.current.rotation.y += 0.003 + scrollVelocity.current * 0.04;
    }
  });

  return (
    <>
      <CameraController 
        mouseX={mouseX} 
        mouseY={mouseY} 
        scrollProgress={scrollProgress}
      />
      
      <ambientLight intensity={0.2} />
      <DynamicPointLight scrollProgress={scrollProgress} />
      <pointLight position={[-5, -3, 3]} intensity={0.5} color="#8b5cf6" />
      
      <group ref={groupRef}>
        <CoreOrb 
          scrollProgress={scrollProgress} 
          scrollVelocity={scrollVelocity} 
        />
        <NeuralNodes count={130} scrollProgress={scrollProgress} />
        <NeuralConnections count={130} scrollProgress={scrollProgress} />
      </group>

      <EffectComposer>
        <Bloom
          intensity={1.2}
          luminanceThreshold={0.15}
          luminanceSmoothing={0.8}
          mipmapBlur
        />
        <ChromaticAberration
          blendFunction={BlendFunction.NORMAL}
          offset={new THREE.Vector2(0.0006, 0.0006)}
        />
      </EffectComposer>
    </>
  );
}

/**
 * NeuralScene — Fixed interactive backdrop Canvas.
 */
interface NeuralSceneProps {
  mouseX: number;
  mouseY: number;
  scrollProgress: React.MutableRefObject<number>;
  scrollVelocity: React.MutableRefObject<number>;
}

export default function NeuralScene({ mouseX, mouseY, scrollProgress, scrollVelocity }: NeuralSceneProps) {
  return (
    <div className="fixed inset-0 z-0 pointer-events-none">
      <Canvas
        camera={{ position: [0, 0, 5.2], fov: 45 }}
        dpr={[1, 1.5]}
        gl={{ 
          antialias: true, 
          alpha: true,
          powerPreference: 'high-performance',
        }}
        style={{ background: 'transparent' }}
      >
        <SceneContent 
          mouseX={mouseX} 
          mouseY={mouseY} 
          scrollProgress={scrollProgress} 
          scrollVelocity={scrollVelocity} 
        />
      </Canvas>
    </div>
  );
}
