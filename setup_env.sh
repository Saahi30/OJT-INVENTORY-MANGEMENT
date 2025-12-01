#!/bin/bash
# Script to create .env file for the Inventory Reservation Service

echo "Setting up .env file..."
echo ""

# Check if .env already exists
if [ -f .env ]; then
    echo "⚠️  .env file already exists!"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted. Keeping existing .env file."
        exit 0
    fi
fi

# Get database configuration
echo "Enter your PostgreSQL database configuration:"
echo ""

read -p "Database username [postgres]: " DB_USER
DB_USER=${DB_USER:-postgres}

read -p "Database password [postgres]: " -s DB_PASS
echo ""
DB_PASS=${DB_PASS:-postgres}

read -p "Database host [localhost]: " DB_HOST
DB_HOST=${DB_HOST:-localhost}

read -p "Database port [5432]: " DB_PORT
DB_PORT=${DB_PORT:-5432}

read -p "Database name [inventory_db]: " DB_NAME
DB_NAME=${DB_NAME:-inventory_db}

# Create .env file
cat > .env << EOF
DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}
ENVIRONMENT=development
LOG_LEVEL=INFO
EOF

echo ""
echo "✅ .env file created successfully!"
echo ""
echo "Contents:"
echo "DATABASE_URL=postgresql+asyncpg://${DB_USER}:***@${DB_HOST}:${DB_PORT}/${DB_NAME}"
echo "ENVIRONMENT=development"
echo "LOG_LEVEL=INFO"
echo ""
echo "Next steps:"
echo "1. Make sure PostgreSQL is running"
echo "2. Create the database: createdb ${DB_NAME}"
echo "3. Start the application: uvicorn app.main:app --reload"

