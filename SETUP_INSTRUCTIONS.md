# Quick Setup Instructions

## The Error You're Seeing

If you see this error:
```
ValidationError: 1 validation error for Settings
database_url
  Field required [type=missing, input_value={}, input_type=dict]
```

It means the application can't find the database configuration.

## Solution: Create .env File

### Option 1: Create .env file manually

Create a file named `.env` in the project root with:

```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/inventory_db
ENVIRONMENT=development
LOG_LEVEL=INFO
```

**Important:** Replace `postgres:postgres` with your actual PostgreSQL username and password.

### Option 2: Use environment variable

Instead of creating `.env`, you can set the environment variable:

```bash
export DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/inventory_db
```

### Option 3: Quick setup script

Run this command to create the `.env` file:

```bash
cat > .env << 'EOF'
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/inventory_db
ENVIRONMENT=development
LOG_LEVEL=INFO
EOF
```

**Remember to edit the username and password!**

## Database Setup

1. **Make sure PostgreSQL is running:**
   ```bash
   pg_isready
   ```

2. **Create the database:**
   ```bash
   createdb inventory_db
   ```

   Or using psql:
   ```bash
   psql -U postgres
   CREATE DATABASE inventory_db;
   \q
   ```

## Verify Setup

1. **Check if .env file exists:**
   ```bash
   ls -la .env
   ```

2. **Check database connection:**
   ```bash
   psql -U postgres -d inventory_db -c "SELECT 1;"
   ```

3. **Start the application:**
   ```bash
   uvicorn app.main:app --reload
   ```

   You should see:
   ```
   INFO:     Uvicorn running on http://127.0.0.1:8000
   INFO:     Application startup complete.
   ```

## Common Database URLs

### Local PostgreSQL (default user)
```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/inventory_db
```

### Local PostgreSQL (custom user)
```
DATABASE_URL=postgresql+asyncpg://myuser:mypassword@localhost:5432/inventory_db
```

### PostgreSQL with custom port
```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/inventory_db
```

### Remote PostgreSQL
```
DATABASE_URL=postgresql+asyncpg://user:password@hostname:5432/inventory_db
```

## Troubleshooting

### "Connection refused"
- Make sure PostgreSQL is running: `pg_isready`
- Check if the port is correct (default is 5432)
- Verify username and password

### "Database does not exist"
- Create the database: `createdb inventory_db`

### "Password authentication failed"
- Check your username and password in the DATABASE_URL
- Try connecting manually: `psql -U username -d inventory_db`

### Still having issues?
1. Check the `.env` file exists and has correct format
2. Verify PostgreSQL is running
3. Test database connection manually
4. Check the application logs for more details

