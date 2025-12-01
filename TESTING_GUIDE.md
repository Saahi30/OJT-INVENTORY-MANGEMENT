# Testing Guide - Inventory Reservation Service

This guide will help you test the application to verify it's working correctly.

## Prerequisites

1. **Python 3.10+** installed
2. **PostgreSQL** installed and running
3. **pip** installed

## Step 1: Setup Environment

### 1.1 Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 1.2 Configure Database

Create a `.env` file in the project root:

```bash
# Copy example file
cp .env.example .env
```

Edit `.env` and set your database URL:
```
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/inventory_db
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### 1.3 Create Database

```bash
# Create PostgreSQL database
createdb inventory_db

# Or using psql:
psql -U postgres
CREATE DATABASE inventory_db;
\q
```

## Step 2: Run the Application

### Option A: Using uvicorn directly

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Option B: Using the run script

```bash
./run.sh
```

You should see output like:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

## Step 3: Verify Application is Running

### 3.1 Check Health Endpoint

Open your browser or use curl:

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "healthy"}
```

### 3.2 Check API Documentation

Open in browser:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

You should see all available endpoints listed.

## Step 4: Manual API Testing

### 4.1 Create a SKU

```bash
curl -X POST "http://localhost:8000/api/v1/skus" \
  -H "Content-Type: application/json" \
  -d '{
    "sku_code": "PROD-001",
    "name": "Test Product",
    "description": "A test product",
    "initial_qty": 100
  }'
```

**Expected Response:**
```json
{
  "sku_id": "uuid-here",
  "sku_code": "PROD-001",
  "name": "Test Product",
  "description": "A test product",
  "attributes": null
}
```

**Save the `sku_id` from the response for next steps!**

### 4.2 Check Availability

```bash
# Replace SKU_ID with the actual UUID from step 4.1
curl "http://localhost:8000/api/v1/inventory/availability?sku_ids=SKU_ID"
```

**Expected Response:**
```json
[
  {
    "sku_id": "uuid-here",
    "total_qty": 100,
    "reserved_qty": 0,
    "allocated_qty": 0,
    "available_qty": 100,
    "version": 1
  }
]
```

### 4.3 Create a Hold

```bash
# Replace SKU_ID with the actual UUID
curl -X POST "http://localhost:8000/api/v1/inventory/holds" \
  -H "Content-Type: application/json" \
  -d '{
    "client_token": "test-token-123",
    "items": [
      {"sku_id": "SKU_ID", "qty": 10}
    ],
    "expires_in_seconds": 300,
    "strategy": "optimistic"
  }'
```

**Expected Response:**
```json
{
  "reservation_id": "uuid-here",
  "client_token": "test-token-123",
  "status": "HELD",
  "type": "HOLD",
  "total_items": 1,
  "items": [
    {
      "reservation_item_id": "uuid-here",
      "sku_id": "SKU_ID",
      "qty": 10
    }
  ],
  "expires_at": "2024-01-01T12:05:00Z"
}
```

**Save the `reservation_id` for next steps!**

### 4.4 Verify Inventory Updated

```bash
# Check availability again - should show 10 reserved
curl "http://localhost:8000/api/v1/inventory/availability?sku_ids=SKU_ID"
```

**Expected Response:**
```json
[
  {
    "sku_id": "uuid-here",
    "total_qty": 100,
    "reserved_qty": 10,
    "allocated_qty": 0,
    "available_qty": 90,
    "version": 2
  }
]
```

### 4.5 Test Idempotency

```bash
# Try creating the same hold again with same client_token
curl -X POST "http://localhost:8000/api/v1/inventory/holds" \
  -H "Content-Type: application/json" \
  -d '{
    "client_token": "test-token-123",
    "items": [
      {"sku_id": "SKU_ID", "qty": 10}
    ],
    "expires_in_seconds": 300,
    "strategy": "optimistic"
  }'
```

**Expected:** Should return the SAME reservation_id (idempotency working!)

### 4.6 Convert Hold to Allocation

```bash
# Replace RESERVATION_ID with the actual UUID from step 4.3
curl -X POST "http://localhost:8000/api/v1/inventory/holds/RESERVATION_ID/convert"
```

**Expected Response:**
```json
{
  "reservation_id": "uuid-here",
  "status": "ALLOCATED",
  "type": "HOLD",
  ...
}
```

### 4.7 Verify Allocation

```bash
# Check availability - reserved should be 0, allocated should be 10
curl "http://localhost:8000/api/v1/inventory/availability?sku_ids=SKU_ID"
```

**Expected Response:**
```json
[
  {
    "sku_id": "uuid-here",
    "total_qty": 100,
    "reserved_qty": 0,
    "allocated_qty": 10,
    "available_qty": 90,
    "version": 3
  }
]
```

### 4.8 Test Batch Hold

```bash
# Create another SKU first
curl -X POST "http://localhost:8000/api/v1/skus" \
  -H "Content-Type: application/json" \
  -d '{
    "sku_code": "PROD-002",
    "name": "Test Product 2",
    "initial_qty": 50
  }'

# Then create batch hold with both SKUs
curl -X POST "http://localhost:8000/api/v1/inventory/holds" \
  -H "Content-Type: application/json" \
  -d '{
    "client_token": "batch-token-456",
    "items": [
      {"sku_id": "SKU_ID_1", "qty": 5},
      {"sku_id": "SKU_ID_2", "qty": 3}
    ],
    "expires_in_seconds": 300,
    "strategy": "optimistic"
  }'
```

### 4.9 Test Consistency Check

```bash
curl "http://localhost:8000/api/v1/inventory/consistency"
```

**Expected Response:**
```json
{
  "is_consistent": true,
  "total_skus": 2,
  "inconsistent_skus": [],
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### 4.10 Test Error Cases

#### Insufficient Inventory
```bash
curl -X POST "http://localhost:8000/api/v1/inventory/holds" \
  -H "Content-Type: application/json" \
  -d '{
    "client_token": "error-test",
    "items": [
      {"sku_id": "SKU_ID", "qty": 1000}
    ],
    "expires_in_seconds": 300,
    "strategy": "optimistic"
  }'
```

**Expected:** 400 Bad Request with "Insufficient inventory" error

#### Invalid Reservation ID
```bash
curl -X POST "http://localhost:8000/api/v1/inventory/holds/00000000-0000-0000-0000-000000000000/convert"
```

**Expected:** 400 Bad Request with "Reservation not found" error

## Step 5: Run Automated Tests

### 5.1 Run All Tests

```bash
pytest
```

### 5.2 Run with Verbose Output

```bash
pytest -v
```

### 5.3 Run Specific Test File

```bash
pytest tests/test_inventory_service.py
pytest tests/test_api.py
```

### 5.4 Run with Coverage

```bash
pytest --cov=app --cov-report=html
```

Then open `htmlcov/index.html` in your browser to see coverage report.

## Step 6: Test Locking Strategies

### 6.1 Test Optimistic Locking

Create a hold with optimistic strategy:
```bash
curl -X POST "http://localhost:8000/api/v1/inventory/holds" \
  -H "Content-Type: application/json" \
  -d '{
    "client_token": "opt-test-1",
    "items": [{"sku_id": "SKU_ID", "qty": 5}],
    "expires_in_seconds": 300,
    "strategy": "optimistic"
  }'
```

### 6.2 Test Pessimistic Locking

Create a hold with pessimistic strategy:
```bash
curl -X POST "http://localhost:8000/api/v1/inventory/holds" \
  -H "Content-Type: application/json" \
  -d '{
    "client_token": "pess-test-1",
    "items": [{"sku_id": "SKU_ID", "qty": 5}],
    "expires_in_seconds": 300,
    "strategy": "pessimistic"
  }'
```

## Step 7: Test Expiry Mechanism

### 7.1 Create a Hold with Short Expiry

```bash
curl -X POST "http://localhost:8000/api/v1/inventory/holds" \
  -H "Content-Type: application/json" \
  -d '{
    "client_token": "expiry-test",
    "items": [{"sku_id": "SKU_ID", "qty": 5}],
    "expires_in_seconds": 5,
    "strategy": "optimistic"
  }'
```

### 7.2 Wait 70 seconds (expiry worker runs every 60 seconds)

### 7.3 Check Reservation Status

The reservation should automatically change to `EXPIRED` status and inventory should be released.

## Step 8: Using Swagger UI (Easiest Method)

1. Start the application
2. Open http://localhost:8000/docs in your browser
3. You'll see an interactive API documentation
4. Click "Try it out" on any endpoint
5. Fill in the request body
6. Click "Execute"
7. See the response

This is the easiest way to test all endpoints!

## Troubleshooting

### Database Connection Error

**Error:** `asyncpg.exceptions.InvalidPasswordError` or connection refused

**Solution:**
- Verify PostgreSQL is running: `pg_isready`
- Check database URL in `.env` file
- Verify username/password are correct
- Ensure database exists: `psql -l`

### Port Already in Use

**Error:** `Address already in use`

**Solution:**
```bash
# Use a different port
uvicorn app.main:app --reload --port 8001
```

### Import Errors

**Error:** `ModuleNotFoundError: No module named 'app'`

**Solution:**
- Ensure you're in the project root directory
- Activate virtual environment
- Install dependencies: `pip install -r requirements.txt`

### Tables Not Created

**Error:** `relation "skus" does not exist`

**Solution:**
- The app should create tables automatically on startup
- Check database connection
- Verify `init_db()` is called in `main.py`

## Success Criteria

✅ Application starts without errors  
✅ Health endpoint returns `{"status": "healthy"}`  
✅ Can create SKU  
✅ Can create hold  
✅ Inventory updates correctly  
✅ Idempotency works (duplicate requests return same result)  
✅ Can convert hold to allocation  
✅ Can release hold  
✅ Batch operations work  
✅ Consistency check returns `is_consistent: true`  
✅ Tests pass  

## Next Steps

Once basic testing is complete:
1. Test concurrent requests (multiple holds on same SKU)
2. Test edge cases (zero quantity, negative values, etc.)
3. Load testing (if needed)
4. Review audit logs in database

---

**Happy Testing! 🚀**

