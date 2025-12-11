'use client';

import { Search, ZoomIn, ZoomOut, Maximize2, RotateCcw, Loader2, Plus } from 'lucide-react';
import { useReactFlow } from '@xyflow/react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useGraphStore } from '@/lib/stores';
import type { GraphOverview } from '@/types';

interface GraphControlsProps {
  overview: GraphOverview | null;
  onSearch: (query: string) => void;
  onTypeFilter: (type: string | null) => void;
  isSearching?: boolean;
  entityCount?: number;
  onLoadMore?: () => void;
  canLoadMore?: boolean;
}

export function GraphControls({
  overview,
  onSearch,
  onTypeFilter,
  isSearching,
  entityCount,
  onLoadMore,
  canLoadMore
}: GraphControlsProps) {
  const { zoomIn, zoomOut, fitView } = useReactFlow();
  const { filters, setFilters, resetFilters } = useGraphStore();

  return (
    <div className="absolute top-4 left-4 z-10 flex flex-col gap-2">
      {/* Search */}
      <div className="flex items-center gap-2 bg-background border rounded-lg p-2">
        {isSearching ? (
          <Loader2 className="h-4 w-4 text-muted-foreground animate-spin" />
        ) : (
          <Search className="h-4 w-4 text-muted-foreground" />
        )}
        <Input
          placeholder="Search entities..."
          className="h-8 w-48 border-0 focus-visible:ring-0"
          value={filters.searchQuery}
          onChange={(e) => {
            setFilters({ searchQuery: e.target.value });
            onSearch(e.target.value);
          }}
        />
      </div>

      {/* Entity count indicator with Load More */}
      {entityCount !== undefined && (
        <div className="flex items-center gap-2">
          <div className="bg-background/90 border rounded-lg px-3 py-1.5 text-xs text-muted-foreground">
            Showing {entityCount} entities
          </div>
          {canLoadMore && (
            <Button
              variant="outline"
              size="sm"
              className="h-7 px-2 text-xs"
              onClick={onLoadMore}
            >
              <Plus className="h-3 w-3 mr-1" />
              Load More
            </Button>
          )}
        </div>
      )}

      {/* Type Filter */}
      <div className="bg-background border rounded-lg p-2">
        <Select
          value={filters.entityTypes[0] || 'all'}
          onValueChange={(value) => {
            const type = value === 'all' ? null : value;
            setFilters({ entityTypes: type ? [type] : [] });
            onTypeFilter(type);
          }}
        >
          <SelectTrigger className="h-8 w-48">
            <SelectValue placeholder="Filter by type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            {overview?.entity_types
              .filter(({ type }) => type && type.trim() !== '')
              .map(({ type, count }) => (
                <SelectItem key={type} value={type}>
                  {type} ({count})
                </SelectItem>
              ))}
          </SelectContent>
        </Select>
      </div>

      {/* Zoom Controls */}
      <div className="flex gap-1 bg-background border rounded-lg p-1">
        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => zoomIn()}>
          <ZoomIn className="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => zoomOut()}>
          <ZoomOut className="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => fitView()}>
          <Maximize2 className="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={resetFilters}>
          <RotateCcw className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
