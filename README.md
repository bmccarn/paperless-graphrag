# Paperless-GraphRAG

A knowledge graph interface for [paperless-ngx](https://github.com/paperless-ngx/paperless-ngx) documents using Microsoft's [GraphRAG](https://github.com/microsoft/graphrag). This service syncs your paperless-ngx documents into a knowledge graph and provides an intelligent query interface that understands relationships between entities across your entire document collection.

## What is GraphRAG?

Traditional RAG (Retrieval-Augmented Generation) finds relevant document chunks based on semantic similarity. GraphRAG goes further by:

1. **Extracting entities** (people, organizations, accounts, policies, etc.) from your documents
2. **Building relationships** between entities across all documents
3. **Creating community summaries** that capture themes and patterns
4. **Enabling two query modes**:
   - **Local Search**: Find specific information about entities (e.g., "What's my policy number with State Farm?")
   - **Global Search**: Understand themes across your collection (e.g., "What types of insurance do I have?")

## Features

- **Automatic Document Sync**: Incremental sync from paperless-ngx with change detection
- **Knowledge Graph**: Extracts entities and relationships using LLM-powered analysis
- **Smart Queries**: Natural language queries with local (entity-focused) or global (theme-based) search
- **Graph Visualization**: Interactive visualization of entities and their relationships
- **Web Dashboard**: React-based UI for querying, browsing entities, and managing sync
- **Streaming Responses**: Real-time streaming of query responses

## Screenshots

The web interface provides:

- **Chat Interface**: Natural language queries with streaming responses
- **Graph Explorer**: Visual exploration of entities and relationships
- **Operations Panel**: Sync management and task monitoring
- **Settings**: Live configuration of models, API endpoints, and GraphRAG parameters (no restart required)

## Architecture

```
┌─────────────────┐     ┌─────────────────────────────────────┐     ┌─────────────┐
│  paperless-ngx  │────▶│         paperless-graphrag          │────▶│   LiteLLM   │
│                 │     │  ┌─────────┐  ┌─────────────────┐   │     │   (proxy)   │
│   Documents     │     │  │ FastAPI │  │  GraphRAG Index │   │     └──────┬──────┘
│   Metadata      │     │  │ Backend │  │  - Entities     │   │            │
│   Tags          │     │  └─────────┘  │  - Relations    │   │            ▼
└─────────────────┘     │       │       │  - Communities  │   │     ┌─────────────┐
                        │       ▼       └─────────────────┘   │     │ OpenAI/     │
                        │  ┌─────────┐                        │     │ Anthropic/  │
                        │  │  nginx  │◀── Static frontend     │     │ Local LLM   │
                        │  └─────────┘                        │     └─────────────┘
                        └─────────────────────────────────────┘
```

## Prerequisites

- **Docker** and **Docker Compose** (v2+)
- **paperless-ngx** instance with API access
- **LiteLLM** proxy (recommended) or direct OpenAI API access
- Sufficient resources for indexing:
  - ~4GB RAM for indexing (scales with document count)
  - ~1GB disk per 1000 documents for the index

## Quick Start

### 1. Clone and Configure

```bash
git clone https://github.com/yourusername/paperless-graphrag.git
cd paperless-graphrag

# Copy environment template
cp .env.example .env
```

### 2. Configure Environment Variables

Edit `.env` with your settings:

```bash
# Required: Paperless-ngx connection
PAPERLESS_URL=http://your-paperless-host:8000
PAPERLESS_TOKEN=your_paperless_api_token  # Get from Settings > Administration > Auth Tokens

# Required: LiteLLM connection (or direct OpenAI)
LITELLM_BASE_URL=http://your-litellm-host:4000
LITELLM_API_KEY=your_api_key

# Optional: Model selection
INDEXING_MODEL=gpt-5-mini       # Model for entity extraction
QUERY_MODEL=gpt-5-mini          # Model for user queries
EMBEDDING_MODEL=text-embedding-3-small
```

### 3. Network Setup

The container needs to reach your paperless-ngx and LiteLLM services.

**Option A**: Join an existing Docker network
```yaml
# docker-compose.yml already configured for "paperless-network"
# Just ensure your services are on this network
```

**Option B**: Use host networking (simpler for testing)
```yaml
# In docker-compose.yml, replace networks with:
network_mode: host
```

**Option C**: Create a bridge network
```yaml
networks:
  paperless-network:
    driver: bridge  # Change from external: true
```

### 4. Build and Run

```bash
# Build and start
docker compose up -d --build

# Watch the logs
docker compose logs -f

# Verify health
curl http://localhost:8003/health
```

### 5. Initial Indexing

Open the web UI at http://localhost:8003 and click "Full Sync" in the Operations panel, or:

```bash
curl -X POST http://localhost:8003/sync \
  -H "Content-Type: application/json" \
  -d '{"full": true}'
```

**Note**: Initial indexing takes ~1-2 minutes per 10 documents depending on your LLM speed.

## Usage

### Web Interface

Access the dashboard at http://localhost:8003

**Chat Tab**
- Ask natural language questions about your documents
- Toggle between Local (specific) and Global (thematic) search modes
- View source references in responses

**Graph Tab**
- Explore entities and their relationships visually
- Click entities to see details and connected nodes
- Search for specific entities

**Operations Tab**
- Trigger incremental or full syncs
- Monitor running tasks
- View sync statistics

### Query Examples

**Local Search** (entity-focused):
- "What is my account number with Chase Bank?"
- "Show me all documents from State Farm"
- "What medical procedures did I have in 2023?"
- "Find invoices from Amazon over $100"

**Global Search** (theme-based):
- "What types of insurance coverage do I have?"
- "Summarize my financial accounts"
- "What are the main categories of documents I have?"
- "What recurring subscriptions am I paying for?"

### API Usage

```bash
# Health check
curl http://localhost:8003/health

# Trigger sync
curl -X POST http://localhost:8003/sync \
  -H "Content-Type: application/json" \
  -d '{"full": false}'  # incremental

# Query (local search)
curl -X POST http://localhost:8003/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What insurance policies do I have?",
    "method": "local"
  }'

# Query (global search)
curl -X POST http://localhost:8003/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main themes in my documents?",
    "method": "global"
  }'

# Get graph overview
curl http://localhost:8003/graph/overview

# List entities
curl "http://localhost:8003/graph/entities?limit=50&search=amazon"
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Service health and connectivity status |
| POST | `/sync` | Trigger document sync (`{"full": true/false}`) |
| GET | `/tasks` | List all tasks |
| GET | `/tasks/{id}` | Get task status and progress |
| POST | `/query` | Query the knowledge graph |
| POST | `/query/stream` | Query with streaming response |
| GET | `/documents/stats` | Sync statistics |
| GET | `/graph/overview` | Graph statistics (entities, relationships, communities) |
| GET | `/graph/entities` | List entities with optional search/pagination |
| GET | `/graph/entities/{id}` | Get entity details |
| GET | `/graph/relationships` | List relationships |
| GET | `/settings` | Get current configuration |
| PUT | `/settings` | Update configuration |

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PAPERLESS_URL` | Yes | - | Full URL to paperless-ngx |
| `PAPERLESS_TOKEN` | Yes | - | API token from paperless-ngx |
| `LITELLM_BASE_URL` | Yes | - | LiteLLM proxy URL |
| `LITELLM_API_KEY` | Yes | - | API key for LiteLLM |
| `INDEXING_MODEL` | No | `gpt-5-mini` | Model for entity extraction |
| `QUERY_MODEL` | No | `gpt-5-mini` | Model for query responses |
| `EMBEDDING_MODEL` | No | `text-embedding-3-small` | Model for embeddings |
| `CHUNK_SIZE` | No | `1200` | Text chunk size (tokens) |
| `CHUNK_OVERLAP` | No | `100` | Overlap between chunks |
| `REQUESTS_PER_MINUTE` | No | `60` | Rate limit for LLM calls |
| `TOKENS_PER_MINUTE` | No | `90000` | Token rate limit |
| `CONCURRENT_REQUESTS` | No | `25` | Max concurrent LLM requests |

### Entity Types

The system extracts these entity types optimized for personal document management:

| Entity Type | Examples |
|-------------|----------|
| `person` | Names of individuals |
| `organization` | Companies, agencies, institutions |
| `location` | Addresses, cities, countries |
| `tax_form` | W-2, 1099, Schedule C, etc. |
| `financial_transaction` | Payments, invoices, purchases |
| `account` | Bank accounts, policy numbers, member IDs |
| `insurance_policy` | Coverages, endorsements, claims |
| `medical_record` | Procedures, conditions, medications |
| `subscription` | Services, memberships |
| `legal_document` | Contracts, agreements |
| `vehicle` | Cars, boats (for insurance/DMV) |
| `certification` | Training, licenses, credentials |
| `government_form` | Non-tax government documents |

### Data Persistence

The `./data` directory is mounted as a volume:

```
data/
├── graphrag/
│   ├── input/          # Document text files (synced from paperless)
│   ├── output/         # GraphRAG index (parquet files)
│   ├── cache/          # LLM response cache (saves money on re-runs)
│   └── settings.yaml   # Generated GraphRAG config
└── sync_state.json     # Tracks synced documents
```

## Development

### Local Development (without Docker)

```bash
# Backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Copy and edit environment
cp .env.example .env
# Edit .env with your settings

# Run backend
uvicorn app.main:app --reload --port 8002

# Frontend (in another terminal)
cd frontend
cp .env.local.example .env.local
# Edit .env.local: NEXT_PUBLIC_API_URL=http://localhost:8002

npm install
npm run dev
```

### Project Structure

```
paperless-graphrag/
├── app/
│   ├── api/            # FastAPI routes
│   ├── clients/        # External service clients (paperless)
│   ├── models/         # Pydantic models
│   └── services/       # Business logic (sync, graphrag)
├── frontend/
│   └── src/
│       ├── app/        # Next.js pages
│       ├── components/ # React components
│       └── lib/        # Utilities and API client
├── docker/
│   ├── nginx.conf      # Frontend + API proxy
│   └── supervisord.conf
├── data/               # Persisted data (gitignored)
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Troubleshooting

### Common Issues

**"Connection refused" to paperless-ngx**
- Verify `PAPERLESS_URL` is reachable from inside the container
- Check Docker network configuration
- Try using the host IP instead of `localhost`

**API key or authentication errors**
- Verify `PAPERLESS_TOKEN` is correct (test with curl to paperless API)
- Check `LITELLM_API_KEY` is valid
- Ensure LiteLLM is configured with your model provider

**Sync stuck at 80% (Finalizing documents)**
- This is normal for large document sets - the LLM is extracting entities
- Check logs for actual progress: `docker compose logs -f`
- Indexing ~230 documents takes 20-40 minutes

**Out of memory during indexing**
- Increase Docker memory limit
- Reduce `CONCURRENT_REQUESTS` to lower parallel LLM calls
- Consider indexing in batches

**Frontend shows "Failed to fetch"**
- Backend might still be starting (check health endpoint)
- CORS issue - ensure accessing via correct port (8003)
- Check browser console for detailed error

### Logs

```bash
# All logs
docker compose logs -f

# Backend only
docker compose logs -f 2>&1 | grep -E "(uvicorn|app\.|ERROR)"

# Check nginx access
docker compose exec paperless-graphrag cat /var/log/nginx/access.log
```

### Reset and Rebuild

```bash
# Full reset (removes all indexed data)
docker compose down
rm -rf data/graphrag/output data/graphrag/cache data/sync_state.json
docker compose up -d --build

# Rebuild index only (keeps synced documents)
rm -rf data/graphrag/output data/graphrag/cache
curl -X POST http://localhost:8003/sync -d '{"full": true}'
```

## Performance Tips

1. **Model selection** - Use faster/cheaper models for indexing, better models for queries if needed
2. **Enable LLM caching** - GraphRAG caches responses; re-indexing is faster
3. **Incremental sync** - Only processes changed documents
4. **Adjust rate limits** - Match your API tier to avoid throttling
5. **Use the Settings page** - Adjust models and parameters without restarting the container

## License

MIT License - See [LICENSE](LICENSE) for details.

## Acknowledgments

- [Microsoft GraphRAG](https://github.com/microsoft/graphrag) - The core knowledge graph engine
- [paperless-ngx](https://github.com/paperless-ngx/paperless-ngx) - Document management system
- [LiteLLM](https://github.com/BerriAI/litellm) - LLM proxy for unified API access
