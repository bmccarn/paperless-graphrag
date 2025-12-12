'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import dynamic from 'next/dynamic';
import { GraphControls } from './graph-controls';
import { GraphLegend } from './graph-legend';
import { GraphSidebar } from './graph-sidebar';
import { useGraphStore } from '@/lib/stores';
import { useGraphData, useGraphOverview } from '@/lib/hooks/use-graph';
import { getEntity } from '@/lib/api/graph';
import { Loader2 } from 'lucide-react';
import type { Entity, EntityDetail, Relationship } from '@/types';

// Dynamically import the ForceGraphClient with SSR disabled
const ForceGraphClient = dynamic(
  () => import('./force-graph-client').then((mod) => mod.ForceGraphClient),
  {
    ssr: false,
    loading: () => (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    ),
  }
);

// Type colors - vibrant and saturated
// These match the entityCategories in graph-legend.tsx
const TYPE_COLORS: Record<string, string> = {
  // People - Vibrant blue
  'person': '#4A90E2',
  'officer': '#4A90E2',
  'shareholder': '#4A90E2',
  // Organizations - Vibrant green
  'organization': '#2ECC71',
  // Tax - Vibrant orange
  'tax preparer': '#E67E22',
  'tax form': '#E67E22',
  'tax schedule': '#E67E22',
  'tax identification number': '#E67E22',
  'shareholder record': '#E67E22',
  // Financial - Vibrant teal
  'financial account': '#1ABC9C',
  'billing statement': '#1ABC9C',
  'transaction': '#1ABC9C',
  'monetary amount': '#1ABC9C',
  // Training - Vibrant purple
  'certification': '#9B59B6',
  'training course': '#9B59B6',
  'technical manual': '#9B59B6',
  'hardware component': '#9B59B6',
  // Insurance - Vibrant pink
  'insurance policy': '#E74C8C',
  'insurance endorsement': '#E74C8C',
  'insurance claim': '#E74C8C',
  'policy provision': '#E74C8C',
  // Healthcare - Vibrant red
  'medical benefit': '#E74C3C',
  'healthcare service': '#E74C3C',
  // Legal/Govt - Vibrant gold
  'government benefits program': '#F1C40F',
  'legal election/consent': '#F1C40F',
  'statute or regulation': '#F1C40F',
  // Other - Cool gray-blue
  'appraisal': '#7F8C9A',
  'address': '#7F8C9A',
  'date/event': '#7F8C9A',
  'electronic signature or pin': '#7F8C9A',
};

// Default color for unknown types
const DEFAULT_COLOR = '#7F8C9A';

// Helper to lighten a hex color
function lightenColor(hex: string, percent: number): string {
  const num = parseInt(hex.replace('#', ''), 16);
  const r = Math.min(255, (num >> 16) + Math.round(2.55 * percent));
  const g = Math.min(255, ((num >> 8) & 0x00FF) + Math.round(2.55 * percent));
  const b = Math.min(255, (num & 0x0000FF) + Math.round(2.55 * percent));
  return `#${(0x1000000 + r * 0x10000 + g * 0x100 + b).toString(16).slice(1)}`;
}

// Helper to darken a hex color
function darkenColor(hex: string, percent: number): string {
  const num = parseInt(hex.replace('#', ''), 16);
  const r = Math.max(0, (num >> 16) - Math.round(2.55 * percent));
  const g = Math.max(0, ((num >> 8) & 0x00FF) - Math.round(2.55 * percent));
  const b = Math.max(0, (num & 0x0000FF) - Math.round(2.55 * percent));
  return `#${(0x1000000 + r * 0x10000 + g * 0x100 + b).toString(16).slice(1)}`;
}

// Get color for a node type (matches legend)
function getNodeColor(type: string): string {
  const normalizedType = type.toLowerCase();
  return TYPE_COLORS[normalizedType] || DEFAULT_COLOR;
}

// Generate a hex color for community-based coloring (vibrant)
function getCommunityColor(communityId: string | undefined): string {
  if (!communityId) return DEFAULT_COLOR;
  // Use hash of community ID to generate consistent colors
  let hash = 0;
  for (let i = 0; i < communityId.length; i++) {
    hash = communityId.charCodeAt(i) + ((hash << 5) - hash);
  }
  const hue = Math.abs(hash % 360);
  // Convert HSL to hex (high saturation, good lightness)
  return hslToHex(hue, 70, 55);
}

// Convert HSL to Hex
function hslToHex(h: number, s: number, l: number): string {
  s /= 100;
  l /= 100;
  const a = s * Math.min(l, 1 - l);
  const f = (n: number) => {
    const k = (n + h / 30) % 12;
    const color = l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
    return Math.round(255 * color).toString(16).padStart(2, '0');
  };
  return `#${f(0)}${f(8)}${f(4)}`;
}

// Debounce hook
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

// Graph node type for force-graph
interface ForceGraphNode {
  id: string;
  name: string;
  type: string;
  description: string;
  community_id?: string;
  degree: number;
  val: number;
  color: string;  // Color assigned based on type or community (matches legend)
  x?: number;
  y?: number;
  z?: number;
}

// Graph link type for force-graph
interface ForceGraphLink {
  source: string | ForceGraphNode;
  target: string | ForceGraphNode;
  type: string;
  description?: string;
}

// Graph data type
interface GraphData {
  nodes: ForceGraphNode[];
  links: ForceGraphLink[];
}

const INITIAL_LIMIT = 200;
const LOAD_MORE_INCREMENT = 100;
const MAX_LIMIT = 1000;

interface GraphContainerProps {
  focusEntityId?: string;
}

export function GraphContainer({ focusEntityId }: GraphContainerProps) {
  const graphRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const { overview, isLoading: overviewLoading } = useGraphOverview();
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<string | null>(null);
  const [limit, setLimit] = useState(INITIAL_LIMIT);
  const [isMounted, setIsMounted] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isCssFullscreen, setIsCssFullscreen] = useState(false); // CSS fallback for mobile

  // For direct entity focus
  const [focusedEntity, setFocusedEntity] = useState<EntityDetail | null>(null);
  const [focusLoading, setFocusLoading] = useState(false);

  // Debounce search to prevent reloading on every keystroke
  const debouncedSearch = useDebounce(searchQuery, 500);

  // Set mounted state on client
  useEffect(() => {
    setIsMounted(true);
  }, []);

  // Handle fullscreen toggle - use native Fullscreen API when available (desktop),
  // fall back to CSS fixed positioning for mobile (iOS Safari doesn't support Fullscreen API)
  const toggleFullscreen = useCallback(async () => {
    const elem = containerRef.current;
    if (!elem) return;

    // Check if native fullscreen API is available and we're not on mobile
    const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
    const fullscreenAvailable = document.fullscreenEnabled ||
      (document as any).webkitFullscreenEnabled;

    if (!isMobile && fullscreenAvailable) {
      // Use native Fullscreen API for desktop
      if (!document.fullscreenElement && !(document as any).webkitFullscreenElement) {
        // Enter fullscreen
        try {
          if (elem.requestFullscreen) {
            await elem.requestFullscreen();
          } else if ((elem as any).webkitRequestFullscreen) {
            await (elem as any).webkitRequestFullscreen();
          }
          setIsFullscreen(true);
          setIsCssFullscreen(false);
        } catch (err) {
          console.error('Failed to enter fullscreen:', err);
        }
      } else {
        // Exit fullscreen
        try {
          if (document.exitFullscreen) {
            await document.exitFullscreen();
          } else if ((document as any).webkitExitFullscreen) {
            await (document as any).webkitExitFullscreen();
          }
          setIsFullscreen(false);
          setIsCssFullscreen(false);
        } catch (err) {
          console.error('Failed to exit fullscreen:', err);
        }
      }
    } else {
      // Fall back to CSS-based fullscreen for mobile
      setIsFullscreen((prev) => !prev);
      setIsCssFullscreen((prev) => !prev);
    }
  }, []);

  const { entities, relationships, isLoading, error } = useGraphData({
    limit,
    search: debouncedSearch || undefined,
    type: typeFilter || undefined,
  });

  // Get state from store
  const {
    selectedNodeId,
    hoveredNodeId,
    is3DMode,
    sizeBy,
    colorBy,
    selectNode,
    setHoveredNode,
  } = useGraphStore();

  // Fetch specific entity when focusEntityId is provided
  useEffect(() => {
    if (focusEntityId) {
      setFocusLoading(true);
      getEntity(focusEntityId)
        .then((entity) => {
          setFocusedEntity(entity);
        })
        .catch((err) => {
          console.error('Failed to fetch entity:', err);
          setFocusedEntity(null);
        })
        .finally(() => {
          setFocusLoading(false);
        });
    } else {
      setFocusedEntity(null);
    }
  }, [focusEntityId]);

  // Reset limit when search or filter changes
  useEffect(() => {
    setLimit(INITIAL_LIMIT);
  }, [debouncedSearch, typeFilter]);

  const handleLoadMore = useCallback(() => {
    setLimit((prev) => Math.min(prev + LOAD_MORE_INCREMENT, MAX_LIMIT));
  }, []);

  const canLoadMore = entities.length >= limit && limit < MAX_LIMIT;

  // Auto-select focused entity
  useEffect(() => {
    if (focusedEntity) {
      selectNode(focusedEntity.id);
    }
  }, [focusedEntity, selectNode]);

  // Transform entities and relationships to force-graph format
  const graphData: GraphData = useMemo(() => {
    // Create a set of entity IDs/names for quick lookup
    const entityLookup = new Map<string, Entity>();
    entities.forEach((e) => {
      entityLookup.set(e.id, e);
      entityLookup.set(e.name, e);
    });

    // Transform entities to nodes with colors that match the legend
    const nodes: ForceGraphNode[] = entities.map((entity) => {
      const degree = entity.degree || 0;
      // Color based on type (matches legend) or community
      const color = colorBy === 'type'
        ? getNodeColor(entity.type)
        : getCommunityColor(entity.community_id);
      // Size calculation: use log scale for degree to prevent massive nodes
      // Range: 1 (uniform) to ~3 (highly connected)
      const sizeVal = sizeBy === 'degree'
        ? 1 + Math.log10(Math.max(1, degree) + 1) * 0.8
        : 1;
      return {
        id: entity.id,
        name: entity.name,
        type: entity.type,
        description: entity.description,
        community_id: entity.community_id,
        degree,
        val: sizeVal,
        color,
      };
    });

    // Transform relationships to links (only if both source and target exist)
    const links: ForceGraphLink[] = relationships
      .filter((rel) => {
        const sourceExists = entityLookup.has(rel.source);
        const targetExists = entityLookup.has(rel.target);
        return sourceExists && targetExists;
      })
      .map((rel) => {
        const sourceEntity = entityLookup.get(rel.source);
        const targetEntity = entityLookup.get(rel.target);
        return {
          source: sourceEntity?.id || rel.source,
          target: targetEntity?.id || rel.target,
          type: rel.type,
          description: rel.description,
        };
      });

    return { nodes, links };
  }, [entities, relationships, sizeBy, colorBy]);

  // Handle node click - select and focus camera
  const handleNodeClick = useCallback(
    (node: ForceGraphNode) => {
      selectNode(node.id);

      // Focus camera on node
      if (graphRef.current && node.x !== undefined && node.y !== undefined) {
        const distance = 200;
        if (is3DMode) {
          const z = node.z || 0;
          graphRef.current.cameraPosition(
            { x: node.x, y: node.y, z: z + distance },
            { x: node.x, y: node.y, z },
            1000
          );
        } else {
          graphRef.current.centerAt(node.x, node.y, 1000);
          graphRef.current.zoom(3, 1000);
        }
      }
    },
    [selectNode, is3DMode]
  );

  // Handle node hover
  const handleNodeHover = useCallback(
    (node: ForceGraphNode | null) => {
      setHoveredNode(node?.id || null);
    },
    [setHoveredNode]
  );

  // Handle background click - deselect
  const handleBackgroundClick = useCallback(() => {
    selectNode(null);
  }, [selectNode]);

  // Reset view to fit all nodes
  const handleResetView = useCallback(() => {
    const fg = graphRef.current;
    if (!fg) return;

    if (is3DMode) {
      // For 3D: zoom to fit all nodes
      fg.zoomToFit(1000, 100);
    } else {
      // For 2D: zoom to fit all nodes with padding
      fg.zoomToFit(1000, 50);
    }
  }, [is3DMode]);

  // Configure force simulation for maximum node spreading
  const handleEngineInit = useCallback((fg: any) => {
    // Store reference for reset
    graphRef.current = fg;

    // Very strong repulsion force to push nodes far apart
    fg.d3Force('charge')?.strength(-2000);

    // Much longer link distance for more spacing
    fg.d3Force('link')?.distance(300);

    // Minimal center force - allow nodes to spread out
    fg.d3Force('center')?.strength(0.005);

    // Add collision force to prevent node overlap
    import('d3-force').then(({ forceCollide }) => {
      fg.d3Force('collision', forceCollide(30));
      fg.d3ReheatSimulation();
    });

    // Reheat simulation to apply new forces
    fg.d3ReheatSimulation();

    // Force a refresh and then zoom to fit after simulation settles
    setTimeout(() => {
      if (fg.refresh) {
        fg.refresh();
      }

      // Wait for simulation to settle, then zoom to fit all nodes
      setTimeout(() => {
        fg.zoomToFit(2000, 80); // 2 second animation, 80px padding
      }, 500);
    }, 200);
  }, []);

  // Search handler
  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query);
  }, []);

  // Type filter handler
  const handleTypeFilter = useCallback((type: string | null) => {
    setTypeFilter(type);
  }, []);

  // Reset handler - clears local search and filter state
  const handleReset = useCallback(() => {
    setSearchQuery('');
    setTypeFilter(null);
    setLimit(INITIAL_LIMIT);
  }, []);

  // Show a subtle loading indicator when searching
  const isSearching = searchQuery !== debouncedSearch;

  // Get connected node IDs for highlighting
  const highlightNodes = useMemo(() => {
    const nodeId = hoveredNodeId || selectedNodeId;
    if (!nodeId) return new Set<string>();

    const connected = new Set<string>([nodeId]);
    graphData.links.forEach((link) => {
      const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
      const targetId = typeof link.target === 'object' ? link.target.id : link.target;
      if (sourceId === nodeId) connected.add(targetId);
      if (targetId === nodeId) connected.add(sourceId);
    });
    return connected;
  }, [hoveredNodeId, selectedNodeId, graphData.links]);

  // Get connected link IDs for highlighting
  const highlightLinks = useMemo(() => {
    const nodeId = hoveredNodeId || selectedNodeId;
    if (!nodeId) return new Set<string>();

    const connected = new Set<string>();
    graphData.links.forEach((link, idx) => {
      const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
      const targetId = typeof link.target === 'object' ? link.target.id : link.target;
      if (sourceId === nodeId || targetId === nodeId) {
        connected.add(`${sourceId}-${targetId}`);
      }
    });
    return connected;
  }, [hoveredNodeId, selectedNodeId, graphData.links]);

  // Lock body scroll when in CSS-based fullscreen mode (mobile fallback only)
  useEffect(() => {
    if (isCssFullscreen) {
      // Prevent body scrolling on mobile CSS fullscreen
      document.body.style.overflow = 'hidden';
      document.body.style.position = 'fixed';
      document.body.style.width = '100%';
      document.body.style.height = '100%';
    } else {
      // Restore body scrolling
      document.body.style.overflow = '';
      document.body.style.position = '';
      document.body.style.width = '';
      document.body.style.height = '';
    }

    return () => {
      // Cleanup on unmount
      document.body.style.overflow = '';
      document.body.style.position = '';
      document.body.style.width = '';
      document.body.style.height = '';
    };
  }, [isCssFullscreen]);

  // Listen for fullscreen change events (Escape key, browser exit)
  useEffect(() => {
    const handleFullscreenChange = () => {
      const isCurrentlyFullscreen = !!(document.fullscreenElement || (document as any).webkitFullscreenElement);
      setIsFullscreen(isCurrentlyFullscreen);
      // Native fullscreen never uses CSS fullscreen
      if (!isCurrentlyFullscreen) {
        setIsCssFullscreen(false);
      }
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);

    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      document.removeEventListener('webkitfullscreenchange', handleFullscreenChange);
    };
  }, []);

  // Custom 2D node rendering - large visible nodes
  const nodeCanvasObject = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const isHighlighted = highlightNodes.has(node.id);
    // Larger size for better visibility
    const baseSize = (node.val || 1) * 16;
    const size = isHighlighted ? baseSize * 1.3 : baseSize;
    const x = node.x || 0;
    const y = node.y || 0;
    const color = node.color || DEFAULT_COLOR;

    // Draw solid core with gradient for depth
    const coreGradient = ctx.createRadialGradient(
      x - size * 0.3, y - size * 0.3, 0,
      x, y, size
    );
    coreGradient.addColorStop(0, lightenColor(color, 30));
    coreGradient.addColorStop(0.5, color);
    coreGradient.addColorStop(1, darkenColor(color, 20));

    ctx.beginPath();
    ctx.arc(x, y, size, 0, Math.PI * 2);
    ctx.fillStyle = coreGradient;
    ctx.fill();

    // Add subtle border for definition
    ctx.strokeStyle = 'rgba(255,255,255,0.15)';
    ctx.lineWidth = 1;
    ctx.stroke();
  }, [highlightNodes]);

  // Pointer area for 2D nodes (larger than visual for easier clicking)
  const nodePointerAreaPaint = useCallback((node: any, color: string, ctx: CanvasRenderingContext2D) => {
    const size = ((node.val || 1) * 16) * 1.2;
    ctx.beginPath();
    ctx.arc(node.x || 0, node.y || 0, size, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
  }, []);

  // Loading state (also wait for client-side mount)
  if (!isMounted || isLoading || overviewLoading || focusLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Data error state
  if (error) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center space-y-2">
          <p className="text-destructive">Failed to load graph data</p>
          <p className="text-sm text-muted-foreground">{error.message}</p>
        </div>
      </div>
    );
  }

  // Empty state
  if (entities.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center space-y-2">
          <p className="text-lg font-medium">No entities found</p>
          <p className="text-sm text-muted-foreground">
            Run a sync to populate the knowledge graph
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={`h-full relative ${
        isCssFullscreen
          ? 'fixed inset-0 z-50 w-screen h-screen overflow-hidden touch-none'
          : ''
      }`}
      style={{
        backgroundColor: '#0a0a14',
        ...(isCssFullscreen ? { touchAction: 'none' } : {})
      }}
    >
      {/* Clean black background */}

      <ForceGraphClient
        key={`graph-${is3DMode ? '3d' : '2d'}-${sizeBy}-${colorBy}`}
        fgRef={graphRef}
        is3DMode={is3DMode}
        graphData={graphData}
        // Node configuration - use colors assigned in graphData (matches legend)
        nodeLabel={(node: any) =>
          `<div style="padding: 8px; background: rgba(0,0,0,0.9); border-radius: 6px; max-width: 300px; border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 4px 20px rgba(0,0,0,0.5);">
            <strong style="color: ${node.color}">${node.name}</strong><br/>
            <small style="opacity: 0.7">${node.type}</small><br/>
            ${node.description ? `<small style="opacity: 0.6">${node.description.substring(0, 100)}${node.description.length > 100 ? '...' : ''}</small>` : ''}
          </div>`
        }
        nodeColor={(node: any) => node.color}
        nodeVal={(node: any) => node.val}
        nodeRelSize={6}
        // 2D custom rendering
        nodeCanvasObject={nodeCanvasObject}
        nodePointerAreaPaint={nodePointerAreaPaint}
        // Link configuration - thin white lines
        linkColor={(link: any) => {
          const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
          const targetId = typeof link.target === 'object' ? link.target.id : link.target;
          const linkKey = `${sourceId}-${targetId}`;

          if (highlightLinks.size === 0) {
            return 'rgba(255,255,255,0.4)';
          }
          if (highlightLinks.has(linkKey)) {
            return 'rgba(255,255,255,0.9)';
          }
          return 'rgba(255,255,255,0.08)';
        }}
        linkWidth={(link: any) => {
          const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
          const targetId = typeof link.target === 'object' ? link.target.id : link.target;
          const linkKey = `${sourceId}-${targetId}`;

          if (highlightLinks.size > 0 && highlightLinks.has(linkKey)) {
            return 1.5;
          }
          return 0.8; // Thin lines
        }}
        // Curved links with noticeable particles
        linkCurvature={0.12}
        linkDirectionalParticles={(link: any) => {
          const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
          const targetId = typeof link.target === 'object' ? link.target.id : link.target;
          const linkKey = `${sourceId}-${targetId}`;
          if (highlightLinks.size > 0) {
            return highlightLinks.has(linkKey) ? 5 : 0;
          }
          return 3;
        }}
        linkDirectionalParticleSpeed={0.002}
        linkDirectionalParticleWidth={4}
        linkDirectionalParticleColor={(link: any) => {
          const sourceColor = typeof link.source === 'object' ? link.source.color : null;
          return sourceColor || '#ffffff';
        }}
        // Interaction
        onNodeClick={(node: any) => handleNodeClick(node)}
        onNodeHover={(node: any) => handleNodeHover(node)}
        onBackgroundClick={handleBackgroundClick}
        // Simulation - longer warmup for better initial spread
        warmupTicks={200}
        cooldownTicks={100}
        d3AlphaDecay={0.01}
        d3VelocityDecay={0.3}
        onEngineInit={handleEngineInit}
        // Deep space background
        backgroundColor="#000000"
        // 3D specific props - higher link opacity for visibility
        nodeOpacity={1}
        linkOpacity={0.8}
        nodeResolution={16}
        enableNodeDrag={true}
        enableNavigationControls={true}
        showNavInfo={false}
        enableBloom={false}
      />

      <GraphControls
        overview={overview}
        onSearch={handleSearch}
        onTypeFilter={handleTypeFilter}
        onReset={handleReset}
        isSearching={isSearching}
        entityCount={entities.length}
        onLoadMore={handleLoadMore}
        canLoadMore={canLoadMore}
        isFullscreen={isFullscreen}
        onToggleFullscreen={toggleFullscreen}
        onResetView={handleResetView}
        portalContainer={containerRef.current}
      />
      <GraphLegend />
      <GraphSidebar
        entities={entities}
        relationships={relationships}
        focusedEntity={focusedEntity || undefined}
      />
    </div>
  );
}
