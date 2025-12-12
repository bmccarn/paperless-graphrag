'use client';

import { useState, useEffect, useCallback } from 'react';
import { getGraphOverview, getEntities, getRelationshipsForEntities, GetEntitiesParams } from '@/lib/api';
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

      // First, fetch entities (sorted by degree - most connected first)
      const entitiesRes = await getEntities({ ...parsedParams, limit: parsedParams?.limit || 200 });
      setEntities(entitiesRes.items);

      // Then, fetch relationships that connect the loaded entities
      // This ensures all returned relationships will have matching nodes
      if (entitiesRes.items.length > 0) {
        const entityNames = entitiesRes.items.map((e) => e.name);
        const relationshipsRes = await getRelationshipsForEntities(entityNames, 2000);
        setRelationships(relationshipsRes.items);
      } else {
        setRelationships([]);
      }

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
