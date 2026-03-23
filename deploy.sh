#!/bin/bash
# Production deployment script for WhatsApp Bot

echo "🚀 Starting WhatsApp Bot Deployment..."

# Set working directory
cd "$(dirname "$0")"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found. Please create it with your configuration."
    exit 1
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install Python dependencies"
    exit 1
fi

# Build frontend applications
echo "🔨 Building customer chat frontend..."
cd frontend/aqua-chat-modern-main
npm install
npm run build

if [ $? -ne 0 ]; then
    echo "❌ Failed to build customer chat frontend"
    exit 1
fi

echo "🔨 Building admin panel..."
cd ../admin
npm install
npm run build

if [ $? -ne 0 ]; then
    echo "❌ Failed to build admin panel"
    exit 1
fi

cd ../..

# Create production directories
mkdir -p production
mkdir -p production/frontend-customer
mkdir -p production/frontend-admin

# Copy built frontends
cp -r frontend/aqua-chat-modern-main/dist/* production/frontend-customer/
cp -r frontend/admin/dist/* production/frontend-admin/

echo "✅ Build complete!"
echo ""
echo "🎯 Deployment Summary:"
echo "  Backend API: Ready to run with 'python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000'"
echo "  Customer Chat: Available in production/frontend-customer/"
echo "  Admin Panel: Available in production/frontend-admin/"
echo ""
echo "💡 Next steps:"
echo "  1. Configure your web server (nginx/apache) to serve the frontend directories"
echo "  2. Set up the backend as a system service or use a process manager like PM2"
echo "  3. Configure SSL certificates for HTTPS"
echo "  4. Set up monitoring and logging"