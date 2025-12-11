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
}

export async function getEntities(params?: GetEntitiesParams): Promise<PaginatedResponse<Entity>> {
  const searchParams = new URLSearchParams();
  if (params?.limit) searchParams.set('limit', String(params.limit));
  if (params?.offset) searchParams.set('offset', String(params.offset));
  if (params?.type) searchParams.set('type', params.type);
  if (params?.search) searchParams.set('search', params.search);
  if (params?.community_id) searchParams.set('community_id', params.community_id);

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
