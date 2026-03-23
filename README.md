# Water Utility Chatbot - AI-Powered Customer Support

A modern, LLM-first chatbot for water utility customer support, demonstrating agentic AI principles, multi-turn conversations, and tool integration.

## 🚀 Live Demo

**Deployed on Vercel:** [Ready for deployment - follow deployment instructions below](#-deployment)

*Note: Replace this link with your actual Vercel URL after deployment*

## 🎯 Project Overview

This project showcases:
- **Agentic AI Design**: LLM-first intent classification (Groq only)
- **Multi-Turn Conversations**: Stateful session management for complex workflows
- **Tool Integration**: Structured tools for complaints, billing, and customer service
- **Natural Language Robustness**: Flexible entity extraction and input handling
- **Production-Ready Patterns**: Logging, validation, configuration management
- **Cloud Deployment**: Vercel + Supabase for scalable deployment

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (HTML/JS)                       │
│              WhatsApp-like Chat Interface                   │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP POST /chat
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend                           │
├─────────────────────────────────────────────────────────────┤
│  main.py: Request handling, input validation               │
│  config.py: Configuration management                        │
│  logger.py: Structured logging                             │
│  validation.py: Input validation & sanitization            │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  agent.py    │  │  tools.py    │  │  storage.py  │
│  (Router)    │  │  (Actions)   │  │  (Database)  │
└──────────────┘  └──────────────┘  └──────────────┘
        │                │                │
        └────────────────┼────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ OpenRouter   │  │   Intents    │  │  SQLite DB   │
│   LLM API    │  │  (Fallback)  │  │  (Complaints)│
└──────────────┘  └──────────────┘  └──────────────┘
```

## 📋 Features

### Core Capabilities
- **Water Issue Reporting**: No water, low pressure, leaks, quality issues
- **Billing & Payments**: Bill inquiries, payment methods, disputes
- **Complaint Tracking**: Reference-based status checks
- **New Connections**: Application guidance
- **Office Information**: Locations and hours
- **Human Escalation**: Seamless handoff to support team

### Technical Features
- ✅ LLM-first intent classification (Groq)
- ✅ Multi-turn conversation flows
- ✅ Structured logging with sensitive data filtering
- ✅ Input validation and sanitization
- ✅ Fallback mechanisms for API failures
- ✅ Session management per user
- ✅ Ticket ID standardization (WC-XXXXXX format)
- ✅ Configuration management via environment variables

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- pip or conda
- Groq API key (free tier available)

### Installation

1. **Clone the repository**
   ```bash
   cd agentic_whatsapp_bot
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

5. **Run the server**
   ```bash
   python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
   ```

6. **Open the frontend**
   - Navigate to `frontend/index.html` in your browser
   - Or open: `file:///path/to/frontend/index.html`

## � Deployment

### Local Network Deployment
For testing on your local network:

```bash
# Run with network binding
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

# Access from other devices on your network at:
# http://YOUR_LOCAL_IP:8000 (e.g., http://192.168.1.100:8000)
```

### Vercel Cloud Deployment
Deploy to Vercel for internet-accessible hosting (SQLite remains the default DB in local and small-scale deployments):

1. **Prerequisites**
   - Vercel account (free)
   - GitHub account

2. **Deploy to Vercel**
   ```bash
   # Install Vercel CLI
   npm install -g vercel

   # Login to Vercel
   vercel login

   # Deploy
   vercel --prod

   # Or connect to GitHub for automatic deployments
   vercel link
   vercel --prod
   ```

3. **Environment Variables in Vercel**
   Set these in your Vercel dashboard:
   ```
   GROQ_API_KEY=your_groq_api_key
   PYTHONPATH=.
   ```

4. **Access Your Live App**
   - Vercel will provide a live URL (e.g., `https://your-app.vercel.app`)
   - Frontend: `https://your-app.vercel.app`
   - Admin Panel: `https://your-app.vercel.app/admin/`
   - API: `https://your-app.vercel.app/api/chat`

> Note: Vercel serverless filesystem is ephemeral. For production data durability you can still run the app on a VM or container with SQLite, or migrate to a managed DB later when needed.

## �📝 Configuration

### Environment Variables (.env)

```env
# API Keys (Required)
GROQ_API_KEY=your_key_here

# Model Selection
GROQ_MODEL=mixtral-8x7b-32768

# Server Configuration
HOST=127.0.0.1
PORT=8000
DEBUG=False

# Logging
LOG_LEVEL=INFO

# Rate Limiting
RATE_LIMIT_ENABLED=True
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_WINDOW=60

# CORS
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:8000
```

## AI Engine

This system uses Groq as the sole LLM.
No third-party fallback is used.
All intent classification is AI-driven.
Guardrails restrict usage to water utility services.

Default model: `llama-3.1-8b-instant` (override with `GROQ_MODEL`).

## 🔄 Conversation Flows

### 1. Water Issue Reporting
```
User: "No water in my area"
Bot: "I can help report this issue. Please provide (in order):
      1. name
      2. area
      3. issue"
User: "John"
Bot: "Thanks — I got: name: John.
      Please provide the remaining information:
      - area
      - issue"
User: "Makululu, no water supply"
Bot: "✅ Complaint Logged Successfully
      Reference Number: WC-A1B2C3
      ..."
```

### 2. Billing Inquiry
```
User: "Check my bill"
Bot: "Please provide your account number..."
User: "123456"
Bot: "💳 Billing Information
      Account: 123456
      Amount Due: K245.60
      ..."
```

### 3. Complaint Follow-Up
```
User: "Track my complaint"
Bot: "Please provide your reference number..."
User: "WC-A1B2C3"
Bot: "✅ Complaint Status
      Reference: WC-A1B2C3
      Status: RECEIVED
      ..."
```

## 📊 Logging

Logs are stored in `logs/` directory:
- `app.log`: All application logs (structured JSON format)
- `errors.log`: Error-level logs only

Sensitive data (API keys, phone numbers, account numbers) is automatically redacted.

## 🧪 Testing

### Run Tests
```bash
python -m pytest tests/ -v
```

### Manual Testing
```bash
python test_agent_flow.py
python test_issue_fix.py
```

## 🔐 Security

- ✅ API keys protected in `.env` (not committed)
- ✅ Input validation and sanitization
- ✅ Sensitive data filtering in logs
- ✅ SQL injection prevention (parameterized queries)
- ✅ CORS configuration
- ✅ Rate limiting support

## 📚 API Reference

### POST /chat
Submit a user message and get a bot response.

**Request:**
```json
{
  "phone": "+260970000000",
  "message": "No water in my area"
}
```

**Response:**
```json
{
  "reply": "I can help report this issue...",
  "intent": "no_water_supply",
  "confidence": 0.95,
  "entities": {
    "name": "",
    "area": "",
    "issue": "No water supply",
    "ticket_id": "",
    "account_number": ""
  }
}
```

### GET /test_llm
Test Groq API connection.

**Response:**
```json
{
  "success": true,
  "raw_response": {...}
}
```

## 🎓 Academic Insights

### Agentic AI Principles Demonstrated

1. **LLM-First Design**: The system trusts LLM classification over keyword matching
2. **Fallback Mechanisms**: Multiple fallback chains ensure robustness
3. **Tool Integration**: Structured tools (log_complaint, get_bill, etc.) extend LLM capabilities
4. **State Management**: Session tracking enables multi-turn conversations
5. **Confidence Scoring**: Intent confidence guides response strategy

### Design Decisions

- **Why LLM-first?** More natural, flexible, and scalable than keyword matching
- **Why multi-turn flows?** Realistic customer interactions require context
- **Why structured logging?** Essential for debugging and monitoring
- **Why validation?** Prevents errors and improves user experience

## 🔮 Future Enhancements

### Phase 2: Functional Realism
- [ ] Database for billing accounts
- [ ] Database for office locations
- [ ] Improved multi-turn context awareness
- [ ] Confidence thresholds for intent classification

### Phase 3: Quality & Maintainability
- [ ] Unit tests for core modules
- [ ] Integration tests for conversation flows
- [ ] Database indexes and optimization
- [ ] API versioning (/v1/chat)

### Phase 4: User Experience
- [ ] Responsive frontend design
- [ ] Accessibility improvements (WCAG 2.1)
- [ ] Dark mode support
- [ ] Quick-reply suggestions

### Phase 5: Documentation
- [ ] Architecture diagrams
- [ ] API documentation (Swagger)
- [ ] Deployment guide
- [ ] Troubleshooting guide

## 📖 Project Structure

```
agentic_whatsapp_bot/
├── backend/
│   ├── __init__.py
│   ├── main.py              # FastAPI app & endpoints
│   ├── agent.py             # Intent routing & flows
│   ├── tools.py             # Tool implementations
│   ├── storage.py           # Database layer
│   ├── intents.py           # Fallback intent detection
│   ├── llm_client.py        # LLM integration
│   ├── config.py            # Configuration management
│   ├── logger.py            # Structured logging
│   └── validation.py        # Input validation
├── frontend/
│   └── index.html           # Chat UI
├── tests/
│   └── test_agent_flow.py   # Integration tests
├── logs/                    # Application logs
├── database.db              # SQLite database
├── requirements.txt         # Python dependencies
├── .env.example             # Environment template
├── .gitignore               # Git ignore rules
└── README.md                # This file
```

## 🤝 Contributing

This is a student capstone project. For improvements:
1. Create a feature branch
2. Make changes with clear commit messages
3. Test thoroughly
4. Submit for review

## 📄 License

Academic project - use for educational purposes.

## 🙋 Support

For issues or questions:
1. Check the logs in `logs/` directory
2. Review the troubleshooting section below
3. Test with `/test_llm` endpoint

### Troubleshooting

**Issue**: "GROQ_API_KEY missing"
- **Solution**: Ensure `agentic_whatsapp_bot/.env` exists and contains a valid `GROQ_API_KEY`

**Issue**: "Groq returned non-JSON output" in intent classification
- **Solution**: Check Groq status and that `response_format` is supported for your model

**Issue**: Ticket ID not found when tracking complaint
- **Solution**: Ensure ticket ID format is WC-XXXXXX (6 alphanumeric chars)

**Issue**: Frontend not connecting to backend
- **Solution**: Verify backend is running on http://127.0.0.1:8000

---

**Built with ❤️ for the 2026 Capstone Project**
