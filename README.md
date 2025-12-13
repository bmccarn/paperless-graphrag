# Paperless-GraphRAG

A knowledge graph interface for [paperless-ngx](https://github.com/paperless-ngx/paperless-ngx) documents using Microsoft's [GraphRAG](https://github.com/microsoft/graphrag). This service syncs your paperless-ngx documents into a knowledge graph and provides an intelligent query interface that understands relationships between entities across your entire document collection.

## What is GraphRAG?

Traditional RAG (Retrieval-Augmented Generation) finds relevant document chunks based on semantic similarity. GraphRAG goes further by:

1. **Extracting entities** (people, organizations, accounts, policies, etc.) from your documents
2. **Building relationships** between entities across all documents
3. **Creating community summaries** that capture themes and patterns
4. **Enabling multiple query modes**:
   - **Local Search**: Find specific information about entities (e.g., "What's my policy number with State Farm?")
   - **Global Search**: Understand themes across your collection (e.g., "What types of insurance do I have?")
   - **DRIFT Search**: Dynamic reasoning for complex multi-hop queries
   - **Basic Search**: Direct vector similarity search

## Features

### Core Functionality
- **Automatic Document Sync**: Incremental sync from paperless-ngx with change detection
- **Knowledge Graph**: Extracts entities and relationships using LLM-powered analysis
- **Smart Queries**: Natural language queries with multiple search strategies
- **Streaming Responses**: Real-time SSE streaming of query responses

### Web Interface
- **Chat Interface**: Conversational queries with session management and source citations
- **Graph Visualization**: Interactive 3D/2D force-directed graph exploration
- **Operations Dashboard**: Sync management and real-time task monitoring
- **Logs Viewer**: Real-time log streaming with filtering
- **Settings Page**: Live configuration without container restart

### Data Persistence
- **Chat History**: Optional PostgreSQL backend for cross-device chat persistence
- **Graph Data**: Parquet-based storage for entities, relationships, and communities
- **Sync State**: Tracks which documents have been indexed

## Screenshots

The web interface provides:

- **Chat Interface**: Natural language queries with streaming responses and source document links
- **Graph Explorer**: Visual exploration of entities and relationships in 3D or 2D
- **Operations Panel**: Sync management, task monitoring, and progress tracking
- **Logs Viewer**: Real-time application logs with severity filtering
- **Settings**: Live configuration of models, API endpoints, rate limits, and database connection

## Architecture

```
┌─────────────────┐     ┌─────────────────────────────────────────────┐     ┌─────────────┐
│  paperless-ngx  │────▶│              paperless-graphrag             │────▶│   LiteLLM   │
│                 │     │  ┌─────────┐  ┌─────────────────┐           │     │   (proxy)   │
│   Documents     │     │  │ FastAPI │  │  GraphRAG Index │           │     └──────┬──────┘
│   Metadata      │     │  │ Backend │  │  - Entities     │           │            │
│   Tags          │     │  └────┬────┘  │  - Relations    │           │            ▼
└─────────────────┘     │       │       │  - Communities  │           │     ┌─────────────┐
                        │       │       └─────────────────┘           │     │ OpenAI/     │
                        │       ▼                                     │     │ Anthropic/  │
┌─────────────────┐     │  ┌─────────┐                                │     │ Local LLM   │
│   PostgreSQL    │◀───▶│  │  nginx  │◀── Next.js Frontend            │     └─────────────┘
│   (optional)    │     │  └─────────┘                                │
│  Chat History   │     └─────────────────────────────────────────────┘
└─────────────────┘
```

### Components
- **FastAPI Backend**: REST API with async support, SSE streaming, and background task management
- **Next.js Frontend**: React-based UI with Zustand state management and TailwindCSS
- **nginx**: Reverse proxy serving frontend static files and proxying API requests
- **supervisord**: Process manager running uvicorn and nginx
- **PostgreSQL** (optional): Persistent storage for chat history

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

# Optional: Model selection (can also be set via UI)
INDEXING_MODEL=gpt-5-mini       # Model for entity extraction
QUERY_MODEL=gpt-5-mini          # Model for user queries
EMBEDDING_MODEL=text-embedding-3-small
```

### 3. Network Setup

The container needs to reach your paperless-ngx and LiteLLM services.

**Option A**: Join an existing Docker network (recommended if services share a network)
```bash
# In .env:
DOCKER_NETWORK=your-existing-network-name
DOCKER_NETWORK_EXTERNAL=true
```

**Option B**: Create a new isolated network (default)
```bash
# No changes needed - uses default paperless-graphrag-net
```

**Option C**: Use host networking (simplest for testing)
```yaml
# In docker-compose.yml, add to paperless-graphrag service:
network_mode: host
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

#### Chat Tab
- Ask natural language questions about your documents
- Choose search method: Local, Global, DRIFT, or Basic
- View source document references with direct links to paperless-ngx
- Manage multiple chat sessions
- Chat history persists locally (or in PostgreSQL if configured)

#### Graph Tab
- **3D/2D Toggle**: Switch between immersive 3D view and simpler 2D layout
- **Search**: Find entities by name or type
- **Filtering**: Filter by entity type or community
- **Node Details**: Click any node to see full details in sidebar
- **Relationships**: Explore connections between entities
- **Community View**: See how entities cluster into communities

#### Operations Tab
- **Incremental Sync**: Process only new/modified documents
- **Full Sync**: Reprocess all documents from scratch
- **Task Monitoring**: Track progress of running tasks
- **Statistics**: View document counts and sync status

#### Logs Tab
- **Real-time Streaming**: Live application logs via SSE
- **Severity Filtering**: Filter by log level (INFO, WARNING, ERROR)
- **Search**: Search through log messages
- **Auto-scroll**: Automatically follow new log entries

#### Settings Tab
- **Model Configuration**: Select indexing, query, and embedding models
- **Rate Limiting**: Configure requests/tokens per minute and concurrency
- **Chunk Settings**: Adjust chunk size and overlap for document processing
- **Connection Testing**: Test paperless-ngx and LiteLLM connectivity
- **Database Settings**: Configure PostgreSQL for chat persistence

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

**DRIFT Search** (complex reasoning):
- "How are my insurance policies connected to my property?"
- "What's the relationship between my bank accounts and tax documents?"
- "Trace all documents related to my home purchase"

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PAPERLESS_URL` | Yes | - | Full URL to paperless-ngx instance |
| `PAPERLESS_TOKEN` | Yes | - | API token from paperless-ngx |
| `LITELLM_BASE_URL` | Yes | - | LiteLLM proxy URL |
| `LITELLM_API_KEY` | Yes | - | API key for LiteLLM |
| `INDEXING_MODEL` | No | `gpt-5-mini` | Model for entity extraction |
| `QUERY_MODEL` | No | `gpt-5.1` | Model for query responses |
| `EMBEDDING_MODEL` | No | `text-embedding-3-small` | Model for embeddings |
| `CHUNK_SIZE` | No | `1200` | Text chunk size (100-4000 tokens) |
| `CHUNK_OVERLAP` | No | `100` | Overlap between chunks (0-500) |
| `REQUESTS_PER_MINUTE` | No | `60` | Rate limit for LLM API calls |
| `TOKENS_PER_MINUTE` | No | `90000` | Token rate limit |
| `CONCURRENT_REQUESTS` | No | `25` | Max concurrent LLM requests |
| `DATABASE_URL` | No | - | PostgreSQL URL for chat persistence |
| `DOCKER_NETWORK` | No | `paperless-graphrag-net` | Docker network name |
| `DOCKER_NETWORK_EXTERNAL` | No | `false` | Whether network is external |

### Runtime Settings

Many settings can be changed via the Settings page without restarting the container. These are stored in `data/runtime_settings.json`:

- Model selection (indexing, query, embedding)
- Rate limiting (requests/minute, tokens/minute, concurrent requests)
- Chunk configuration (size, overlap)
- Database URL (for chat persistence)

Settings changed via the UI take precedence over environment variables.

### Database Configuration (Optional)

For persistent chat history across browsers/devices, configure PostgreSQL:

```bash
# In .env
DATABASE_URL=postgresql://user:password@host:5432/database
```

The application will:
1. Automatically create required tables on startup
2. Store chat sessions and messages in PostgreSQL
3. Fall back to browser localStorage if database is unavailable

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

## Complete API Reference

### Health & Status

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Service health and connectivity status |
| GET | `/api/tasks` | List all background tasks |
| GET | `/api/tasks/{task_id}` | Get specific task status and progress |

### Query Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/query` | Query the knowledge graph (returns complete response) |
| POST | `/query/stream` | Query with SSE streaming response |

**Query Request Body:**
```json
{
  "query": "What insurance policies do I have?",
  "method": "local",  // "local", "global", "drift", or "basic"
  "conversation_history": []  // Optional: previous messages for context
}
```

**Query Methods:**
- `local`: Entity-focused search for specific facts
- `global`: Theme-based search using community summaries
- `drift`: Dynamic reasoning for complex multi-hop queries
- `basic`: Direct vector similarity search

### Sync Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/sync` | Trigger document sync |
| GET | `/documents/stats` | Get sync statistics |

**Sync Request Body:**
```json
{
  "full": false  // true for full resync, false for incremental
}
```

### Graph Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/graph/overview` | Graph statistics (entity/relationship/community counts) |
| GET | `/graph/entities` | List entities with pagination and filtering |
| GET | `/graph/entity/{entity_id}` | Get single entity with relationships |
| GET | `/graph/relationships` | List relationships with pagination |
| GET | `/graph/search` | Search entities by name or type |
| GET | `/graph/communities` | List community summaries |
| GET | `/graph/for-visualization` | Get graph data formatted for force-graph rendering |

**Entity List Parameters:**
- `limit`: Number of results (default: 50)
- `offset`: Pagination offset
- `search`: Filter by name
- `entity_type`: Filter by type
- `sort_by_degree`: Sort by connection count (default: true)

### Chat Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/chat/status` | Check database connection status |
| GET | `/api/chat/sessions` | List all chat sessions |
| POST | `/api/chat/sessions` | Create new chat session |
| GET | `/api/chat/sessions/{id}` | Get session with messages |
| PUT | `/api/chat/sessions/{id}` | Update session (rename) |
| DELETE | `/api/chat/sessions/{id}` | Delete session and messages |
| POST | `/api/chat/sessions/{id}/messages` | Add message to session |

### Settings Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/settings` | Get all current settings |
| PUT | `/settings` | Update settings |
| POST | `/settings/test-paperless` | Test paperless-ngx connection |
| POST | `/settings/test-litellm` | Test LiteLLM connection |
| GET | `/settings/models` | Get available models from LiteLLM |
| GET | `/settings/current-models` | Get currently configured models |

### Logs Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/logs` | Get recent log entries |
| GET | `/api/logs/stream` | SSE stream of real-time logs |

**Logs Parameters:**
- `limit`: Number of log entries (default: 100)
- `level`: Minimum log level filter

## Data Persistence

The `./data` directory is mounted as a volume:

```
data/
├── graphrag/
│   ├── input/              # Document text files (synced from paperless)
│   ├── output/             # GraphRAG index
│   │   └── <timestamp>/
│   │       └── artifacts/
│   │           ├── create_final_entities.parquet
│   │           ├── create_final_relationships.parquet
│   │           ├── create_final_communities.parquet
│   │           ├── create_final_community_reports.parquet
│   │           └── ...
│   ├── cache/              # LLM response cache (saves money on re-runs)
│   └── settings.yaml       # Generated GraphRAG config
├── sync_state.json         # Tracks synced documents
└── runtime_settings.json   # UI-managed settings (gitignored)
```

## Development

### Local Development (without Docker)

**Backend:**
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and edit environment
cp .env.example .env
# Edit .env with your settings

# Run backend (port 8002)
uvicorn app.main:app --reload --port 8002
```

**Frontend:**
```bash
cd frontend

# Install dependencies
npm install

# Create local environment
echo "NEXT_PUBLIC_API_URL=http://localhost:8002" > .env.local

# Run development server (port 3000)
npm run dev
```

### Project Structure

```
paperless-graphrag/
├── app/                        # Backend (FastAPI)
│   ├── api/                    # API route handlers
│   │   ├── routes.py           # Main routes (health, sync, query)
│   │   ├── graph_routes.py     # Graph exploration endpoints
│   │   ├── chat_routes.py      # Chat persistence endpoints
│   │   └── logs_routes.py      # Log streaming endpoints
│   ├── clients/                # External service clients
│   │   └── paperless.py        # Paperless-ngx API client
│   ├── db/                     # Database layer
│   │   ├── connection.py       # Async PostgreSQL connection
│   │   └── models.py           # SQLAlchemy ORM models
│   ├── models/                 # Pydantic models
│   │   └── schemas.py          # Request/response schemas
│   ├── services/               # Business logic
│   │   ├── graphrag.py         # GraphRAG indexing and querying
│   │   ├── graph_reader.py     # Parquet file reading
│   │   ├── sync.py             # Document synchronization
│   │   ├── chat_history.py     # Chat persistence service
│   │   └── settings_persistence.py  # Runtime settings management
│   ├── config.py               # Configuration management
│   └── main.py                 # FastAPI application entry
├── frontend/                   # Frontend (Next.js)
│   └── src/
│       ├── app/                # Next.js pages (App Router)
│       │   ├── page.tsx        # Home/landing page
│       │   ├── chat/           # Chat interface
│       │   ├── graph/          # Graph visualization
│       │   ├── logs/           # Log viewer
│       │   ├── operations/     # Sync management
│       │   └── settings/       # Configuration UI
│       ├── components/         # React components
│       │   ├── chat/           # Chat-specific components
│       │   ├── graph/          # Graph visualization components
│       │   ├── layout/         # Header, navigation
│       │   └── ui/             # Reusable UI components
│       ├── lib/                # Utilities
│       │   ├── api/            # API client functions
│       │   ├── hooks/          # Custom React hooks
│       │   └── stores/         # Zustand state stores
│       └── types/              # TypeScript definitions
├── docker/
│   ├── nginx.conf              # nginx reverse proxy config
│   └── supervisord.conf        # Process manager config
├── data/                       # Persisted data (gitignored)
├── Dockerfile                  # Multi-stage Docker build
├── docker-compose.yml          # Container orchestration
├── requirements.txt            # Python dependencies
└── .env.example                # Environment template
```

### Key Technologies

**Backend:**
- FastAPI (async REST API)
- SQLAlchemy 2.0 (async ORM)
- asyncpg (PostgreSQL driver)
- Microsoft GraphRAG (knowledge graph engine)
- SSE-Starlette (server-sent events)

**Frontend:**
- Next.js 14 (React framework, App Router)
- TypeScript
- Zustand (state management)
- TailwindCSS (styling)
- react-force-graph (3D/2D graph visualization)
- Radix UI (accessible components)

## Troubleshooting

### Common Issues

**"Connection refused" to paperless-ngx**
- Verify `PAPERLESS_URL` is reachable from inside the container
- If using Docker, ensure both containers are on the same network
- Try using the host IP instead of `localhost` or container name

**API key or authentication errors**
- Verify `PAPERLESS_TOKEN` is correct (test with curl to paperless API)
- Check `LITELLM_API_KEY` is valid
- Ensure LiteLLM is configured with your model provider

**Sync stuck at high percentage**
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

**Database connection errors**
- Verify PostgreSQL is accessible from the container
- Check `DATABASE_URL` format: `postgresql://user:password@host:5432/database`
- URL-encode special characters in password (e.g., `@` becomes `%40`)

**Graph visualization not loading**
- Ensure sync has completed and entities exist
- Check `/graph/overview` endpoint for entity counts
- Large graphs may take time to render - try 2D mode first

### Logs

```bash
# All logs
docker compose logs -f

# Backend only
docker compose logs -f 2>&1 | grep -E "(uvicorn|app\.|ERROR)"

# Check nginx access
docker compose exec paperless-graphrag cat /var/log/nginx/access.log

# Use the Logs page in the UI for filtered, searchable logs
```

### Reset and Rebuild

```bash
# Full reset (removes all indexed data)
docker compose down
rm -rf data/graphrag/output data/graphrag/cache data/sync_state.json
docker compose up -d --build

# Rebuild index only (keeps synced documents)
rm -rf data/graphrag/output data/graphrag/cache
curl -X POST http://localhost:8003/sync -H "Content-Type: application/json" -d '{"full": true}'

# Reset chat history (if using database)
# Connect to PostgreSQL and: DROP TABLE chat_messages; DROP TABLE chat_sessions;

# Clear runtime settings (revert to env vars)
rm data/runtime_settings.json
docker compose restart
```

## Performance Tips

1. **Model selection**: Use faster/cheaper models for indexing (high volume), better models for queries if needed
2. **Enable LLM caching**: GraphRAG caches responses; re-indexing is faster and cheaper
3. **Incremental sync**: Only processes changed documents - use this for regular updates
4. **Adjust rate limits**: Match your API tier to avoid throttling
5. **Use the Settings page**: Adjust models and parameters without restarting the container
6. **Graph performance**: Use 2D mode for large graphs; 3D can be slow with 1000+ nodes
7. **Database**: PostgreSQL chat persistence adds negligible overhead but enables cross-device access

## API Usage Examples

### Query with curl

```bash
# Local search (specific facts)
curl -X POST http://localhost:8003/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What insurance policies do I have?",
    "method": "local"
  }'

# Global search (themes)
curl -X POST http://localhost:8003/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main themes in my documents?",
    "method": "global"
  }'

# Streaming query
curl -N http://localhost:8003/query/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Summarize my financial accounts",
    "method": "global"
  }'
```

### Graph exploration

```bash
# Get graph statistics
curl http://localhost:8003/graph/overview

# List entities (paginated)
curl "http://localhost:8003/graph/entities?limit=50&offset=0&sort_by_degree=true"

# Search entities
curl "http://localhost:8003/graph/entities?search=amazon"

# Filter by type
curl "http://localhost:8003/graph/entities?entity_type=organization"

# Get entity details
curl http://localhost:8003/graph/entity/abc123

# Get visualization data
curl http://localhost:8003/graph/for-visualization
```

### Chat sessions (requires database)

```bash
# Check database status
curl http://localhost:8003/api/chat/status

# List sessions
curl http://localhost:8003/api/chat/sessions

# Create session
curl -X POST http://localhost:8003/api/chat/sessions \
  -H "Content-Type: application/json" \
  -d '{"name": "Insurance Questions"}'

# Add message
curl -X POST http://localhost:8003/api/chat/sessions/{session_id}/messages \
  -H "Content-Type: application/json" \
  -d '{
    "role": "user",
    "content": "What policies do I have?",
    "method": "local"
  }'
```

## License

MIT License - See [LICENSE](LICENSE) for details.

## Acknowledgments

- [Microsoft GraphRAG](https://github.com/microsoft/graphrag) - The core knowledge graph engine
- [paperless-ngx](https://github.com/paperless-ngx/paperless-ngx) - Document management system
- [LiteLLM](https://github.com/BerriAI/litellm) - LLM proxy for unified API access
- [react-force-graph](https://github.com/vasturiano/react-force-graph) - 3D/2D graph visualization
- [Radix UI](https://www.radix-ui.com/) - Accessible component primitives
