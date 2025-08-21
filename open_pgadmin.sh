#!/bin/bash

# Open pgAdmin convenience script

echo "🔧 Checking if pgAdmin is running..."

if ! docker ps | grep -q contrap_pgadmin; then
    echo "⚠️  pgAdmin is not running. Starting it now..."
    docker compose up -d pgadmin
    echo "⏳ Waiting for pgAdmin to start..."
    sleep 5
fi

echo "✅ pgAdmin is running!"
echo ""
echo "📋 Connection Details:"
echo "   URL: http://localhost:5050"
echo "   Email: admin@contrap.pt"
echo "   Password: admin"
echo ""
echo "📊 Database Connection Info (for adding server in pgAdmin):"
echo "   Host: postgres"
echo "   Port: 5432"
echo "   Database: contrap"
echo "   Username: contrap_user"
echo "   Password: contrap_dev_password"
echo ""

# Try to open in browser (works on macOS)
if command -v open &> /dev/null; then
    echo "🌐 Opening pgAdmin in your browser..."
    open http://localhost:5050
elif command -v xdg-open &> /dev/null; then
    # Linux
    xdg-open http://localhost:5050
else
    echo "🌐 Please open your browser and navigate to: http://localhost:5050"
fi
