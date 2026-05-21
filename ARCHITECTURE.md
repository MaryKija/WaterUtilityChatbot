# Water Utility Chatbot - System Architecture

## High-Level Overview

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
│  • Emergency Detection (emergency_detector.py)            │
│  • Evaluation System (evaluation.py)                   │
└─────────────────────────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Groq LLM  │  │   SQLite DB  │  │   Admin UI  │
│   (AI)      │  │  (Storage)   │  │ (Dashboard) │
└──────────────┘  ┌──────────────┘  └──────────────┘
```

## Module Responsibilities

### 1. **main.py** - FastAPI Application Entry Point
**Purpose**: Central API server and request routing

**Key Components**:
- FastAPI application setup and configuration
- Request validation and error handling
- Authentication endpoint routing
- Static file serving for frontend
- CORS and security middleware
- Health check endpoints

**Major Endpoints**:
```python
# Authentication
POST /auth/login          # Admin authentication
POST /auth/logout         # Token revocation

# Customer Interface
POST /chat               # Main chat endpoint
POST /chat/clear         # Clear conversation history
GET  /chat/updates       # Get conversation updates
POST /feedback           # Submit user feedback

# Admin Interface (Protected)
GET  /admin/dashboard     # Dashboard metrics
GET  /admin/complaints    # List all complaints
GET  /admin/complaint/{id} # Get specific complaint
GET  /admin/escalations   # List escalations
GET  /admin/session/{id}   # Get session history
POST /admin/resolution     # Manage resolutions

# System
GET  /health              # System health check
```

### 2. **auth.py** - Authentication & Authorization System
**Purpose**: Secure access control with role-based permissions

**Key Classes**:
- `UserRole`: Enum (CUSTOMER, ADMIN, SUPER_ADMIN)
- `Permission`: Enum (VIEW_DASHBOARD, MANAGE_RESOLUTIONS, etc.)
- `AdminUser`: User authentication and session data
- `AuthToken`: Token management and validation
- `AuthService`: Core authentication logic
- `PIIProtection`: Data redaction based on roles

**Security Features**:
- Token-based authentication with expiration
- Role-based access control (RBAC)
- Permission system for granular access
- Audit logging for all security events
- PII redaction based on user roles

### 3. **orchestrator.py** - Conversation Orchestration
**Purpose**: Central conversation flow management and AI coordination

**Key Functions**:
- `process()`: Main conversation entry point
- `_handle_new_intent()`: Intent classification and routing
- `_route_to_agent()`: Agent selection based on intent
- Session management and context tracking
- Metrics collection integration
- Emergency detection integration

**Conversation Flow**:
1. Receive user message and context
2. Classify intent using LLM pipeline
3. Route to appropriate agent/handler
4. Execute tools and collect responses
5. Update session metrics and context
6. Return structured response with metadata

### 4. **intent_pipeline.py** - Intent Classification System
**Purpose**: AI-powered intent classification and entity extraction

**Components**:
- `IntentPipeline`: Main classification orchestrator
- Rule-based pattern matching for common intents
- LLM fallback for complex classification
- Entity extraction (names, numbers, locations)
- Confidence scoring and threshold management

**Supported Intents**:
- `no_water_supply`: Water outage reporting
- `billing_inquiry`: Account and bill questions
- `complaint_status`: Ticket tracking
- `new_connection`: Service applications
- `office_info`: Branch locations and hours
- `escalation`: Human agent requests
- `emergency`: Urgent situation detection

### 5. **tools.py** - Tool Execution Layer
**Purpose**: Implement specific actions and external system integrations

**Available Tools**:
```python
# Complaint Management
log_complaint(name, area, issue) -> Create complaint ticket
get_complaint_status(ticket_id) -> Check ticket status
get_complaint_details(ticket_id) -> Full complaint information

# Billing Services
get_bill(account_number) -> Retrieve billing information
get_payment_methods() -> Available payment options
get_payment_status(payment_id) -> Payment tracking

# Customer Service
get_office_info(branch_or_area) -> Branch locations and hours
get_new_connection_info() -> Connection application process
escalate_to_human(reason, details) -> Human handoff

# Utility Services
check_area_outage(area) -> Current outage status
get_service_interruptions() -> Scheduled maintenance info
```

### 6. **storage.py** - Database Layer
**Purpose**: Persistent data storage with comprehensive schema

**Database Tables**:
```sql
-- Core Tables
water_complaints          -- Customer complaints and tickets
escalations               -- Human escalation records
session_context           -- Conversation state management
conversation_history      -- Full chat history with PII protection

-- Mock Service Data
mock_customers           -- Customer account information
mock_accounts            -- Billing account details
mock_bills              -- Invoice and payment data
mock_payments           -- Payment transaction records
mock_outages            -- Service outage information
mock_offices             -- Branch location data

-- Evaluation & Feedback
session_metrics          -- Performance and usage analytics
user_feedback           -- Customer satisfaction data
admin_resolution         -- Case resolution tracking
```

**Key Functions**:
- Database initialization and schema management
- CRUD operations for all data types
- Search and filtering capabilities
- Data migration and seeding support

### 7. **metrics_collector.py** - Performance Monitoring
**Purpose**: Real-time system performance and user behavior tracking

**Metrics Collected**:
- Response times and latency
- Intent classification accuracy
- Conversation completion rates
- User satisfaction scores
- System error rates
- Escalation frequency

**Data Classes**:
- `SessionMetrics`: Per-conversation performance data
- `TurnMetrics`: Individual message interaction metrics
- Real-time collection and storage

### 8. **emergency_detector.py** - Emergency Detection
**Purpose**: Identify urgent situations requiring immediate attention

**Emergency Indicators**:
- Medical emergency keywords
- Safety and security threats
- Urgent service disruptions
- Life-threatening situations

**Response Actions**:
- Immediate escalation to human agents
- Emergency contact information
- Priority routing in admin dashboard
- Alert notifications

### 9. **evaluation.py** - Quality Assessment
**Purpose**: System performance evaluation and quality metrics

**Evaluation Components**:
- Conversation quality scoring
- Intent accuracy measurement
- Response relevance assessment
- User satisfaction analysis

## Data Flow Architecture

### Customer Chat Flow

```
User Message → Frontend (React)
       ↓
HTTP POST /chat (JSON)
       ↓
Request Validation (main.py)
       ↓
Intent Classification (intent_pipeline.py)
       ↓
Conversation Orchestration (orchestrator.py)
       ↓
Tool Execution (tools.py)
       ↓
Database Operations (storage.py)
       ↓
Response Generation + Metrics Collection
       ↓
JSON Response → Frontend Display
```

### Admin Dashboard Flow

```
Admin Login → POST /auth/login
       ↓
Token Generation (auth.py)
       ↓
Role-Based Permission Check
       ↓
Access Grant/Deny
       ↓
Audit Logging
       ↓
Authenticated Requests → Admin Endpoints
       ↓
PII Redaction (auth.py) → Data Access (storage.py)
       ↓
Dashboard Display → Admin UI (static/admin.html)
```

### Metrics Collection Flow

```
User Interaction → Conversation Processing
       ↓
Real-time Metrics (metrics_collector.py)
       ↓
Session Storage (storage.py)
       ↓
Dashboard Analytics → Admin Interface
```

## Security Architecture

### Authentication Flow
```
Login Request → Credential Validation
       ↓
Token Generation (JWT-like)
       ↓
Role-Based Permission Check
       ↓
Access Grant/Deny
       ↓
Audit Logging
```

### Data Protection Layers
```
User Request → Input Validation
       ↓
PII Detection → Role-Based Redaction
       ↓
Database Access (Parameterized Queries)
       ↓
Response Filtering → Secure Output
```

## Technology Stack

### Backend Technologies
- **FastAPI**: Modern Python web framework
- **SQLite**: Lightweight database for development
- **Groq API**: LLM for natural language processing
- **Pydantic**: Data validation and serialization
- **Uvicorn**: ASGI server for production

### Frontend Technologies
- **React**: Customer chat interface
- **Vite**: Build tool and development server
- **Tailwind CSS**: Utility-first styling
- **HTML/JS**: Admin dashboard

### Development Tools
- **Python 3.9+**: Core runtime environment
- **pytest**: Testing framework
- **Logging**: Structured JSON logging system
- **Environment Variables**: Configuration management

## Performance Considerations

### Scalability
- **Database**: SQLite suitable for <10,000 records
- **Concurrent Users**: Optimized for <100 simultaneous
- **Memory Usage**: In-memory session storage
- **API Rate Limits**: Configurable throttling

### Optimization Strategies
- **Intent Caching**: Store classification results
- **Session Management**: Efficient context tracking
- **Database Indexing**: Optimized query performance
- **Response Caching**: Reduce LLM API calls

## Integration Points

### External Services
- **Groq LLM**: Natural language processing
- **Future WhatsApp**: Business API integration
- **Payment Gateways**: Billing system integration
- **Email Services**: Notification system

### Internal Integrations
- **Metrics Collection**: Real-time performance data
- **Audit System**: Security event tracking
- **Evaluation Engine**: Quality assessment
- **Admin Dashboard**: Management interface

## Future WhatsApp Integration Architecture

### Planned Integration
```
WhatsApp Business API → Webhook Endpoint
       ↓
Message Processing → Current Orchestrator
       ↓
WhatsApp Response → Formatted Output
       ↓
Media Support → File Handling
```

### Integration Components
- **Webhook Server**: WhatsApp message reception
- **Message Adapter**: WhatsApp format conversion
- **Media Handler**: Image and document processing
- **Interactive Buttons**: WhatsApp UI elements
- **WhatsApp Pay**: Payment processing integration

## Deployment Architecture

### Development Environment
```
Frontend Dev Server (Vite) :3000
       ↓
Backend Dev Server (Uvicorn) :8000
       ↓
SQLite Database (local file)
```

### Production Environment
```
Load Balancer → Multiple App Instances
       ↓
Application Servers (Gunicorn + Uvicorn)
       ↓
PostgreSQL Database (Cloud)
       ↓
Redis Cache (Session Storage)
```

## Monitoring & Observability

### Logging Strategy
- **Structured JSON Logs**: Consistent format across all modules
- **Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Sensitive Data Redaction**: Automatic PII filtering
- **Log Rotation**: Prevent disk overflow
- **Error Tracking**: Separate error log files

### Metrics Dashboard
- **Real-time Monitoring**: Live performance data
- **Health Checks**: System status endpoints
- **Alert System**: Error threshold notifications
- **User Analytics**: Interaction patterns and satisfaction

---

**This architecture supports enterprise-grade deployment while maintaining simplicity and clarity for development and scaling.**
