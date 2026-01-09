import { create } from 'zustand';
import * as aiApi from '@/lib/api/ai';
import type {
  DocumentListItem,
  DocumentSuggestion,
  JobStatusResponse,
  Tag,
  DocumentType,
  ProcessingScope,
  DocumentFilters,
  ApprovalRequest,
} from '@/lib/api/ai';

interface AIState {
  // Document browser
  documents: DocumentListItem[];
  documentsLoading: boolean;
  documentsError: string | null;
  totalDocuments: number;
  currentPage: number;
  pageSize: number;
  totalPages: number;
  filters: DocumentFilters;

  // Selection
  selectedDocumentIds: Set<number>;

  // Taxonomy
  tags: Tag[];
  documentTypes: DocumentType[];
  taxonomyLoading: boolean;

  // Processing jobs
  activeJob: JobStatusResponse | null;
  jobs: JobStatusResponse[];
  jobPollingInterval: ReturnType<typeof setInterval> | null;

  // Suggestions
  pendingSuggestions: DocumentSuggestion[];
  suggestionsLoading: boolean;

  // Processing options
  processingOptions: {
    generateTitles: boolean;
    suggestTags: boolean;
    suggestDocumentType: boolean;
    autoApply: boolean;
  };

  // Stats
  stats: {
    pendingSuggestions: number;
    processedDocuments: number;
    activeJobs: number;
  } | null;

  // Actions - Documents
  fetchDocuments: (filters?: DocumentFilters) => Promise<void>;
  setPage: (page: number) => void;
  setFilters: (filters: Partial<DocumentFilters>) => void;
  clearFilters: () => void;

  // Actions - Selection
  selectDocument: (id: number) => void;
  deselectDocument: (id: number) => void;
  toggleDocument: (id: number) => void;
  selectAll: () => void;
  clearSelection: () => void;
  selectUnprocessed: () => void;

  // Actions - Taxonomy
  fetchTaxonomy: () => Promise<void>;
  createTag: (name: string, color?: string) => Promise<Tag>;
  createDocumentType: (name: string) => Promise<DocumentType>;

  // Actions - Processing
  startProcessing: (scope: ProcessingScope) => Promise<string>;
  setProcessingOptions: (options: Partial<AIState['processingOptions']>) => void;
  pollJobStatus: (jobId: string) => void;
  stopPolling: () => void;
  fetchJobs: () => Promise<void>;

  // Actions - Suggestions
  fetchPendingSuggestions: () => Promise<void>;
  approveSuggestion: (docId: number, request: ApprovalRequest) => Promise<void>;
  rejectSuggestion: (docId: number) => Promise<void>;
  applySuggestion: (docId: number) => Promise<void>;
  applyAllApproved: () => Promise<void>;
  bulkApprove: (documentIds: number[]) => Promise<void>;
  markForReprocess: (docId: number) => Promise<void>;
  resetSuggestion: (docId: number) => Promise<void>;

  // Actions - Stats
  fetchStats: () => Promise<void>;

  // Actions - Reset
  reset: () => void;
}

const initialState = {
  documents: [],
  documentsLoading: false,
  documentsError: null,
  totalDocuments: 0,
  currentPage: 1,
  pageSize: 20,
  totalPages: 0,
  filters: {},

  selectedDocumentIds: new Set<number>(),

  tags: [],
  documentTypes: [],
  taxonomyLoading: false,

  activeJob: null,
  jobs: [],
  jobPollingInterval: null,

  pendingSuggestions: [],
  suggestionsLoading: false,

  processingOptions: {
    generateTitles: true,
    suggestTags: true,
    suggestDocumentType: true,
    autoApply: false,
  },

  stats: null,
};

export const useAIStore = create<AIState>((set, get) => ({
  ...initialState,

  // =========================================================================
  // Document Actions
  // =========================================================================

  fetchDocuments: async (filters?: DocumentFilters) => {
    const state = get();
    const mergedFilters = {
      ...state.filters,
      ...filters,
      page: filters?.page ?? state.currentPage,
      page_size: state.pageSize,
    };

    set({ documentsLoading: true, documentsError: null });

    try {
      const response = await aiApi.getDocuments(mergedFilters);
      set({
        documents: response.documents,
        totalDocuments: response.total,
        currentPage: response.page,
        totalPages: response.total_pages,
        documentsLoading: false,
      });
    } catch (error) {
      set({
        documentsError: error instanceof Error ? error.message : 'Failed to fetch documents',
        documentsLoading: false,
      });
    }
  },

  setPage: (page: number) => {
    set({ currentPage: page });
    get().fetchDocuments({ page });
  },

  setFilters: (filters: Partial<DocumentFilters>) => {
    set((state) => ({
      filters: { ...state.filters, ...filters },
      currentPage: 1, // Reset to first page on filter change
    }));
    get().fetchDocuments({ ...filters, page: 1 });
  },

  clearFilters: () => {
    set({ filters: {}, currentPage: 1 });
    get().fetchDocuments({ page: 1 });
  },

  // =========================================================================
  // Selection Actions
  // =========================================================================

  selectDocument: (id: number) => {
    set((state) => {
      const newSet = new Set(state.selectedDocumentIds);
      newSet.add(id);
      return { selectedDocumentIds: newSet };
    });
  },

  deselectDocument: (id: number) => {
    set((state) => {
      const newSet = new Set(state.selectedDocumentIds);
      newSet.delete(id);
      return { selectedDocumentIds: newSet };
    });
  },

  toggleDocument: (id: number) => {
    const state = get();
    if (state.selectedDocumentIds.has(id)) {
      get().deselectDocument(id);
    } else {
      get().selectDocument(id);
    }
  },

  selectAll: () => {
    const state = get();
    const allIds = new Set(state.documents.map((d) => d.id));
    set({ selectedDocumentIds: allIds });
  },

  clearSelection: () => {
    set({ selectedDocumentIds: new Set() });
  },

  selectUnprocessed: () => {
    const state = get();
    const unprocessedIds = new Set(
      state.documents.filter((d) => !d.ai_processed_at).map((d) => d.id)
    );
    set({ selectedDocumentIds: unprocessedIds });
  },

  // =========================================================================
  // Taxonomy Actions
  // =========================================================================

  fetchTaxonomy: async () => {
    set({ taxonomyLoading: true });
    try {
      const [tags, documentTypes] = await Promise.all([
        aiApi.getTags(),
        aiApi.getDocumentTypes(),
      ]);
      set({ tags, documentTypes, taxonomyLoading: false });
    } catch (error) {
      console.error('Failed to fetch taxonomy:', error);
      set({ taxonomyLoading: false });
    }
  },

  createTag: async (name: string, color?: string) => {
    const tag = await aiApi.createTag(name, color);
    set((state) => ({ tags: [...state.tags, tag] }));
    return tag;
  },

  createDocumentType: async (name: string) => {
    const docType = await aiApi.createDocumentType(name);
    set((state) => ({ documentTypes: [...state.documentTypes, docType] }));
    return docType;
  },

  // =========================================================================
  // Processing Actions
  // =========================================================================

  startProcessing: async (scope: ProcessingScope) => {
    const state = get();

    const request = {
      scope,
      document_ids: scope === 'selected' ? Array.from(state.selectedDocumentIds) : [],
      generate_titles: state.processingOptions.generateTitles,
      suggest_tags: state.processingOptions.suggestTags,
      suggest_document_type: state.processingOptions.suggestDocumentType,
      auto_apply: state.processingOptions.autoApply,
    };

    const response = await aiApi.startProcessing(request);

    // Start polling for job status
    get().pollJobStatus(response.job_id);

    return response.job_id;
  },

  setProcessingOptions: (options) => {
    set((state) => ({
      processingOptions: { ...state.processingOptions, ...options },
    }));
  },

  pollJobStatus: (jobId: string) => {
    // Clear any existing polling
    get().stopPolling();

    const poll = async () => {
      try {
        const status = await aiApi.getJobStatus(jobId);
        set({ activeJob: status });

        // Stop polling if job is complete
        if (['completed', 'failed', 'cancelled'].includes(status.status)) {
          get().stopPolling();
          // Refresh data after job completes
          get().fetchDocuments();
          get().fetchPendingSuggestions();
          get().fetchStats();
        }
      } catch (error) {
        console.error('Failed to poll job status:', error);
        get().stopPolling();
      }
    };

    // Poll immediately, then every 2 seconds
    poll();
    const interval = setInterval(poll, 2000);
    set({ jobPollingInterval: interval });
  },

  stopPolling: () => {
    const state = get();
    if (state.jobPollingInterval) {
      clearInterval(state.jobPollingInterval);
      set({ jobPollingInterval: null });
    }
  },

  fetchJobs: async () => {
    try {
      const jobs = await aiApi.getJobs();
      set({ jobs });
    } catch (error) {
      console.error('Failed to fetch jobs:', error);
    }
  },

  // =========================================================================
  // Suggestions Actions
  // =========================================================================

  fetchPendingSuggestions: async () => {
    set({ suggestionsLoading: true });
    try {
      const suggestions = await aiApi.getPendingSuggestions();
      set({ pendingSuggestions: suggestions, suggestionsLoading: false });
    } catch (error) {
      console.error('Failed to fetch suggestions:', error);
      set({ suggestionsLoading: false });
    }
  },

  approveSuggestion: async (docId: number, request: ApprovalRequest) => {
    await aiApi.approveSuggestion(docId, request);
    // Refresh suggestions
    get().fetchPendingSuggestions();
  },

  rejectSuggestion: async (docId: number) => {
    await aiApi.rejectSuggestion(docId);
    // Refresh suggestions
    get().fetchPendingSuggestions();
  },

  applySuggestion: async (docId: number) => {
    await aiApi.applySuggestion(docId);
    // Refresh everything
    get().fetchDocuments();
    get().fetchPendingSuggestions();
    get().fetchStats();
  },

  applyAllApproved: async () => {
    await aiApi.applyAllApproved();
    // Refresh everything
    get().fetchDocuments();
    get().fetchPendingSuggestions();
    get().fetchStats();
  },

  bulkApprove: async (documentIds: number[]) => {
    await aiApi.bulkApprove(documentIds);
    get().fetchPendingSuggestions();
  },

  markForReprocess: async (docId: number) => {
    await aiApi.markForReprocess(docId);
    // Refresh documents and suggestions
    get().fetchDocuments();
    get().fetchPendingSuggestions();
    get().fetchStats();
  },

  resetSuggestion: async (docId: number) => {
    await aiApi.resetSuggestion(docId);
    // Refresh suggestions
    get().fetchPendingSuggestions();
  },

  // =========================================================================
  // Stats Actions
  // =========================================================================

  fetchStats: async () => {
    try {
      const stats = await aiApi.getAIStats();
      set({
        stats: {
          pendingSuggestions: stats.pending_suggestions,
          processedDocuments: stats.processed_documents,
          activeJobs: stats.active_jobs,
        },
      });
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  },

  // =========================================================================
  // Reset
  // =========================================================================

  reset: () => {
    get().stopPolling();
    set(initialState);
  },
}));
