// API Response Types

export type QueryMethod = 'local' | 'global' | 'drift' | 'basic';
export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed';

// Health Response
export interface HealthResponse {
  status: 'healthy' | 'degraded';
  paperless_connected: boolean;
  graphrag_initialized: boolean;
  last_sync: string | null;
  document_count: number;
}

// Query Types
export interface ConversationMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface QueryRequest {
  query: string;
  method: QueryMethod;
  community_level?: number;
  conversation_history?: ConversationMessage[];
}

export interface SourceDocumentRef {
  paperless_id: number;
  title: string;
  view_url: string;
}

export interface QueryResponse {
  query: string;
  method: string;
  response: string;
  source_documents?: SourceDocumentRef[];
}

// Sync Types
export interface SyncRequest {
  full: boolean;
}

export interface SyncResponse {
  task_id: string;
  status: string;
  message: string;
}

export interface SyncResult {
  added: number;
  updated: number;
  deleted: number;
  recovered: number;
  unchanged: number;
  errors: number;
  status?: string;
  operation?: string;
  output?: string;
}

// Task Types
export interface Task {
  task_id: string;
  status: TaskStatus;
  task_type: string;
  result: Record<string, unknown> | null;
  error: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
  // Progress tracking
  progress_percent: number | null;
  progress_message: string | null;
  progress_detail: string | null;
}

// Stats Response
export interface StatsResponse {
  total_documents: number;
  index_version: number;
  last_full_sync: string | null;
  last_incremental_sync: string | null;
}

// Graph Types (for new endpoints)
export interface Entity {
  id: string;
  name: string;
  type: string;
  description: string;
  community_id?: string;
  degree?: number; // Number of connections (relationships) for this entity
}

// Force graph node type (for visualization)
export interface GraphNode {
  id: string;
  name: string;
  type: string;
  description: string;
  community_id?: string;
  degree: number;
  val: number; // Node size value
  color: string; // Node color
}

// Force graph link type (for visualization)
export interface GraphLink {
  source: string;
  target: string;
  type: string;
  description?: string;
  weight?: number;
}

export interface EntityDetail extends Entity {
  relationships: Relationship[];
}

export interface Relationship {
  id: string;
  source: string;
  target: string;
  type: string;
  description: string;
  weight?: number;
}

export interface Community {
  id: string;
  level: number;
  title: string;
  summary: string;
  entity_count: number;
}

export interface GraphOverview {
  entity_count: number;
  relationship_count: number;
  community_count: number;
  entity_types: { type: string; count: number }[];
  relationship_types: { type: string; count: number }[];
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  has_more: boolean;
}

// Settings Types
export interface SettingValue {
  value: string | number | null;
  has_value: boolean;
  label: string;
  type: 'string' | 'integer' | 'float';
  sensitive: boolean;
  required: boolean;
  default: string | number | null;
  min?: number;
  max?: number;
  description?: string;
}

export interface SettingsResponse {
  settings: Record<string, SettingValue>;
  is_configured: boolean;
  missing_required: string[];
}

export interface SettingsUpdateRequest {
  settings: Record<string, string | number | null>;
}

export interface SettingsUpdateResponse {
  success: boolean;
  updated: string[];
  errors: Record<string, string>;
}

export interface ConfigStatusResponse {
  is_configured: boolean;
  missing_required: string[];
  message: string;
}

export interface ConnectionTestResult {
  paperless: { success: boolean; message: string };
  litellm: { success: boolean; message: string };
}
