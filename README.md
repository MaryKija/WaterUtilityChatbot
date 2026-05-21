# Water Utility Chatbot - AI-Powered Customer Support

A comprehensive, production-ready chatbot system for water utility customer support with advanced AI capabilities, secure admin panel, and evaluation metrics.

## 🎯 Project Scope

This is a **complete customer service solution** that includes:

- **AI-Powered Chat Interface**: Natural language understanding via Groq LLM
- **Secure Admin Dashboard**: Token-based authentication with role-based access control
- **Complaint Management**: Full ticket lifecycle with escalation support
- **Billing Integration**: Account inquiries and payment processing
- **Evaluation System**: Real-time metrics and user feedback collection
- **PII Protection**: Automatic data redaction and privacy compliance
- **Audit Logging**: Complete security event tracking

## 🚀 Live Demo

**Development Environment**: `http://127.0.0.1:8000`
**Admin Panel**: `http://127.0.0.1:8000/admin`

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Frontend Layer                        │
│  ┌─────────────────┐  ┌─────────────────┐         │
│  │ Customer UI    │  │ Admin Dashboard │         │
│  │ (React/Vite)   │  │  (HTML/JS)     │         │
│  └─────────────────┘  └─────────────────┘         │
└─────────────────────────────────────────────────────────────┘
                         │ HTTP API
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                 FastAPI Backend                        │
├─────────────────────────────────────────────────────────────┤
│  • Authentication & Authorization (auth.py)             │
│  • Request Routing & Validation (main.py)              │
│  • Intent Classification (intent_pipeline.py)           │
│  • Conversation Orchestration (orchestrator.py)         │
│  • Tool Execution (tools.py)                          │
│  • Data Storage (storage.py)                          │
│  • Metrics Collection (metrics_collector.py)            │
└─────────────────────────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Groq LLM  │  │   SQLite DB  │  │   Admin UI  │
│   (AI)      │  │  (Storage)   │  │ (Dashboard) │
└──────────────┘  └──────────────┘  └──────────────┘
```

## 📋 Features

### Core Capabilities
- **Water Issue Reporting**: No water, low pressure, leaks, quality issues
- **Billing & Payments**: Account inquiries, bill checking, payment methods
- **Complaint Tracking**: Reference-based status tracking with WC-XXXXXX format
- **New Connections**: Application guidance and process information
- **Office Information**: Branch locations and operating hours
- **Human Escalation**: Seamless handoff to support team
- **Emergency Detection**: Automatic escalation for urgent situations

### Technical Features
- ✅ **Advanced AI**: Groq LLM with intent classification and entity extraction
- ✅ **Secure Authentication**: Token-based auth with role-based access control
- ✅ **PII Protection**: Automatic data redaction based on user roles
- ✅ **Multi-turn Conversations**: Context-aware session management
- ✅ **Admin Dashboard**: Comprehensive management interface with metrics
- ✅ **Evaluation System**: Real-time performance tracking and user feedback
- ✅ **Audit Logging**: Complete security event tracking
- ✅ **Structured Logging**: JSON-formatted logs with sensitive data filtering
- ✅ **Input Validation**: Comprehensive sanitization and validation

### Admin Dashboard Features
- **Real-time Metrics**: Live performance monitoring
- **Complaint Management**: Full ticket lifecycle management
- **User Analytics**: Session and interaction analytics
- **System Health**: Service status and error monitoring

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+ (for frontend development)
- Groq API key (free tier available)

### Installation

1. **Clone repository**
   ```bash
   git clone <repository-url>
   cd agentic_whatsapp_bot
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

5. **Initialize database with sample data**
   ```bash
   python scripts/seed_database.py
   ```

## 🔧 Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Required: Groq API Configuration
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant

# Server Configuration
HOST=127.0.0.1
PORT=8000
DEBUG=false

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=logs/app.log

# Admin Configuration (for development)
ADMIN_DEFAULT_USERNAME=admin
ADMIN_DEFAULT_PASSWORD=admin123
SUPER_ADMIN_USERNAME=superadmin
SUPER_ADMIN_PASSWORD=admin123

# Security Configuration
TOKEN_EXPIRE_HOURS=24
SESSION_SECRET=your_session_secret_here
```

## 🏃‍♂️ Running the Application

### Backend Server
```bash
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### Customer Frontend
```bash
cd frontend/aqua-chat-modern-main
npm install
npm run dev
```
Open the Vite URL shown in terminal (usually `http://127.0.0.1:5173`)

### Admin Dashboard
Access at: `http://127.0.0.1:8000/admin`

**Demo Credentials:**
- **Admin**: `admin` / `admin123`
- **Super Admin**: `superadmin` / `admin123`

## 🧪 Testing

### Run Test Suite
```bash
python -m pytest tests/ -v
```

### Manual Testing
```bash
# Test LLM connection
curl http://127.0.0.1:8000/test_llm

# Test chat endpoint
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"phone": "+260970000000", "message": "No water in my area"}'
```

### Database Testing
```bash
# Fresh database with sample data
python scripts/seed_database.py
```

## 🚨 Known Limitations

### Current Limitations
- **Single LLM Provider**: Currently only supports Groq (no fallback providers)
- **Mock Data**: Billing and account data uses simulated information
- **No Real WhatsApp Integration**: Currently web-based only
- **SQLite Only**: No support for other database systems
- **Local File Storage**: No cloud storage integration

### Performance Considerations
- **Concurrent Users**: Optimized for <100 simultaneous users
- **Database Size**: SQLite suitable for <10,000 records
- **Memory Usage**: LLM responses cached in memory

## 🔮 Future WhatsApp Integration Plan

### Phase 1: WhatsApp API Integration
- [ ] **WhatsApp Business API** integration
- [ ] **Webhook configuration** for message handling
- [ ] **Message format adaptation** for WhatsApp constraints
- [ ] **Media support** for images and documents

### Phase 2: Enhanced Features
- [ ] **Interactive buttons** and quick replies
- [ ] **Location services** integration
- [ ] **Payment processing** via WhatsApp Pay
- [ ] **Multilingual support** for local languages

### Phase 3: Production Scaling
- [ ] **Cloud database** migration (PostgreSQL)
- [ ] **Load balancing** for high availability
- [ ] **Monitoring and alerting** system
- [ ] **Automated deployment** pipeline

## 📊 API Reference

### Authentication Endpoints
```bash
POST /auth/login      # Admin login
POST /auth/logout     # Admin logout
```

### Customer Endpoints
```bash
POST /chat            # Send message to bot
POST /chat/clear      # Clear conversation history
GET  /chat/updates    # Get conversation updates
POST /feedback        # Submit user feedback
```

### Admin Endpoints (Authentication Required)
```bash
GET  /admin/dashboard           # Dashboard metrics
GET  /admin/complaints         # List all complaints
GET  /admin/complaint/{id}     # Get specific complaint
GET  /admin/escalations        # List escalations
GET  /admin/session/{id}        # Get session history
POST /admin/resolution          # Manage resolutions
```

### Health Check
```bash
GET /health           # System health status
```

## 🔐 Security Features

### Authentication & Authorization
- **Token-Based Auth**: Secure JWT-like tokens with expiration
- **Role-Based Access**: CUSTOMER, ADMIN, SUPER_ADMIN roles
- **Permission System**: Granular access control for different actions
- **Session Management**: Automatic token cleanup and expiration

### Data Protection
- **PII Redaction**: Automatic masking of sensitive information
- **Role-Based Data Access**: Different data levels for different users
- **Audit Logging**: Complete security event tracking
- **Input Validation**: Comprehensive sanitization and validation

### Compliance
- **Data Retention**: Configurable retention policies
- **User Consent**: Explicit consent for data processing
- **Right to Deletion**: User data removal capabilities
- **Transparency**: Clear data usage policies

## 📈 Evaluation & Metrics

### Performance Metrics
- **Response Time**: Average bot response times
- **Intent Accuracy**: Classification confidence scores
- **Resolution Rate**: Successful issue resolution percentage
- **User Satisfaction**: Feedback ratings and scores

## 📁 Project Structure

```
agentic_whatsapp_bot/
├── backend/                    # Python backend modules
│   ├── auth.py               # Authentication & authorization
│   ├── orchestrator.py        # Conversation orchestration
│   ├── intent_pipeline.py     # Intent classification
│   ├── tools.py              # Tool implementations
│   ├── storage.py            # Database layer
│   ├── metrics_collector.py   # Performance metrics
│   ├── llm/                 # LLM integration
│   ├── learning/             # ML components
│   └── emergency_detector.py # Emergency detection
├── frontend/                  # Frontend applications
│   └── aqua-chat-modern-main/  # React customer UI
├── static/                    # Static assets
│   ├── admin.html             # Admin dashboard
│   └── feedback.html         # Feedback form
├── scripts/                   # Utility scripts
│   └── seed_database.py      # Database seeding
├── tests/                     # Test suite
├── logs/                      # Application logs
├── requirements.txt            # Python dependencies
├── .env.example              # Environment template
├── .gitignore                # Git ignore rules
├── ETHICS.md                 # Ethics framework
└── README.md                 # This file
```

## 🛡️ Ethics and Trust

Our commitment to responsible AI deployment and user trust.

### Key Principles
- **AI Disclosure**: Clear identification that users are interacting with an AI system
- **Data Privacy**: Automatic PII redaction and transparent data practices
- **Human Oversight**: Automatic escalation for emergencies and complex issues
- **Accuracy**: No hallucinated information - all responses based on verified sources
- **User Consent**: Explicit consent for data storage and processing

📖 **Full Ethics Framework**: See [ETHICS.md](./ETHICS.md) for comprehensive details

## 🚀 Deployment

### Local Development
```bash
# Backend
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

# Frontend (development)
cd frontend/aqua-chat-modern-main
npm run dev
```

### Production Deployment
```bash
# Build frontend
cd frontend/aqua-chat-modern-main
npm run build

# Run production server
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### Environment Setup
- **Development**: Use `.env` file with demo credentials
- **Production**: Set environment variables in your hosting platform
- **Security**: Change default admin passwords in production
- **Database**: Run `scripts/seed_database.py` for initial setup

## 🤝 Contributing

This is a capstone project demonstrating enterprise-grade AI chatbot development. For contributions:

1. Follow the existing code style and patterns
2. Add comprehensive tests for new features
3. Update documentation for any API changes
4. Ensure security best practices are maintained

## 📄 License

Academic project - use for educational purposes with attribution.

## 🙋 Support

For issues or questions:
1. Check logs in `logs/` directory
2. Verify environment variables are set correctly
3. Test with `/health` endpoint for system status
4. Review troubleshooting section in documentation

---

**Built with ❤️ for 2026 Capstone Project**
