'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ReactFlow,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  useReactFlow,
  type Node,
  type Edge,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { EntityNode } from './entity-node';
import { GraphControls } from './graph-controls';
import { GraphLegend } from './graph-legend';
import { GraphSidebar } from './graph-sidebar';
import { useGraphStore } from '@/lib/stores';
import { useGraphData, useGraphOverview } from '@/lib/hooks/use-graph';
import { getEntity } from '@/lib/api/graph';
import { Loader2 } from 'lucide-react';
import type { Entity, Relationship, EntityDetail } from '@/types';

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

const nodeTypes = {
  entity: EntityNode,
};

// Layout with wide spacing - type clusters arranged in a grid pattern
function calculateLayout(
  entities: Entity[],
  relationships: Relationship[]
): { nodes: Node[]; edges: Edge[] } {
  // Create a map of entity name to index
  const entityMap = new Map<string, number>();
  entities.forEach((entity, idx) => {
    entityMap.set(entity.name, idx);
    entityMap.set(entity.id, idx);
  });

  // Group entities by type for clustered layout
  const typeGroups = new Map<string, Entity[]>();
  entities.forEach((entity) => {
    const type = entity.type || 'unknown';
    if (!typeGroups.has(type)) {
      typeGroups.set(type, []);
    }
    typeGroups.get(type)!.push(entity);
  });

  // Calculate positions - arrange type clusters in a grid
  const typeArray = Array.from(typeGroups.entries());
  const numTypes = typeArray.length;
  const typeCols = Math.ceil(Math.sqrt(numTypes));
  const clusterSpacing = 1500; // Large spacing between type clusters

  const nodes: Node[] = [];

  typeArray.forEach(([type, typeEntities], typeIndex) => {
    // Position each type cluster in a grid
    const typeRow = Math.floor(typeIndex / typeCols);
    const typeCol = typeIndex % typeCols;
    const clusterCenterX = typeCol * clusterSpacing;
    const clusterCenterY = typeRow * clusterSpacing;

    // Arrange entities within each cluster in a grid with generous spacing
    const cols = Math.ceil(Math.sqrt(typeEntities.length));
    const nodeSpacing = 250; // Generous spacing between nodes

    typeEntities.forEach((entity, entityIndex) => {
      const row = Math.floor(entityIndex / cols);
      const col = entityIndex % cols;
      const gridWidth = (cols - 1) * nodeSpacing;
      const gridHeight = (Math.ceil(typeEntities.length / cols) - 1) * nodeSpacing;

      const x = clusterCenterX + col * nodeSpacing - gridWidth / 2;
      const y = clusterCenterY + row * nodeSpacing - gridHeight / 2;

      // Add small jitter to prevent perfect overlaps
      const jitterX = (Math.random() - 0.5) * 30;
      const jitterY = (Math.random() - 0.5) * 30;

      nodes.push({
        id: entity.id || entity.name,
        type: 'entity',
        position: {
          x: x + jitterX,
          y: y + jitterY,
        },
        data: {
          name: entity.name,
          type: entity.type,
          description: entity.description,
        },
      });
    });
  });

  // Create edges from relationships
  const edges: Edge[] = relationships
    .filter((rel) => {
      const sourceExists = entityMap.has(rel.source);
      const targetExists = entityMap.has(rel.target);
      return sourceExists && targetExists;
    })
    .map((rel, idx) => {
      const sourceEntity = entities.find(
        (e) => e.name === rel.source || e.id === rel.source
      );
      const targetEntity = entities.find(
        (e) => e.name === rel.target || e.id === rel.target
      );

      return {
        id: `edge-${idx}`,
        source: sourceEntity?.id || rel.source,
        target: targetEntity?.id || rel.target,
        label: rel.type,
        animated: false,
        style: { stroke: '#888' },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: '#888',
        },
      };
    });

  return { nodes, edges };
}

const INITIAL_LIMIT = 50;
const LOAD_MORE_INCREMENT = 50;
const MAX_LIMIT = 500;

interface GraphContainerProps {
  focusEntityId?: string;
}

export function GraphContainer({ focusEntityId }: GraphContainerProps) {
  const { overview, isLoading: overviewLoading } = useGraphOverview();
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<string | null>(null);
  const [limit, setLimit] = useState(INITIAL_LIMIT);

  // For direct entity focus
  const [focusedEntity, setFocusedEntity] = useState<EntityDetail | null>(null);
  const [focusLoading, setFocusLoading] = useState(false);

  // Debounce search to prevent reloading on every keystroke
  const debouncedSearch = useDebounce(searchQuery, 500);

  const { entities, relationships, isLoading, error } = useGraphData({
    limit,
    search: debouncedSearch || undefined,
    type: typeFilter || undefined,
  });

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
    setLimit(prev => Math.min(prev + LOAD_MORE_INCREMENT, MAX_LIMIT));
  }, []);

  const canLoadMore = entities.length >= limit && limit < MAX_LIMIT;

  const { selectNode, selectedNodeId } = useGraphStore();

  // Auto-select focused entity
  useEffect(() => {
    if (focusedEntity) {
      selectNode(focusedEntity.id);
    }
  }, [focusedEntity, selectNode]);

  const { nodes: initialNodes, edges: initialEdges } = useMemo(
    () => calculateLayout(entities, relationships),
    [entities, relationships]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Update nodes and edges when data changes
  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      selectNode(node.id);
    },
    [selectNode]
  );

  const onPaneClick = useCallback(() => {
    selectNode(null);
  }, [selectNode]);

  // Just update local state - the debounced value will trigger the data fetch
  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query);
  }, []);

  const handleTypeFilter = useCallback((type: string | null) => {
    setTypeFilter(type);
  }, []);

  // Show a subtle loading indicator when searching (but don't block the whole UI)
  const isSearching = searchQuery !== debouncedSearch;

  if (isLoading || overviewLoading || focusLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

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
    <div className="h-full relative">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        nodeTypes={nodeTypes}
        fitView
        minZoom={0.1}
        maxZoom={2}
        defaultEdgeOptions={{
          style: { strokeWidth: 1.5 },
        }}
      >
        <Background color="#444" gap={16} />
        <MiniMap
          nodeColor={(node) => {
            const type = (node.data as { type?: string })?.type?.toLowerCase();
            const colors: Record<string, string> = {
              person: '#3b82f6',
              organization: '#22c55e',
              location: '#f97316',
              date: '#a855f7',
              document: '#6b7280',
              topic: '#ec4899',
              event: '#ef4444',
              product: '#eab308',
              financial_item: '#10b981',
            };
            return colors[type || ''] || '#64748b';
          }}
          className="!bg-background/80"
        />
      </ReactFlow>

      <GraphControls
        overview={overview}
        onSearch={handleSearch}
        onTypeFilter={handleTypeFilter}
        isSearching={isSearching}
        entityCount={entities.length}
        onLoadMore={handleLoadMore}
        canLoadMore={canLoadMore}
      />
      <GraphLegend />
      <GraphSidebar entities={entities} relationships={relationships} focusedEntity={focusedEntity || undefined} />
    </div>
  );
}
