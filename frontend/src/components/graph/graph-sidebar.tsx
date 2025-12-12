'use client';

import { X, GripHorizontal, FileText, ExternalLink, Loader2 } from 'lucide-react';
import { useState, useRef, useCallback, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { useGraphStore } from '@/lib/stores';
import { getEntitySourceDocuments, type SourceDocument } from '@/lib/api/graph';
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
  const [sourceDocuments, setSourceDocuments] = useState<SourceDocument[]>([]);
  const [loadingSourceDocs, setLoadingSourceDocs] = useState(false);

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

  // Fetch source documents when entity is selected
  useEffect(() => {
    if (!selectedNodeId) {
      setSourceDocuments([]);
      return;
    }

    const fetchSourceDocs = async () => {
      setLoadingSourceDocs(true);
      try {
        const docs = await getEntitySourceDocuments(selectedNodeId);
        setSourceDocuments(docs);
      } catch (error) {
        console.error('Failed to fetch source documents:', error);
        setSourceDocuments([]);
      } finally {
        setLoadingSourceDocs(false);
      }
    };

    fetchSourceDocs();
  }, [selectedNodeId]);

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
        className="fixed inset-0 z-[55] bg-black/50"
        onClick={() => selectNode(null)}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
      />

      {/* Modal - Draggable on desktop, full-width bottom sheet on mobile */}
      <div
        className="fixed z-[60] bg-background border rounded-t-xl md:rounded-lg shadow-2xl flex flex-col overflow-hidden
          inset-x-0 bottom-0 max-h-[70vh] md:max-h-[70vh]
          md:inset-auto md:w-[600px] md:max-w-[90vw]"
        style={{
          // Only apply position on desktop
          ...(typeof window !== 'undefined' && window.innerWidth >= 768 ? {
            left: `calc(50% + ${position.x}px)`,
            top: `calc(50% + ${position.y}px)`,
            transform: 'translate(-50%, -50%)',
          } : {}),
          // Safe area for mobile notch/home indicator
          paddingBottom: 'env(safe-area-inset-bottom, 0px)',
        }}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
      >
        {/* Header - Draggable on desktop, swipe indicator on mobile */}
        <div
          className="flex items-center justify-between p-3 md:p-4 border-b shrink-0 md:cursor-move bg-muted/50"
          onMouseDown={handleMouseDown}
        >
          {/* Mobile swipe indicator */}
          <div className="absolute top-2 left-1/2 -translate-x-1/2 w-10 h-1 bg-muted-foreground/30 rounded-full md:hidden" />

          <div className="flex items-center gap-2 md:gap-3 min-w-0 flex-1 mt-2 md:mt-0">
            <GripHorizontal className="h-5 w-5 text-muted-foreground shrink-0 hidden md:block" />
            <div className="min-w-0">
              <h3 className="font-semibold break-words text-base md:text-lg">{selectedEntity.name}</h3>
              <Badge variant="secondary" className="mt-1 text-xs">
                {selectedEntity.type}
              </Badge>
            </div>
          </div>
          <Button variant="ghost" size="icon" className="shrink-0 h-9 w-9 md:h-10 md:w-10" onClick={() => selectNode(null)}>
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

            <Separator />

            {/* Source Documents Section */}
            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-2 flex items-center gap-2">
                <FileText className="h-4 w-4" />
                Source Documents
                {loadingSourceDocs ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <span>({sourceDocuments.length})</span>
                )}
              </h4>
              {loadingSourceDocs ? (
                <p className="text-sm text-muted-foreground">Loading...</p>
              ) : sourceDocuments.length === 0 ? (
                <p className="text-sm text-muted-foreground">No source documents found</p>
              ) : (
                <div className="space-y-2">
                  {sourceDocuments.map((doc) => (
                    <a
                      key={doc.paperless_id}
                      href={doc.view_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 p-2 rounded bg-muted hover:bg-muted/80 transition-colors group"
                    >
                      <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
                      <span className="text-sm flex-1 truncate" title={doc.title}>
                        {doc.title}
                      </span>
                      <ExternalLink className="h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                    </a>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
