# FastAPI Inventory Reservation Service

A highly concurrent and reliable inventory reservation service that supports both optimistic and pessimistic locking strategies for managing stock across multiple SKUs.

## Features

### Core Features (Implemented)
- ✅ REST endpoints for creating, converting, and releasing inventory holds
- ✅ Optimistic locking strategy (version-based)
- ✅ Pessimistic locking strategy (explicit locks)
- ✅ Idempotent operations using client tokens
- ✅ Batch holds across multiple SKUs with atomic transactions
- ✅ Automatic expiry of held reservations
- ✅ Availability snapshots
- ✅ Consistency check endpoint

## Tech Stack

- **FastAPI** - Modern async web framework
- **SQLAlchemy** - ORM with async support
- **PostgreSQL** - Database (with asyncpg driver)
- **Pydantic** - Data validation
- **pytest** - Testing framework

## Project Structure

```
OJT-INVENTORY-MANGEMENT/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── database.py           # Database connection and session
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── inventory.py     # Inventory API endpoints
│   │   └── skus.py          # SKU management endpoints
│   └── services/
│       ├── __init__.py
│       └── inventory_service.py  # Core business logic
├── tests/                   # Test files
├── requirements.txt         # Python dependencies
├── .env.example            # Environment variables template
├── DEVELOPMENT_LOG.md      # Development progress and decisions
└── README.md               # This file
```

## Setup

### Prerequisites

- Python 3.10+
- PostgreSQL 12+ (installed and running)
- pip

**⚠️ Important:** Before running the app, make sure to:
1. Create a `.env` file with your database configuration (see step 4 below)
2. Create the PostgreSQL database (see step 5 below)

### Installation

1. **Clone the repository** (if applicable)

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   
   Create a `.env` file in the project root:
   ```bash
   # Create .env file
   cat > .env << 'EOF'
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/inventory_db
   ENVIRONMENT=development
   LOG_LEVEL=INFO
   EOF
   ```
   
   **Important:** Edit `.env` and replace `postgres:postgres` with your actual PostgreSQL username and password.
   
   Or set the environment variable directly:
   ```bash
   export DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/inventory_db
   ```
   
   **Note:** The app will use a default database URL if `.env` is not found, but you should customize it for your setup.

5. **Create database:**
   
   **Option A: Using the script (easiest):**
   ```bash
   ./create_database.sh
   ```
   
   **Option B: Using createdb command:**
   ```bash
   createdb inventory_db
   ```
   
   **Option C: Using psql:**
   ```bash
   psql -U postgres -c "CREATE DATABASE inventory_db;"
   ```
   
   Or interactively:
   ```bash
   psql -U postgres
   CREATE DATABASE inventory_db;
   \q
   ```
   
   **Note:** Replace `postgres` with your PostgreSQL username if different.

6. **Run the application:**
   ```bash
   uvicorn app.main:app --reload
   ```

   The API will be available at `http://localhost:8000`
   API documentation at `http://localhost:8000/docs`

## API Endpoints

### SKU Management

- `POST /api/v1/skus` - Create a new SKU
- `GET /api/v1/skus/{sku_id}` - Get SKU details

### Inventory Operations

- `POST /api/v1/inventory/holds` - Create a hold reservation
- `POST /api/v1/inventory/allocations` - Create a direct allocation
- `POST /api/v1/inventory/holds/{reservation_id}/convert` - Convert hold to allocation
- `POST /api/v1/inventory/holds/{reservation_id}/release` - Release a hold
- `GET /api/v1/inventory/availability` - Get availability snapshot
- `GET /api/v1/inventory/consistency` - Check inventory consistency

## Usage Examples

### Create a SKU

```bash
curl -X POST "http://localhost:8000/api/v1/skus" \
  -H "Content-Type: application/json" \
  -d '{
    "sku_code": "PROD-001",
    "name": "Product 1",
    "description": "Test product",
    "initial_qty": 100
  }'
```

### Create a Hold

```bash
curl -X POST "http://localhost:8000/api/v1/inventory/holds" \
  -H "Content-Type: application/json" \
  -d '{
    "client_token": "unique-token-123",
    "items": [
      {"sku_id": "uuid-here", "qty": 5}
    ],
    "expires_in_seconds": 300,
    "strategy": "optimistic"
  }'
```

### Convert Hold to Allocation

```bash
curl -X POST "http://localhost:8000/api/v1/inventory/holds/{reservation_id}/convert"
```

### Check Availability

```bash
curl "http://localhost:8000/api/v1/inventory/availability?sku_ids=uuid1&sku_ids=uuid2"
```

## Command Line Interface (CLI)

The project includes a terminal-based CLI for easy interaction with the inventory system.

### Installation

Make sure to install the CLI dependencies:
```bash
pip install -r requirements.txt
```

### Usage

#### Interactive Mode (Recommended)

Start the interactive menu:
```bash
python cli.py interactive
```

This will show a menu where you can:
- List all products
- Create new products
- Check availability
- Create holds
- Check consistency
- Health check

#### Individual Commands

You can also use individual commands:

**List all products:**
```bash
python cli.py list-products
```

**Create a product:**
```bash
python cli.py create-product
```

**Check availability:**
```bash
python cli.py availability
```

**Create a hold:**
```bash
python cli.py create-hold
```

**Check consistency:**
```bash
python cli.py consistency
```

**Health check:**
```bash
python cli.py health
```

**Custom API URL:**
```bash
python cli.py --url http://localhost:8001 list-products
```

### CLI Features

- ✅ Beautiful terminal output with colors and tables
- ✅ Interactive prompts for easy input
- ✅ Error handling with helpful messages
- ✅ Connection status checking
- ✅ Formatted data display

## Testing

### Quick Test (Recommended First)

1. **Start the server:**
   ```bash
   uvicorn app.main:app --reload
   ```

2. **In another terminal, run the quick test script:**
   ```bash
   python quick_test.py
   ```
   
   This will verify all basic functionality is working.

### Automated Tests

Run tests with pytest:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=app --cov-report=html
```

### Manual Testing

1. **Use Swagger UI** (Easiest):
   - Start the server
   - Open http://localhost:8000/docs
   - Use the interactive API documentation to test endpoints

2. **Use curl commands** (See [TESTING_GUIDE.md](TESTING_GUIDE.md) for detailed examples)

3. **Check health endpoint:**
   ```bash
   curl http://localhost:8000/health
   ```

For detailed testing instructions, see [TESTING_GUIDE.md](TESTING_GUIDE.md).

## Design Decisions

### Locking Strategies

- **Optimistic Locking**: Uses version field with retry logic. Best for low-contention scenarios.
- **Pessimistic Locking**: Uses database row locks and asyncio locks. Best for high-contention scenarios.

### Idempotency

Idempotency is enforced via unique constraint on `client_token` in the `reservations` table. Duplicate requests with the same token return the existing reservation.

### Batch Operations

Batch holds are atomic - either all SKUs are reserved or none. Uses database transactions to ensure consistency.

### Expiry

Background worker runs every 60 seconds (configurable) to expire held reservations past their expiry time.

## Development Log

See [DEVELOPMENT_LOG.md](DEVELOPMENT_LOG.md) for detailed progress tracking, decisions, and implementation notes.

## License

[Add your license here]

