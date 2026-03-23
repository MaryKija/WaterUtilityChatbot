## System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Interface                          │
│                    (HTML/CSS/JavaScript)                        │
│                   WhatsApp-like Chat UI                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                    HTTP POST /chat
                             │
                             ▼
┌───────────────────────────────────────────────────────────���─────┐
│                      FastAPI Backend                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  main.py: Request Handler & Validation                  │  │
│  │  - Receives chat requests                               │  │
│  │  - Validates input (phone, message)                     │  │
│  │  - Routes to intent classification                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                   │
│                             ▼                                   │
│  ┌─────────────────────────────────────────────────────────���┐  │
│  │  Intent Classification (LLM-First)                      │  │
│  │  - Primary: OpenRouter API (LLM)                        │  │
│  ���  - Fallback 1: Local keyword detection                  │  │
│  │  - Fallback 2: Ollama/DeepSeek                          │  │
│  │  - Returns: intent, confidence, entities               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                   │
│                             ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  agent.py: Intent Router & Flow Manager                 │  │
│  │  - Routes to appropriate handler                        │  │
│  │  - Manages multi-turn conversation state                │  │
│  │  - Extracts entities from user input                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                   │
│        ┌─────────────────���──┼────────────────────┐              │
│        ▼                    ▼                    ▼              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  tools.py    │  │  storage.py  │  │  validation  │         │
│  │  (Actions)   │  │  (Database)  │  │  (Sanitize)  │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                             │
        ┌────────────────────┼��───────────────────┐
        ▼                    ▼                    ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ OpenRouter   │  │   SQLite     │  │   Logging    │
│   LLM API    │  │   Database   │  │   System     │
└──────────────┘  └──────────────┘  └──────────────┘
```

## Module Responsibilities

### 1. **main.py** - Request Handler
**Purpose**: Entry point for all chat requests

**Key Functions**:
- `chat(data: ChatRequest)`: Main endpoint
- `classify_intent(message: str)`: LLM-based intent classification
- `_normalize_intent_result()`: Standardize intent output
- `_extract_last_json_object()`: Parse LLM JSON responses

**Flow**:
1. Receive chat request (phone, message)
2. Validate input
3. Classify intent using LLM
4. Route to agent
5. Return response with metadata

### 2. **agent.py** - Intent Router & Flow Manager
**Purpose**: Route intents to appropriate handlers and manage conversation state

**Key Functions**:
- `run_agent()`: Main routing logic
- `_fill_complaint_fields_from_message()`: Extract complaint details
- `_decline_out_of_scope()`: Handle unknown intents

**Conversation Flows**:
1. **Complaint Flow**: Collect name, area, issue → log complaint
2. **Billing Flow**: Extract account number → retrieve bill
3. **Follow-up Flow**: Extract ticket ID → get status
4. **FAQ Flow**: Provide help information
5. **Escalation Flow**: Transfer to human agent

### 3. **tools.py** - Tool Implementations
**Purpose**: Implement specific actions/tools

**Tools**:
- `log_complaint()`: Create complaint ticket
- `get_complaint_status()`: Retrieve complaint status
- `get_bill()`: Fetch billing information
- `get_payment_methods()`: Payment options
- `get_office_info()`: Office locations
- `escalate_to_human()`: Escalation message

### 4. **storage.py** - Database Layer
**Purpose**: Persistent data storage

**Functions**:
- `init_db()`: Initialize SQLite schema
- `create_complaint()`: Insert complaint
- `get_complaint()`: Retrieve complaint by ID
- `set_complaint_status()`: Update complaint status

**Schema**:
```sql
CREATE TABLE water_complaints (
    ticket_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    area TEXT NOT NULL,
    issue TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
)
```

### 5. **validation.py** - Input Validation
**Purpose**: Validate and sanitize user input

**Functions**:
- `validate_phone_number()`: E.164 format validation
- `validate_message()`: Length and content checks
- `validate_account_number()`: Account format validation
- `validate_ticket_id()`: Ticket format validation
- `sanitize_input()`: Remove malicious content
- `extract_account_number()`: Flexible account extraction
- `extract_ticket_id()`: Flexible ticket extraction

### 6. **config.py** - Configuration Management
**Purpose**: Centralized configuration

**Features**:
- Load environment variables
- Validate required settings
- Provide configuration object
- Generate API headers

### 7. **logger.py** - Structured Logging
**Purpose**: Centralized, structured logging

**Features**:
- JSON-formatted logs
- Sensitive data filtering
- Rotating file handlers
- Separate error logs
- Console output for development

### 8. **intents.py** - Fallback Intent Detection
**Purpose**: Keyword-based fallback for intent classification

**Function**:
- `detect_intent()`: Keyword matching for common intents

## Data Flow

### Complaint Reporting Flow

```
User Input: "No water in my area"
    ↓
[Validation] Phone & message validated
    ↓
[Intent Classification] LLM → "no_water_supply" (0.95 confidence)
    ↓
[Agent Routing] Complaint intent detected
    ↓
[Session Management] Initialize complaint flow
    ↓
[Entity Extraction] Extract name, area, issue
    ↓
[Validation] Check all required fields present
    ↓
[Tool Execution] log_complaint() → create ticket
    ↓
[Response] Return ticket ID and confirmation
    ↓
[Logging] Log action with metadata
    ↓
User Output: "✅ Complaint Logged Successfully
              Reference Number: WC-A1B2C3"
```

### Billing Inquiry Flow

```
User Input: "Check my bill"
    ↓
[Intent Classification] LLM → "billing_inquiry" (0.90 confidence)
    ↓
[Agent Routing] Billing intent detected
    ↓
[Session Management] Initialize billing flow
    ↓
[Entity Extraction] Extract account number from message
    ↓
[Validation] Validate account number format
    ↓
[Tool Execution] get_bill(account_number)
    ↓
[Response] Return billing information
    ↓
User Output: "💳 Billing Information
              Account: 123456
              Amount Due: K245.60"
```

## Intent Classification Strategy

### LLM-First Design

The system uses a **LLM-first** approach rather than keyword matching:

**Why?**
- More natural language understanding
- Handles variations and typos
- Extracts entities automatically
- Scales to new intents easily
- Provides confidence scores

**Process**:
1. **Primary**: Send to OpenRouter LLM
2. **Fallback 1**: Local keyword detection (intents.py)
3. **Fallback 2**: Ollama/DeepSeek (if available)
4. **Final**: Default to out_of_scope

**Confidence Thresholds**:
- High (0.9-1.0): Trust LLM classification
- Medium (0.5-0.9): May need clarification
- Low (<0.5): Likely out of scope

## Session Management

### Session State Structure

```python
session = {
    "flow": "complaint",              # Current flow type
    "complaint_intent": "no_water_supply",
    "name": "John",                   # Extracted fields
    "area": "Makululu",
    "issue": "No water supply",
    "account_number": "123456",       # For billing
    "ticket_id": "WC-A1B2C3",        # For follow-ups
    "billing_intent": "billing_inquiry"
}
```

### Flow Types

1. **complaint**: Collecting complaint details
2. **billing**: Collecting account information
3. **followup**: Collecting ticket ID
4. **None**: Single-turn interactions

## Error Handling & Fallbacks

### Fallback Chain

```
Try OpenRouter LLM
    ↓ (fails)
Try Local Keyword Detection
    ↓ (fails)
Try Ollama/DeepSeek
    ↓ (fails)
Return Default (out_of_scope)
```

### Error Scenarios

| Scenario | Handling |
|----------|----------|
| API timeout | Retry with fallback |
| Invalid JSON | Parse last {...} object |
| Missing fields | Prompt user for input |
| Invalid phone | Normalize to E.164 |
| Injection attempt | Sanitize input |

## Security Considerations

### Input Validation
- Phone number format validation
- Message length limits (1-1000 chars)
- Account number format validation
- Ticket ID format validation

### Data Protection
- Sensitive data redacted in logs
- API keys in environment variables
- SQL injection prevention (parameterized queries)
- CORS configuration

### Logging Security
- Automatic redaction of: API keys, tokens, passwords, phone numbers, account numbers
- Separate error logs for debugging
- Rotating file handlers to prevent disk overflow

## Performance Considerations

### Optimization Strategies

1. **Greeting Short-Circuit**: Greetings handled locally (no LLM call)
2. **Session Caching**: Store extracted entities in session
3. **Fallback Efficiency**: Try fastest methods first
4. **Timeout Management**: 30s timeout for LLM calls

### Scalability

- **In-Memory Sessions**: Works for demo; use Redis for production
- **SQLite Database**: Suitable for small-medium scale
- **Stateless API**: Can be horizontally scaled

## Testing Strategy

### Unit Tests
- Input validation functions
- Entity extraction
- Intent normalization
- Tool implementations

### Integration Tests
- Full conversation flows
- Multi-turn interactions
- Error scenarios
- Fallback mechanisms

### Manual Testing
- `test_agent_flow.py`: Multi-turn conversation
- `test_issue_fix.py`: Specific issue scenarios
- `/test_llm` endpoint: API connectivity

## Future Enhancements

### Short-term (Phase 2-3)
- [ ] Database for billing accounts
- [ ] Database for office locations
- [ ] Confidence threshold enforcement
- [ ] Unit test coverage

### Medium-term (Phase 4)
- [ ] Redis for session storage
- [ ] Rate limiting implementation
- [ ] API versioning
- [ ] Responsive frontend

### Long-term (Phase 5)
- [ ] Multi-language support
- [ ] Sentiment analysis
- [ ] Analytics dashboard
- [ ] Advanced NLU models

## Deployment Considerations

### Development
```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

### Production
- Use production ASGI server (Gunicorn + Uvicorn)
- Enable HTTPS
- Use PostgreSQL instead of SQLite
- Implement rate limiting
- Set up monitoring and alerting
- Use environment-specific configs

## Monitoring & Observability

### Logging
- Structured JSON logs in `logs/app.log`
- Error logs in `logs/errors.log`
- Automatic log rotation (10MB per file, 5 backups)

### Metrics to Track
- Intent classification accuracy
- Response time per request
- Error rate by type
- User satisfaction (future)

### Debugging
- Enable DEBUG mode in .env
- Check logs for detailed traces
- Use `/test_llm` endpoint for API testing
- Review session state in logs

---

**This architecture supports the capstone project's goals of demonstrating agentic AI principles while maintaining simplicity and clarity.**
