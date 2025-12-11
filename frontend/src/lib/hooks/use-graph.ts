'use client';

import { useState, useEffect, useCallback } from 'react';
import { getGraphOverview, getEntities, getRelationships, GetEntitiesParams } from '@/lib/api';
import type { GraphOverview, Entity, Relationship } from '@/types';

export function useGraphOverview() {
  const [overview, setOverview] = useState<GraphOverview | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchOverview = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await getGraphOverview();
      setOverview(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch graph overview'));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOverview();
  }, [fetchOverview]);

  return { overview, isLoading, error, refetch: fetchOverview };
}

export function useGraphData(params?: GetEntitiesParams) {
  const [entities, setEntities] = useState<Entity[]>([]);
  const [relationships, setRelationships] = useState<Relationship[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  // Stringify params for stable dependency
  const paramsKey = JSON.stringify(params || {});

  const fetchData = useCallback(async () => {
    try {
      setIsLoading(true);

      const parsedParams = JSON.parse(paramsKey) as GetEntitiesParams;

      const [entitiesRes, relationshipsRes] = await Promise.all([
        getEntities({ ...parsedParams, limit: parsedParams?.limit || 200 }),
        getRelationships({ limit: 500 }),
      ]);

      setEntities(entitiesRes.items);
      setRelationships(relationshipsRes.items);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch graph data'));
    } finally {
      setIsLoading(false);
    }
  }, [paramsKey]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { entities, relationships, isLoading, error, refetch: fetchData };
}
