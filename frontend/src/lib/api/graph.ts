import { apiClient } from './client';
import type {
  GraphOverview,
  Entity,
  EntityDetail,
  Relationship,
  Community,
  PaginatedResponse
} from '@/types';

export async function getGraphOverview(): Promise<GraphOverview> {
  return apiClient.get<GraphOverview>('/graph/overview');
}

export interface GetEntitiesParams {
  limit?: number;
  offset?: number;
  type?: string;
  search?: string;
  community_id?: string;
  community_level?: number;
}

export async function getEntities(params?: GetEntitiesParams): Promise<PaginatedResponse<Entity>> {
  const searchParams = new URLSearchParams();
  if (params?.limit) searchParams.set('limit', String(params.limit));
  if (params?.offset) searchParams.set('offset', String(params.offset));
  if (params?.type) searchParams.set('type', params.type);
  if (params?.search) searchParams.set('search', params.search);
  if (params?.community_id) searchParams.set('community_id', params.community_id);
  if (params?.community_level !== undefined) searchParams.set('community_level', String(params.community_level));

  const query = searchParams.toString();
  return apiClient.get<PaginatedResponse<Entity>>(`/graph/entities${query ? `?${query}` : ''}`);
}

export async function getEntity(entityId: string): Promise<EntityDetail> {
  return apiClient.get<EntityDetail>(`/graph/entities/${encodeURIComponent(entityId)}`);
}

export interface GetRelationshipsParams {
  limit?: number;
  offset?: number;
  source_id?: string;
  target_id?: string;
  type?: string;
}

export async function getRelationships(params?: GetRelationshipsParams): Promise<PaginatedResponse<Relationship>> {
  const searchParams = new URLSearchParams();
  if (params?.limit) searchParams.set('limit', String(params.limit));
  if (params?.offset) searchParams.set('offset', String(params.offset));
  if (params?.source_id) searchParams.set('source_id', params.source_id);
  if (params?.target_id) searchParams.set('target_id', params.target_id);
  if (params?.type) searchParams.set('type', params.type);

  const query = searchParams.toString();
  return apiClient.get<PaginatedResponse<Relationship>>(`/graph/relationships${query ? `?${query}` : ''}`);
}

export async function getCommunities(level?: number): Promise<PaginatedResponse<Community>> {
  const query = level !== undefined ? `?level=${level}` : '';
  return apiClient.get<PaginatedResponse<Community>>(`/graph/communities${query}`);
}

export async function getCommunity(communityId: string): Promise<Community & { entities: Entity[] }> {
  return apiClient.get<Community & { entities: Entity[] }>(`/graph/communities/${encodeURIComponent(communityId)}`);
}

export async function getRelationshipsForEntities(entityNames: string[], limit: number = 1000): Promise<PaginatedResponse<Relationship>> {
  return apiClient.post<PaginatedResponse<Relationship>>('/graph/relationships/for-entities', {
    entity_names: entityNames,
    limit,
  });
}

export interface SourceDocument {
  paperless_id: number;
  graphrag_doc_id: string;
  title: string;
  view_url: string;
}

export async function getEntitySourceDocuments(entityId: string): Promise<SourceDocument[]> {
  return apiClient.get<SourceDocument[]>(`/graph/entities/${encodeURIComponent(entityId)}/source-documents`);
}
