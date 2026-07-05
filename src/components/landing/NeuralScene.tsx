'use client';

import React, { useRef, useMemo, useEffect } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Float, MeshDistortMaterial } from '@react-three/drei';
import { EffectComposer, Bloom, ChromaticAberration } from '@react-three/postprocessing';
import * as THREE from 'three';
import { BlendFunction } from 'postprocessing';

/**
 * NeuralNode — Individual node in the neural network visualization.
 * Small glowing sphere that pulses gently.
 */
function NeuralNodes({ count = 120 }: { count?: number }) {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  
  // Generate random positions on a sphere surface with some noise
  const positions = useMemo(() => {
    const pos = [];
    for (let i = 0; i < count; i++) {
      // Fibonacci sphere distribution for even spacing
      const phi = Math.acos(1 - 2 * (i + 0.5) / count);
      const theta = Math.PI * (1 + Math.sqrt(5)) * i;
      
      const radius = 2.2 + (Math.random() - 0.5) * 0.8;
      const x = radius * Math.sin(phi) * Math.cos(theta);
      const y = radius * Math.sin(phi) * Math.sin(theta);
      const z = radius * Math.cos(phi);
      
      pos.push({ x, y, z, scale: 0.02 + Math.random() * 0.04, speed: 0.3 + Math.random() * 0.7 });
    }
    return pos;
  }, [count]);

  useFrame((state) => {
    if (!meshRef.current) return;
    const time = state.clock.elapsedTime;

    positions.forEach((pos, i) => {
      // Gentle floating motion
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
      <meshBasicMaterial color="#60a5fa" transparent opacity={0.8} />
    </instancedMesh>
  );
}

/**
 * NeuralConnections — Glowing line segments connecting nearby neural nodes.
 * Creates the neural network web aesthetic.
 */
function NeuralConnections({ count = 120 }: { count?: number }) {
  const geometryRef = useRef<THREE.BufferGeometry>(null);
  
  // Generate connection line positions
  const linePositions = useMemo(() => {
    const nodePositions: THREE.Vector3[] = [];
    for (let i = 0; i < count; i++) {
      const phi = Math.acos(1 - 2 * (i + 0.5) / count);
      const theta = Math.PI * (1 + Math.sqrt(5)) * i;
      const radius = 2.2 + (Math.random() - 0.5) * 0.8;
      nodePositions.push(new THREE.Vector3(
        radius * Math.sin(phi) * Math.cos(theta),
        radius * Math.sin(phi) * Math.sin(theta),
        radius * Math.cos(phi),
      ));
    }
    
    const vertices: number[] = [];
    const threshold = 1.5;
    
    for (let i = 0; i < nodePositions.length; i++) {
      for (let j = i + 1; j < nodePositions.length; j++) {
        const dist = nodePositions[i].distanceTo(nodePositions[j]);
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

  // Set geometry attributes imperatively to avoid R3F type issues
  useEffect(() => {
    if (geometryRef.current) {
      geometryRef.current.setAttribute(
        'position',
        new THREE.BufferAttribute(linePositions, 3)
      );
    }
  }, [linePositions]);

  return (
    <lineSegments>
      <bufferGeometry ref={geometryRef} />
      <lineBasicMaterial color="#3b82f6" transparent opacity={0.08} />
    </lineSegments>
  );
}

/**
 * CoreOrb — Central glowing distorted sphere that forms the "AI core".
 * Uses MeshDistortMaterial for organic morphing effect.
 */
function CoreOrb() {
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    if (!meshRef.current) return;
    meshRef.current.rotation.x = state.clock.elapsedTime * 0.1;
    meshRef.current.rotation.y = state.clock.elapsedTime * 0.15;
  });

  return (
    <Float speed={1.5} rotationIntensity={0.2} floatIntensity={0.3}>
      <mesh ref={meshRef}>
        <icosahedronGeometry args={[1.2, 4]} />
        <MeshDistortMaterial
          color="#1d4ed8"
          emissive="#3b82f6"
          emissiveIntensity={0.4}
          roughness={0.2}
          metalness={0.8}
          distort={0.25}
          speed={2}
          transparent
          opacity={0.3}
        />
      </mesh>
    </Float>
  );
}

/**
 * CameraController — Subtly moves the camera based on mouse position.
 * Creates parallax depth effect in the 3D scene.
 */
function CameraController({ mouseX, mouseY }: { mouseX: number; mouseY: number }) {
  const { camera } = useThree();
  
  useFrame(() => {
    // Smooth interpolation toward mouse-based target
    camera.position.x += (mouseX * 1.5 - camera.position.x) * 0.02;
    camera.position.y += (-mouseY * 1.0 - camera.position.y) * 0.02;
    camera.lookAt(0, 0, 0);
  });

  return null;
}

/**
 * SceneContent — All 3D objects grouped together.
 * Separated from Canvas to enable proper React Three Fiber context.
 */
function SceneContent({ mouseX, mouseY }: { mouseX: number; mouseY: number }) {
  const groupRef = useRef<THREE.Group>(null);

  useFrame((state) => {
    if (!groupRef.current) return;
    // Slow auto-rotation
    groupRef.current.rotation.y = state.clock.elapsedTime * 0.05;
  });

  return (
    <>
      <CameraController mouseX={mouseX} mouseY={mouseY} />
      
      {/* Lighting */}
      <ambientLight intensity={0.15} />
      <pointLight position={[5, 5, 5]} intensity={0.8} color="#3b82f6" />
      <pointLight position={[-5, -3, 3]} intensity={0.4} color="#8b5cf6" />
      <pointLight position={[0, 5, -5]} intensity={0.3} color="#06b6d4" />
      
      <group ref={groupRef}>
        <CoreOrb />
        <NeuralNodes count={120} />
        <NeuralConnections count={120} />
      </group>

      {/* Post-processing effects */}
      <EffectComposer>
        <Bloom
          intensity={1.5}
          luminanceThreshold={0.1}
          luminanceSmoothing={0.9}
          mipmapBlur
        />
        <ChromaticAberration
          blendFunction={BlendFunction.NORMAL}
          offset={new THREE.Vector2(0.0005, 0.0005)}
        />
      </EffectComposer>
    </>
  );
}

/**
 * NeuralScene — Main 3D canvas component for the hero section.
 * Renders an interactive neural network orb with post-processing.
 * Responds to mouse position for parallax camera movement.
 */
interface NeuralSceneProps {
  mouseX: number;
  mouseY: number;
}

export default function NeuralScene({ mouseX, mouseY }: NeuralSceneProps) {
  return (
    <div className="absolute inset-0 z-0">
      <Canvas
        camera={{ position: [0, 0, 6], fov: 45 }}
        dpr={[1, 1.5]}
        gl={{ 
          antialias: true, 
          alpha: true,
          powerPreference: 'high-performance',
        }}
        style={{ background: 'transparent' }}
      >
        <SceneContent mouseX={mouseX} mouseY={mouseY} />
      </Canvas>
    </div>
  );
}
