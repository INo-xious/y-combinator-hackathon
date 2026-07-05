import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* Transpile Three.js packages for Next.js compatibility */
  transpilePackages: ['three', '@react-three/fiber', '@react-three/drei', '@react-three/postprocessing'],
};

export default nextConfig;
