'use client';

/**
 * ForceGraph wrapper component for Next.js
 *
 * Uses a deferred loading approach to ensure WebGL is fully initialized
 * before loading Three.js-dependent libraries.
 *
 * Enhanced with:
 * - Custom 3D node materials with emissive glow
 * - Scene lighting (ambient + point lights)
 * - Bloom post-processing
 * - Starfield background
 * - Directional particles with color inheritance
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { Loader2 } from 'lucide-react';

interface ForceGraphClientProps {
  fgRef?: React.RefObject<any>;
  is3DMode: boolean;
  graphData: any;
  nodeLabel?: (node: any) => string;
  nodeColor?: (node: any) => string;
  nodeAutoColorBy?: string | ((node: any) => string);
  nodeVal?: (node: any) => number;
  nodeRelSize?: number;
  linkDirectionalArrowLength?: number;
  linkDirectionalArrowRelPos?: number;
  linkDirectionalArrowColor?: string | ((link: any) => string);
  linkLabel?: string | ((link: any) => string);
  linkColor?: string | ((link: any) => string);
  linkWidth?: number | ((link: any) => number);
  onNodeClick?: (node: any) => void;
  onNodeHover?: (node: any) => void;
  onBackgroundClick?: () => void;
  warmupTicks?: number;
  cooldownTicks?: number;
  backgroundColor?: string;
  // Force simulation settings
  d3AlphaDecay?: number;
  d3VelocityDecay?: number;
  // 3D specific
  nodeOpacity?: number;
  linkOpacity?: number;
  nodeResolution?: number;
  enableNodeDrag?: boolean;
  enableNavigationControls?: boolean;
  showNavInfo?: boolean;
  // 2D specific
  nodeCanvasObject?: (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => void;
  nodePointerAreaPaint?: (node: any, color: string, ctx: CanvasRenderingContext2D) => void;
  // Callback to configure forces after graph is mounted
  onEngineInit?: (fg: any) => void;
  // Visual enhancement props (shared between 2D and 3D)
  enableBloom?: boolean;
  linkDirectionalParticles?: number | ((link: any) => number);
  linkDirectionalParticleSpeed?: number | ((link: any) => number);
  linkDirectionalParticleWidth?: number;
  linkDirectionalParticleColor?: (link: any) => string;
  linkCurvature?: number | ((link: any) => number);
}

// Check if WebGL is available
function isWebGLAvailable(): boolean {
  try {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
    return gl !== null;
  } catch {
    return false;
  }
}

// Parse hex color to RGB values
function hexToRgb(hex: string): { r: number; g: number; b: number } {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result
    ? {
        r: parseInt(result[1], 16) / 255,
        g: parseInt(result[2], 16) / 255,
        b: parseInt(result[3], 16) / 255,
      }
    : { r: 1, g: 1, b: 1 };
}

export function ForceGraphClient({ fgRef, is3DMode, graphData, ...props }: ForceGraphClientProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const localRef = useRef<any>(null);
  const threeRef = useRef<any>(null);
  const sceneInitialized = useRef(false);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [GraphComponent, setGraphComponent] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Use provided ref or local ref
  const graphRef = fgRef || localRef;

  // Load force-graph library dynamically after checking WebGL
  useEffect(() => {
    let mounted = true;

    const loadGraph = async () => {
      // Wait for next frame to ensure DOM is ready
      await new Promise(resolve => requestAnimationFrame(resolve));

      if (!mounted) return;

      // Check WebGL availability
      if (!isWebGLAvailable()) {
        setError('WebGL is not available in your browser. Please use a modern browser with WebGL support.');
        setIsLoading(false);
        return;
      }

      try {
        // Load Three.js for 3D mode
        if (is3DMode) {
          const [module, THREE] = await Promise.all([
            import('react-force-graph-3d'),
            import('three'),
          ]);
          if (mounted) {
            threeRef.current = THREE;
            setGraphComponent(() => module.default);
          }
        } else {
          const module = await import('react-force-graph-2d');
          if (mounted) {
            setGraphComponent(() => module.default);
          }
        }

        if (mounted) {
          setIsLoading(false);
        }
      } catch (err) {
        console.error('Failed to load force-graph library:', err);
        if (mounted) {
          setError(err instanceof Error ? err.message : 'Failed to load graph library');
          setIsLoading(false);
        }
      }
    };

    // Reset state when mode changes
    setIsLoading(true);
    setGraphComponent(null);
    setError(null);
    sceneInitialized.current = false;

    loadGraph();

    return () => {
      mounted = false;
    };
  }, [is3DMode]);

  // Update dimensions based on container size
  useEffect(() => {
    if (!containerRef.current) return;

    const updateDimensions = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        setDimensions({
          width: rect.width || 800,
          height: rect.height || 600,
        });
      }
    };

    updateDimensions();

    const resizeObserver = new ResizeObserver(updateDimensions);
    resizeObserver.observe(containerRef.current);

    return () => resizeObserver.disconnect();
  }, []);

  // Create custom 3D node - large spheres with gradient-like shading
  const nodeThreeObject = useCallback((node: any) => {
    const THREE = threeRef.current;
    if (!THREE) return null;

    // Larger size for better visibility
    const size = (node.val || 1) * 14;
    const color = node.color || '#ffffff';
    const rgb = hexToRgb(color);

    // Create sphere geometry
    const geometry = new THREE.SphereGeometry(size, 32, 32);

    // Material with good lighting response for 3D spherical look
    const material = new THREE.MeshStandardMaterial({
      color: new THREE.Color(rgb.r, rgb.g, rgb.b),
      roughness: 0.4,
      metalness: 0.1,
      envMapIntensity: 0.5,
    });

    const mesh = new THREE.Mesh(geometry, material);
    return mesh;
  }, []);

  // Loading state
  if (isLoading || !GraphComponent) {
    return (
      <div ref={containerRef} className="h-full w-full flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div ref={containerRef} className="h-full w-full flex items-center justify-center">
        <div className="text-center space-y-2">
          <p className="text-destructive">Failed to load graph visualization</p>
          <p className="text-sm text-muted-foreground">{error}</p>
        </div>
      </div>
    );
  }

  const {
    nodeOpacity,
    linkOpacity,
    nodeResolution,
    enableNodeDrag,
    enableNavigationControls,
    showNavInfo,
    nodeCanvasObject,
    nodePointerAreaPaint,
    d3AlphaDecay,
    d3VelocityDecay,
    onEngineInit,
    enableBloom,
    linkDirectionalParticles,
    linkDirectionalParticleSpeed,
    linkDirectionalParticleWidth,
    linkDirectionalParticleColor,
    linkCurvature,
    ...commonProps
  } = props;

  const graphProps = is3DMode
    ? {
        ...commonProps,
        nodeOpacity,
        linkOpacity,
        nodeResolution: nodeResolution || 20,
        enableNodeDrag,
        enableNavigationControls,
        showNavInfo,
        d3AlphaDecay,
        d3VelocityDecay,
        // Custom 3D node rendering
        nodeThreeObject,
        nodeThreeObjectExtend: false,
        // 3D link styling - thin lines
        linkWidth: 0.8,
        linkCurvature,
        // Particles for 3D
        linkDirectionalParticles,
        linkDirectionalParticleSpeed,
        linkDirectionalParticleWidth,
        linkDirectionalParticleColor,
      }
    : {
        ...commonProps,
        nodeCanvasObject,
        nodePointerAreaPaint,
        d3AlphaDecay,
        d3VelocityDecay,
        // 2D link styling with particles
        linkCurvature,
        linkDirectionalParticles,
        linkDirectionalParticleSpeed,
        linkDirectionalParticleWidth,
        linkDirectionalParticleColor,
      };

  // Callback ref to configure forces and post-processing after graph mounts
  const setGraphRef = (instance: any) => {
    if (graphRef && 'current' in graphRef) {
      (graphRef as React.MutableRefObject<any>).current = instance;
    }

    // Configure forces and effects when the graph instance is available
    if (instance && !sceneInitialized.current) {
      sceneInitialized.current = true;

      // Small delay to ensure everything is ready
      setTimeout(() => {
        // Configure forces
        if (onEngineInit) {
          onEngineInit(instance);
        }

        // 3D scene enhancements
        if (is3DMode) {
          setup3DScene(instance, dimensions, enableBloom);
        }
      }, 150);
    }
  };

  return (
    <div ref={containerRef} className="h-full w-full relative" style={{ zIndex: 1 }}>
      <GraphComponent
        ref={setGraphRef}
        graphData={graphData}
        width={dimensions.width}
        height={dimensions.height}
        {...graphProps}
      />
    </div>
  );
}

// Create radial gradient texture for node glow
function createGlowTexture(THREE: any, color: string): any {
  const size = 128;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d');

  if (ctx) {
    const gradient = ctx.createRadialGradient(
      size / 2, size / 2, 0,
      size / 2, size / 2, size / 2
    );
    gradient.addColorStop(0, color);
    gradient.addColorStop(0.3, `${color}88`);
    gradient.addColorStop(0.6, `${color}33`);
    gradient.addColorStop(1, 'transparent');

    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, size, size);
  }

  const texture = new THREE.CanvasTexture(canvas);
  texture.needsUpdate = true;
  return texture;
}

// Setup 3D scene with lighting, starfield, and bloom
async function setup3DScene(instance: any, dimensions: { width: number; height: number }, enableBloom?: boolean) {
  try {
    const THREE = await import('three');
    const scene = instance.scene();

    if (!scene) {
      console.warn('Scene not available');
      return;
    }

    // Clear existing lights (if any custom ones were added before)
    const lightsToRemove: any[] = [];
    scene.traverse((child: any) => {
      if (child.isLight && child.userData?.custom) {
        lightsToRemove.push(child);
      }
    });
    lightsToRemove.forEach((light: any) => scene.remove(light));

    // Ambient light for base illumination
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    ambientLight.userData = { custom: true };
    scene.add(ambientLight);

    // Main directional light for shadows/depth (like sun)
    const mainLight = new THREE.DirectionalLight(0xffffff, 1.0);
    mainLight.position.set(100, 150, 100);
    mainLight.userData = { custom: true };
    scene.add(mainLight);

    // Fill light from opposite side for softer shadows
    const fillLight = new THREE.DirectionalLight(0xffffff, 0.3);
    fillLight.position.set(-100, -50, -100);
    fillLight.userData = { custom: true };
    scene.add(fillLight);

    // Hemisphere light for natural sky/ground gradient
    const hemiLight = new THREE.HemisphereLight(0xffffff, 0x444444, 0.4);
    hemiLight.userData = { custom: true };
    scene.add(hemiLight);

    // Clean black background - no starfield

    // Bloom disabled for cleaner look - was causing foggy appearance
    // Can be re-enabled with lower values if desired
  } catch (err) {
    console.warn('Failed to setup 3D scene:', err);
  }
}

// Create starfield with Points
function createStarfield(THREE: any, scene: any) {
  const starsGeometry = new THREE.BufferGeometry();
  const starCount = 2000;

  const positions = new Float32Array(starCount * 3);
  const colors = new Float32Array(starCount * 3);
  const sizes = new Float32Array(starCount);

  for (let i = 0; i < starCount; i++) {
    // Random position in a large sphere
    const radius = 2000 + Math.random() * 3000;
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos((Math.random() * 2) - 1);

    positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
    positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
    positions[i * 3 + 2] = radius * Math.cos(phi);

    // Slight color variation (white to light blue/purple)
    const colorVariation = Math.random();
    if (colorVariation < 0.7) {
      // White stars
      colors[i * 3] = 0.9 + Math.random() * 0.1;
      colors[i * 3 + 1] = 0.9 + Math.random() * 0.1;
      colors[i * 3 + 2] = 1;
    } else if (colorVariation < 0.85) {
      // Blue-tinted stars
      colors[i * 3] = 0.7;
      colors[i * 3 + 1] = 0.8;
      colors[i * 3 + 2] = 1;
    } else {
      // Purple/pink tinted stars
      colors[i * 3] = 0.9;
      colors[i * 3 + 1] = 0.7;
      colors[i * 3 + 2] = 1;
    }

    // Random sizes
    sizes[i] = Math.random() * 3 + 0.5;
  }

  starsGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  starsGeometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
  starsGeometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));

  const starsMaterial = new THREE.PointsMaterial({
    size: 2,
    vertexColors: true,
    transparent: true,
    opacity: 0.8,
    sizeAttenuation: true,
  });

  const stars = new THREE.Points(starsGeometry, starsMaterial);
  stars.userData = { custom: true };
  scene.add(stars);
}

export default ForceGraphClient;
