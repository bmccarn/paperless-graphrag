"""FastAPI routes for graph visualization API."""

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.dependencies import get_graph_reader_service
from app.services.graph_reader import GraphReaderService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/graph", tags=["graph"])


# Response Models
class EntityTypeCount(BaseModel):
    type: str
    count: int


class GraphOverviewResponse(BaseModel):
    entity_count: int
    relationship_count: int
    community_count: int
    entity_types: list[EntityTypeCount]
    relationship_types: list[EntityTypeCount]


class EntityResponse(BaseModel):
    id: str
    name: str
    type: str
    description: str
    community_id: Optional[str] = None


class RelationshipResponse(BaseModel):
    id: str
    source: str
    target: str
    type: str
    description: str
    weight: float


class EntityDetailResponse(EntityResponse):
    relationships: list[RelationshipResponse]


class CommunityResponse(BaseModel):
    id: str
    level: int
    title: str
    summary: str
    entity_count: int


class CommunityDetailResponse(CommunityResponse):
    entities: list[EntityResponse]


class PaginatedEntitiesResponse(BaseModel):
    items: list[EntityResponse]
    total: int
    has_more: bool


class PaginatedRelationshipsResponse(BaseModel):
    items: list[RelationshipResponse]
    total: int
    has_more: bool


class PaginatedCommunitiesResponse(BaseModel):
    items: list[CommunityResponse]
    total: int
    has_more: bool


# Routes
@router.get("/overview", response_model=GraphOverviewResponse)
async def get_graph_overview(
    graph_reader: GraphReaderService = Depends(get_graph_reader_service),
):
    """Get overview statistics of the knowledge graph."""
    try:
        return await asyncio.to_thread(graph_reader.get_overview)
    except Exception as e:
        logger.exception("Failed to get graph overview")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entities", response_model=PaginatedEntitiesResponse)
async def list_entities(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    type: Optional[str] = Query(default=None, description="Filter by entity type"),
    search: Optional[str] = Query(default=None, description="Search in name and description"),
    community_id: Optional[str] = Query(default=None, description="Filter by community"),
    graph_reader: GraphReaderService = Depends(get_graph_reader_service),
):
    """Get paginated list of entities from the graph."""
    try:
        return await asyncio.to_thread(
            graph_reader.get_entities,
            limit=limit,
            offset=offset,
            entity_type=type,
            search=search,
            community_id=community_id,
        )
    except Exception as e:
        logger.exception("Failed to get entities")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entities/{entity_id}", response_model=EntityDetailResponse)
async def get_entity(
    entity_id: str,
    graph_reader: GraphReaderService = Depends(get_graph_reader_service),
):
    """Get a single entity with its relationships."""
    try:
        entity = await asyncio.to_thread(graph_reader.get_entity, entity_id)
        if entity is None:
            raise HTTPException(status_code=404, detail="Entity not found")
        return entity
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get entity")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/relationships", response_model=PaginatedRelationshipsResponse)
async def list_relationships(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    source_id: Optional[str] = Query(default=None, description="Filter by source entity"),
    target_id: Optional[str] = Query(default=None, description="Filter by target entity"),
    type: Optional[str] = Query(default=None, description="Filter by relationship type"),
    graph_reader: GraphReaderService = Depends(get_graph_reader_service),
):
    """Get paginated list of relationships from the graph."""
    try:
        return await asyncio.to_thread(
            graph_reader.get_relationships,
            limit=limit,
            offset=offset,
            source_id=source_id,
            target_id=target_id,
            relationship_type=type,
        )
    except Exception as e:
        logger.exception("Failed to get relationships")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/communities", response_model=PaginatedCommunitiesResponse)
async def list_communities(
    level: Optional[int] = Query(default=None, ge=0, le=10, description="Filter by community level"),
    graph_reader: GraphReaderService = Depends(get_graph_reader_service),
):
    """Get list of communities from the graph."""
    try:
        return await asyncio.to_thread(graph_reader.get_communities, level)
    except Exception as e:
        logger.exception("Failed to get communities")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/communities/{community_id}", response_model=CommunityDetailResponse)
async def get_community(
    community_id: str,
    graph_reader: GraphReaderService = Depends(get_graph_reader_service),
):
    """Get a single community with its member entities."""
    try:
        community = await asyncio.to_thread(graph_reader.get_community, community_id)
        if community is None:
            raise HTTPException(status_code=404, detail="Community not found")
        return community
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get community")
        raise HTTPException(status_code=500, detail=str(e))
