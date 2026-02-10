import { create } from 'zustand';

// Color-by options for node coloring
export type ColorByOption = 'type' | 'community';

// Size-by options for node sizing
export type SizeByOption = 'uniform' | 'degree';

interface GraphFilters {
  entityTypes: string[];
  communityLevel?: number;
  searchQuery: string;
}

interface GraphState {
  // Selection state
  selectedNodeId: string | null;
  hoveredNodeId: string | null;

  // View mode state
  is3DMode: boolean;
  colorBy: ColorByOption;
  sizeBy: SizeByOption;

  // Filters
  filters: GraphFilters;
  isLoading: boolean;

  // Node filtering
  hideIsolatedNodes: boolean;
  minDegree: number;

  // Actions
  selectNode: (id: string | null) => void;
  setHoveredNode: (id: string | null) => void;
  toggle3DMode: () => void;
  set3DMode: (is3D: boolean) => void;
  setColorBy: (colorBy: ColorByOption) => void;
  setSizeBy: (sizeBy: SizeByOption) => void;
  setFilters: (filters: Partial<GraphFilters>) => void;
  resetFilters: () => void;
  setLoading: (loading: boolean) => void;
  setHideIsolatedNodes: (hide: boolean) => void;
  setMinDegree: (degree: number) => void;
}

const defaultFilters: GraphFilters = {
  entityTypes: [],
  communityLevel: undefined,
  searchQuery: '',
};

export const useGraphStore = create<GraphState>((set) => ({
  // Initial state
  selectedNodeId: null,
  hoveredNodeId: null,
  is3DMode: true, // Default to 3D as per user preference
  colorBy: 'type',
  sizeBy: 'degree',
  filters: defaultFilters,
  isLoading: false,
  hideIsolatedNodes: true,
  minDegree: 0,

  // Actions
  selectNode: (id) => set({ selectedNodeId: id }),
  setHoveredNode: (id) => set({ hoveredNodeId: id }),
  toggle3DMode: () => set((state) => ({ is3DMode: !state.is3DMode })),
  set3DMode: (is3D) => set({ is3DMode: is3D }),
  setColorBy: (colorBy) => set({ colorBy }),
  setSizeBy: (sizeBy) => set({ sizeBy }),
  setFilters: (filters) =>
    set((state) => ({
      filters: { ...state.filters, ...filters },
    })),
  resetFilters: () => set({ filters: defaultFilters, hideIsolatedNodes: true, minDegree: 0 }),
  setLoading: (loading) => set({ isLoading: loading }),
  setHideIsolatedNodes: (hide) => set({ hideIsolatedNodes: hide }),
  setMinDegree: (degree) => set({ minDegree: degree }),
}));
