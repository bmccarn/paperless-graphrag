'use client';

import { X, GripHorizontal } from 'lucide-react';
import { useState, useRef, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { useGraphStore } from '@/lib/stores';
import type { Entity, Relationship } from '@/types';

interface GraphSidebarProps {
  entities: Entity[];
  relationships: Relationship[];
  focusedEntity?: Entity & { relationships?: Relationship[] };
}

export function GraphSidebar({ entities, relationships, focusedEntity }: GraphSidebarProps) {
  const { selectedNodeId, selectNode } = useGraphStore();
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragRef = useRef<{ startX: number; startY: number; initialX: number; initialY: number } | null>(null);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    setIsDragging(true);
    dragRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      initialX: position.x,
      initialY: position.y,
    };
  }, [position]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isDragging || !dragRef.current) return;

    const deltaX = e.clientX - dragRef.current.startX;
    const deltaY = e.clientY - dragRef.current.startY;

    setPosition({
      x: dragRef.current.initialX + deltaX,
      y: dragRef.current.initialY + deltaY,
    });
  }, [isDragging]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
    dragRef.current = null;
  }, []);

  if (!selectedNodeId) {
    return null;
  }

  // Try to find entity in loaded entities, or use focusedEntity if available
  let selectedEntity = entities.find(
    (e) => e.id === selectedNodeId || e.name === selectedNodeId
  );

  // Fall back to focusedEntity if not found in loaded entities
  if (!selectedEntity && focusedEntity && (focusedEntity.id === selectedNodeId || focusedEntity.name === selectedNodeId)) {
    selectedEntity = focusedEntity;
  }

  if (!selectedEntity) {
    return null;
  }

  // Use relationships from focusedEntity if available, otherwise find from graph relationships
  const relatedRelationships = (focusedEntity && focusedEntity.id === selectedEntity.id && focusedEntity.relationships)
    ? focusedEntity.relationships
    : relationships.filter(
        (r) =>
          r.source === selectedEntity!.name ||
          r.target === selectedEntity!.name ||
          r.source === selectedEntity!.id ||
          r.target === selectedEntity!.id
      );

  // Get connected entity names
  const connectedEntities = new Set<string>();
  relatedRelationships.forEach((r) => {
    if (r.source !== selectedEntity.name && r.source !== selectedEntity.id) {
      connectedEntities.add(r.source);
    }
    if (r.target !== selectedEntity.name && r.target !== selectedEntity.id) {
      connectedEntities.add(r.target);
    }
  });

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/50"
        onClick={() => selectNode(null)}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
      />

      {/* Draggable Modal */}
      <div
        className="fixed z-50 w-[600px] max-w-[90vw] h-[70vh] bg-background border rounded-lg shadow-2xl flex flex-col overflow-hidden"
        style={{
          left: `calc(50% + ${position.x}px)`,
          top: `calc(50% + ${position.y}px)`,
          transform: 'translate(-50%, -50%)',
        }}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
      >
        {/* Draggable Header */}
        <div
          className="flex items-center justify-between p-4 border-b shrink-0 cursor-move bg-muted/50"
          onMouseDown={handleMouseDown}
        >
          <div className="flex items-center gap-3 min-w-0 flex-1">
            <GripHorizontal className="h-5 w-5 text-muted-foreground shrink-0" />
            <div className="min-w-0">
              <h3 className="font-semibold break-words text-lg">{selectedEntity.name}</h3>
              <Badge variant="secondary" className="mt-1">
                {selectedEntity.type}
              </Badge>
            </div>
          </div>
          <Button variant="ghost" size="icon" className="shrink-0" onClick={() => selectNode(null)}>
            <X className="h-5 w-5" />
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto overflow-x-hidden p-6">
          <div className="space-y-6">
            {selectedEntity.description && (
              <div>
                <h4 className="text-sm font-medium text-muted-foreground mb-2">
                  Description
                </h4>
                <p className="text-sm whitespace-pre-wrap leading-relaxed" style={{ wordBreak: 'break-word', overflowWrap: 'break-word' }}>
                  {selectedEntity.description}
                </p>
              </div>
            )}

            {selectedEntity.community_id && (
              <div>
                <h4 className="text-sm font-medium text-muted-foreground mb-1">
                  Community
                </h4>
                <Badge variant="outline">{selectedEntity.community_id}</Badge>
              </div>
            )}

            <Separator />

            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-2">
                Relationships ({relatedRelationships.length})
              </h4>
              {relatedRelationships.length === 0 ? (
                <p className="text-sm text-muted-foreground">No relationships found</p>
              ) : (
                <div className="space-y-3">
                  {relatedRelationships.map((rel, idx) => (
                    <div key={idx} className="text-sm p-3 bg-muted rounded overflow-hidden">
                      <div className="text-xs font-medium text-muted-foreground mb-2" style={{ wordBreak: 'break-word' }}>
                        {rel.source} → {rel.target}
                      </div>
                      {rel.type && rel.type.length < 50 && (
                        <div className="mb-2">
                          <Badge variant="outline" className="text-xs">{rel.type}</Badge>
                        </div>
                      )}
                      {rel.description && (
                        <p className="text-xs leading-relaxed" style={{ wordBreak: 'break-word', overflowWrap: 'break-word' }}>
                          {rel.description}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <Separator />

            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-2">
                Connected Entities ({connectedEntities.size})
              </h4>
              <div className="flex flex-wrap gap-1">
                {Array.from(connectedEntities)
                  .slice(0, 15)
                  .map((name) => (
                    <Badge
                      key={name}
                      variant="outline"
                      className="cursor-pointer hover:bg-muted"
                      onClick={() => selectNode(name)}
                    >
                      {name}
                    </Badge>
                  ))}
                {connectedEntities.size > 15 && (
                  <span className="text-xs text-muted-foreground">
                    +{connectedEntities.size - 15} more
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
