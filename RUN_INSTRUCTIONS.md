# How to Run the Application

## ✅ Setup Complete!

Python 3.12 is installed and all dependencies are ready.

## Running the Application

### Step 1: Activate Virtual Environment

```bash
source venv/bin/activate
```

You should see `(venv)` in your terminal prompt.

### Step 2: Make Sure Database is Running

```bash
# Check if PostgreSQL is running
pg_isready

# If not running, start it (depends on your setup)
# brew services start postgresql@16
```

### Step 3: Start the Server

```bash
uvicorn app.main:app --reload
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

### Step 4: Access the Application

- **API Documentation (Swagger)**: http://localhost:8000/docs
- **Alternative Docs (ReDoc)**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Using the CLI

In a **new terminal window**:

```bash
# Activate venv
cd /Users/saahi/Desktop/OJT-INVENTORY-MANGEMENT
source venv/bin/activate

# Run CLI in interactive mode
python cli.py interactive

# Or use individual commands
python cli.py list-products
python cli.py create-product
python cli.py availability
```

## Quick Test

```bash
# In one terminal - start server
source venv/bin/activate
uvicorn app.main:app --reload

# In another terminal - test
source venv/bin/activate
python quick_test.py
```

## Important Notes

1. **Always activate venv first**: `source venv/bin/activate`
2. **Keep server running**: Don't close the terminal where uvicorn is running
3. **Use Python 3.12**: The venv is configured for Python 3.12

## Troubleshooting

### "Module not found"
- Make sure venv is activated: `source venv/bin/activate`
- Check Python version: `python --version` (should be 3.12.x)

### "Database connection error"
- Check PostgreSQL is running: `pg_isready`
- Check `.env` file has correct database URL

### "Port already in use"
- Use different port: `uvicorn app.main:app --reload --port 8001`

## Next Steps

1. Create some products using the CLI or API
2. Create holds and test the inventory system
3. Check the API documentation at http://localhost:8000/docs

Happy coding! 🚀

