# WhatsApp Bot Deployment Guide

## 🎯 System Overview

Your refactored WhatsApp bot consists of:
- **Backend API**: FastAPI server with state-driven architecture
- **Customer Chat Frontend**: React/Vite application for end users
- **Admin Panel Frontend**: React/Vite application for administrators

## 🚀 Quick Start (Development)

### Prerequisites
- Python 3.8+
- Node.js 16+
- npm or yarn

### 1. Environment Setup
Your `.env` file is already configured with the Groq API key. If you need to change settings, edit the `.env` file.

### 2. Development Mode
Run the development startup script:
```bash
# Windows
dev-start.bat

# Linux/Mac
./dev-start.sh
```

This will:
- Install Python dependencies
- Start the customer chat frontend on http://localhost:5173
- Start the admin panel on http://localhost:5174
- Start the backend API on http://localhost:8000

## 🏭 Production Deployment

### Option 1: Automated Deployment (Recommended)
```bash
# Windows
deploy.bat

# Linux/Mac
./deploy.sh
```

### Option 2: Manual Deployment

#### Backend Deployment
```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

#### Frontend Deployment
```bash
# Customer Chat Frontend
cd frontend/aqua-chat-modern-main
npm install
npm run build

# Admin Panel Frontend
cd ../admin
npm install
npm run build
```

## 🌐 Production Server Setup

> SQLite is supported and remains the default to avoid external DB dependency. If your deployment target is Vercel serverless, note that file-based SQLite is ephemeral; for stable state you can run on a VM/EC2/dedicated container.

### Using Nginx (Recommended)
```nginx
# /etc/nginx/sites-available/whatsapp-bot
server {
    listen 80;
    server_name your-domain.com;

    # Customer chat frontend
    location / {
        root /path/to/agentic_whatsapp_bot/production/frontend-customer;
        try_files $uri $uri/ /index.html;
    }

    # Admin panel
    location /admin {
        root /path/to/agentic_whatsapp_bot/production/frontend-admin;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Using Apache
```apache
<VirtualHost *:80>
    ServerName your-domain.com
    DocumentRoot /path/to/agentic_whatsapp_bot/production/frontend-customer

    # Customer chat
    <Directory "/path/to/agentic_whatsapp_bot/production/frontend-customer">
        Require all granted
    </Directory>

    # Admin panel
    Alias /admin /path/to/agentic_whatsapp_bot/production/frontend-admin
    <Directory "/path/to/agentic_whatsapp_bot/production/frontend-admin">
        Require all granted
    </Directory>

    # Backend API proxy
    ProxyPass /api http://127.0.0.1:8000/api
    ProxyPassReverse /api http://127.0.0.1:8000/api
</VirtualHost>
```

## 🔧 Environment Variables

Key configuration options in `.env`:

```bash
# Required
GROQ_API_KEY=your-api-key-here
ADMIN_TOKEN=your-secure-admin-token

# Optional
HOST=0.0.0.0          # Listen on all interfaces for production
PORT=8000             # API port
DEBUG=false           # Disable debug mode for production
LOG_LEVEL=INFO        # Logging level
```

## 🔒 Security Checklist

- [ ] Change the default `ADMIN_TOKEN` to a secure random string
- [ ] Set up HTTPS with SSL certificates
- [ ] Configure firewall rules (only open necessary ports)
- [ ] Use environment-specific `.env` files
- [ ] Set up log rotation
- [ ] Configure backup for SQLite database
- [ ] Set up monitoring and alerts

## 📊 Monitoring

### Health Check
```bash
curl http://localhost:8000/health
```

### Logs
Check the `logs/` directory for application logs.

### Database
SQLite database is stored in `backend/data/chatbot.db`.

## 🐛 Troubleshooting

### Common Issues

1. **Port already in use**: Change the PORT in `.env`
2. **CORS errors**: Add your domain to `CORS_ORIGINS` in `.env`
3. **API key errors**: Verify `GROQ_API_KEY` in `.env`
4. **Build failures**: Clear `node_modules` and reinstall

### Logs Location
- Application logs: `logs/`
- SQLite database: `backend/data/chatbot.db`

## 📞 Support

If you encounter issues:
1. Check the logs in the `logs/` directory
2. Verify your `.env` configuration
3. Ensure all dependencies are installed
4. Check that ports 8000, 5173, 5174 are available