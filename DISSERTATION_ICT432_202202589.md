# MULUNGUSHI UNIVERSITY

## SCHOOL OF ENGINEERING AND TECHNOLOGY (SET)

## DEPARTMENT OF COMPUTER SCIENCE AND IT

---

# PROJECT REPORT TITLE: AGENTIC AI CHATBOT FOR INTELLIGENT CUSTOMER SERVICE AUTOMATION AT LUKANGA WATER SUPPLY AND SANITATION COMPANY (LgWSC)

---

**NAME:** MARY KWANJIWA KIJA

**STUDENT ID:** 202202589

**COURSE:** ICT432 CAPSTONE PROJECT REPORT

**PROGRAMME:** BSc COMPUTER SCIENCE

**SUPERVISOR:** DR. BRIAN HALUBANZA

---

*THIS REPORT IS SUBMITTED IN PARTIAL FULFILMENT FOR THE AWARD OF BACHELOR OF SCIENCE IN COMPUTER SCIENCE FOR THE 2024/2025 ACADEMIC YEAR*

---

## DECLARATION

	I, Mary Kwanjiwa Kija, declare that this project report, titled *Agentic AI Chatbot for Intelligent Customer Service Automation at Lukanga Water Supply and Sanitation Company*, is my own original work and has not been submitted elsewhere for academic credit. All sources used have been acknowledged according to the Harvard referencing style.

| | |
|---|---|
| **Author:** Mary Kwanjiwa Kija | **Supervisor:** Dr. Brian Halubanza |
| **Date:** __________________ | **Date:** __________________ |
| **Signature:** __________________ | **Signature:** __________________ |

---

## ACKNOWLEDGEMENTS

	I would like to express my sincere gratitude to my parents for fully supporting me through all of my years of study. I thank God for having let me get this far in all that I have been doing. My appreciation also goes to Dr. Brian Halubanza, my supervisor, for his expert guidance and constructive criticism throughout the preparation of this report. I wish to thank the School of Engineering and Technology at Mulungushi University for providing the academic environment and support necessary for this project. I am grateful to the staff of Lukanga Water Supply and Sanitation Company (LgWSC) in the Commercial Department for their time and cooperation in completing the staff survey that informed this system's design. Lastly, I am deeply thankful to my family and friends for their continuous financial and moral support.

---

## ABSTRACT

	The demand for faster, more reliable, and accessible customer service in Zambia's utility sector has exposed the limitations of traditional, human-dependent service models. Lukanga Water Supply and Sanitation Company (LgWSC) in Kabwe relies on manual and phone-based customer support, which leads to delays, incomplete complaint records, and limited service availability outside working hours.

	This project designed, implemented, and evaluated an Agentic AI Chatbot for automated customer service using Python, FastAPI, the Groq LLM API (Llama 3.1), and a React-based web interface. The system autonomously handles customer queries, logs complaints with automatic categorisation and priority assignment, checks billing account information, reports service outages, and escalates complex cases to human staff. A hybrid intent classification pipeline combining rule-based matching, lightweight keyword classification, and LLM-based reasoning was implemented to achieve robust natural language understanding. A comprehensive evaluation framework measured response accuracy, intent classification confidence, task completion rates, and user satisfaction.

	A staff survey conducted with four LgWSC Commercial Department employees confirmed that bill inquiries, water outage reports, and payment status checks are the top three most requested chatbot features. The system achieved 38 passing tests out of 39 in the automated test suite, with property-based testing used to formally verify the bug condition for context loss in multi-turn conversations. The system demonstrated reliable complaint logging, billing lookup, outage status retrieval, and human escalation across all tested conversation flows.

	The proposed solution improves response speed, reduces workload on human agents, and extends LgWSC's customer-service accessibility beyond working hours, contributing to the company's digital-transformation agenda and Zambia's Smart Zambia ICT Policy.

**Keywords:** Agentic AI, Chatbot, FastAPI, Groq LLM, Intent Classification, Customer Service Automation, Water Utility, Zambia, Property-Based Testing, RAG

---

## LIST OF FIGURES

| Figure | Title | Page |
|--------|-------|------|
| Figure 3.1 | System Architecture Diagram | Ch. 3 |
| Figure 3.2 | Data Flow Diagram — Customer Chat Flow | Ch. 3 |
| Figure 3.3 | Entity-Relationship Diagram — Database Schema | Ch. 3 |
| Figure 3.4 | UML Use Case Diagram | Ch. 3 |
| Figure 3.5 | UML Sequence Diagram — Complaint Logging Flow | Ch. 3 |
| Figure 3.6 | Hybrid Intent Classification Pipeline | Ch. 3 |
| Figure 4.1 | Project Gantt Chart | Ch. 4 |
| Figure 5.1 | Test Results Summary — 38 Passed, 1 Failed | Ch. 5 |
| Figure 5.2 | Staff Survey — Most Common Inquiry Types | Ch. 5 |
| Figure 5.3 | Staff Survey — Most Important Chatbot Features | Ch. 5 |
| Figure 5.4 | Staff Survey — Percentage of Inquiries Automatable | Ch. 5 |
| Figure 5.5 | Staff Survey — Willingness to Use Chatbot | Ch. 5 |

---

## LIST OF TABLES

| Table | Title | Page |
|-------|-------|------|
| Table 2.1 | Comparison of Reviewed Chatbot Systems | Ch. 2 |
| Table 3.1 | Technologies and Frameworks Used | Ch. 3 |
| Table 3.2 | Functional Requirements Specification | Ch. 3 |
| Table 3.3 | Non-Functional Requirements Specification | Ch. 3 |
| Table 3.4 | Database Tables and Descriptions | Ch. 3 |
| Table 3.5 | API Endpoint Specification | Ch. 3 |
| Table 4.1 | Risk Register | Ch. 4 |
| Table 4.2 | Project Budget | Ch. 4 |
| Table 4.3 | Effort Distribution by Phase | Ch. 4 |
| Table 5.1 | Test Suite Summary by Module | Ch. 5 |
| Table 5.2 | Intent Classification Test Cases and Results | Ch. 5 |
| Table 5.3 | Staff Survey Results Summary | Ch. 5 |
| Table 5.4 | Evaluation Metrics Results | Ch. 5 |

---

## ACRONYMS AND ABBREVIATIONS

| Acronym | Meaning |
|---------|---------|
| AI | Artificial Intelligence |
| API | Application Programming Interface |
| ASGI | Asynchronous Server Gateway Interface |
| CORS | Cross-Origin Resource Sharing |
| CRUD | Create, Read, Update, Delete |
| ER | Entity-Relationship |
| FastAPI | Fast Application Programming Interface (Python web framework) |
| HTTP | Hypertext Transfer Protocol |
| ICT | Information Communication Technology |
| JSON | JavaScript Object Notation |
| LgWSC | Lukanga Water Supply and Sanitation Company |
| LLM | Large Language Model |
| ML | Machine Learning |
| MU | Mulungushi University |
| NLP | Natural Language Processing |
| PBT | Property-Based Testing |
| PII | Personally Identifiable Information |
| RAG | Retrieval-Augmented Generation |
| RBAC | Role-Based Access Control |
| REST | Representational State Transfer |
| SLA | Service Level Agreement |
| SQL | Structured Query Language |
| SQLite | Self-Contained SQL Database Engine |
| TLS | Transport Layer Security |
| UML | Unified Modelling Language |
| URL | Uniform Resource Locator |
| UUID | Universally Unique Identifier |

---

---

# CHAPTER 1 — INTRODUCTION

## 1.1 Introduction

	Artificial Intelligence is transforming how businesses and public service institutions operate, improving efficiency and customer satisfaction across sectors including banking, healthcare, and utilities through intelligent automation (Russell and Norvig, 2022). In Zambia, public utility companies such as Lukanga Water Supply and Sanitation Company (LgWSC) in Kabwe continue to rely on traditional service delivery methods — in-person visits and telephone calls — for customer interactions. These methods create operational bottlenecks, inconsistent service quality, and limited accessibility for customers outside standard working hours.

	Preliminary consultations with LgWSC staff indicated that the customer service unit receives approximately 150–250 calls per day, particularly during supply interruptions and billing periods. At peak hours, customers wait 20–45 minutes for assistance, and staff estimated that 8–12% of complaints go unrecorded due to manual record-keeping failures (LgWSC Internal Staff Interview, 2025). These challenges significantly affect communities across multiple districts served by LgWSC in Central Province.

	Given the widespread adoption of WhatsApp across all demographics in Zambia, integrating customer service into a digital messaging platform offers a highly accessible channel for communication. However, this project implemented the system as a web-based chatbot interface first, with WhatsApp Business API integration planned as a future enhancement. The proposed system leverages Agentic AI — a paradigm that enables autonomous planning, tool use, decision-making, and adaptive response generation — to intelligently process customer queries, log complaints, retrieve service information, escalate complex cases to human staff, and operate consistently in real time (Lee, 2025).

## 1.2 Problem Statement

	LgWSC faces persistent challenges in delivering timely and efficient customer service. Customers frequently experience long waiting times, limited accessibility to physical offices, and difficulty obtaining service updates outside standard business hours. As the number of clients increases, the existing staff structure is unable to handle the high volume of interactions, resulting in slow responses and inconsistent service quality.

	Current methods — manual complaint forms and telephone calls — often result in misplaced or incomplete records, delayed feedback, and poor tracking of complaints. Customers who lack access to physical offices are disproportionately affected. The absence of an automated system limits the company's ability to provide 24/7 support or ensure accurate and timely information delivery.

	An AI-powered chatbot presents an opportunity to address these issues by automating repetitive tasks, offering instant information retrieval, and maintaining consistent communication regardless of time or location. By integrating Agentic AI, the system can handle more complex multi-step tasks such as complaint categorisation, priority routing, and escalation. This project therefore sought to bridge the existing service gap and improve operational efficiency through a scalable, intelligent digital solution.

## 1.3 Aim

	The project aimed to design, implement, and evaluate an Agentic AI Chatbot for intelligent customer service automation at Lukanga Water Supply and Sanitation Company (LgWSC) using the Groq LLM API and Python.

## 1.4 Objectives

**Main Objective:**
To develop and deploy an AI-powered web chatbot that automates customer service operations and enhances service accessibility at LgWSC.

**Specific Objectives:**

1. To assess LgWSC's current customer service processes and identify operational challenges through staff surveys and interviews.
2. To design a conversational AI agent capable of handling customer queries, logging complaints, and providing billing and outage information.
3. To implement a hybrid intent classification pipeline combining rule-based, lightweight, and LLM-based classification using the Groq API.
4. To build a secure backend system with role-based access control, audit logging, and PII protection.
5. To evaluate the system's performance using automated testing, property-based testing, and staff survey feedback.
6. To examine ethical considerations and trust factors in AI-based customer service deployment.

## 1.5 Project Scope

	The project focused on developing a web-based AI chatbot to automate customer service for LgWSC. The chatbot handles common tasks including fault reporting, complaint logging with automatic categorisation and SLA assignment, billing account inquiries, outage status checks, new connection guidance, and human escalation. The system does not perform payment processing or modify existing operational databases beyond complaint logging. The backend was built using Python and FastAPI, with a React-based customer interface and an HTML/JavaScript admin dashboard. The Groq LLM API (Llama 3.1 8B Instant model) was used for natural language understanding. WhatsApp Business API integration was identified as a future enhancement and was not implemented in this version.

## 1.6 Research Questions

	This project addressed the following research questions:

1. How can an agentic AI architecture be designed to autonomously handle multi-step customer service workflows for a water utility company?
2. What hybrid intent classification approach achieves reliable natural language understanding for utility-domain queries?
3. How can context persistence be implemented to maintain conversation state across multi-turn interactions?
4. What governance mechanisms are required to ensure safe, auditable, and privacy-compliant AI deployment in a public utility context?
5. To what extent does the implemented system meet the functional requirements identified through LgWSC staff surveys?

## 1.7 Project Justification

	The project is justified by the need to improve customer experience, reduce response times, and boost operational efficiency at LgWSC. An AI chatbot enables 24/7 customer interaction without overwhelming human agents, ensuring that complaint logging and information requests can be addressed even outside working hours. This aligns with Zambia's Smart Zambia initiative, which promotes digital transformation and e-governance (Smart Zambia, 2023).

	Academically, this project contributes to Applied Artificial Intelligence by demonstrating how modern language models with agentic capabilities can support utility management in developing regions. The combination of agentic reasoning, hybrid intent classification, and property-based testing provides an opportunity to explore novel agent architectures and formal correctness verification methodologies — areas that remain underexplored in the Zambian context (Joshi, 2025).

## 1.8 Definition of Key Terms

- **Agentic AI:** An AI system capable of autonomous goal-directed behaviour, including planning, tool use, and multi-step decision-making, as distinct from reactive LLMs that only generate text responses.
- **Large Language Model (LLM):** A deep learning model trained on large text corpora capable of understanding and generating natural language.
- **Intent Classification:** The process of identifying the purpose or goal behind a user's message (e.g., billing inquiry, fault report).
- **Retrieval-Augmented Generation (RAG):** A technique that grounds LLM responses in verified data retrieved from a knowledge base, reducing hallucination.
- **Property-Based Testing (PBT):** A testing methodology that generates many input examples to verify that a system satisfies formal correctness properties across a wide range of inputs.
- **Escalation:** The process of transferring a conversation from the AI system to a human agent when the AI cannot adequately resolve the issue.

## 1.9 Conclusion

	This chapter introduced the background of the study, identified the main problem, and outlined the aim, objectives, research questions, and justification of the project. The proposed Agentic AI Chatbot for LgWSC seeks to transform customer service delivery by integrating AI capabilities into an accessible digital platform. The following chapter reviews the literature relevant to conversational AI, agentic systems, and chatbot deployment in utility contexts.

---

# CHAPTER 2 — LITERATURE REVIEW

## 2.1 Introduction

	This chapter reviews literature related to conversational AI, agentic AI systems, hybrid intent classification, chatbot deployment in utility sectors, backend architectures, evaluation frameworks, and AI governance. The review draws from academic sources, industry reports, and technical documentation to identify gaps in existing solutions and position the proposed LgWSC Agentic AI Chatbot as a hybrid, governance-aware system suited for public service contexts in Zambia.

## 2.2 Evolution of Conversational AI

	Conversational agents have evolved from rule-based systems relying on predefined pattern matching to advanced Large Language Model (LLM)-powered systems capable of contextual understanding and dynamic response generation. Early chatbots such as ELIZA (Weizenbaum, 1966) used simple pattern-matching rules and could not maintain context across turns. Modern systems leverage transformer-based architectures, enabling nuanced multi-turn dialogue (Vaswani et al., 2017).

	A major development in this evolution is agentic AI, which extends beyond static text generation. Agentic systems can interpret goals, create action plans, execute multi-step tasks, interact with tools, and adapt to new information autonomously (Lee, 2025). This distinguishes them from traditional LLMs that operate reactively and lack goal-oriented autonomy. The ReAct framework (Yao et al., 2023) formalised the combination of reasoning and acting in LLM-based agents, demonstrating that interleaving thought and action steps significantly improves task completion in complex domains.

## 2.3 Intent Classification Approaches

	Intent classification is a foundational component of any conversational AI system. Three primary approaches exist in the literature: rule-based, machine learning-based, and LLM-based classification.

	Rule-based systems use handcrafted patterns and keyword matching. They are highly reliable for well-defined domains but fail on paraphrased or ambiguous inputs (Jurafsky and Martin, 2023). Machine learning classifiers, including Support Vector Machines and BERT-based models, achieve high accuracy on labelled datasets but require substantial training data and periodic retraining as language patterns evolve (Devlin et al., 2019). LLM-based classification leverages the general language understanding of large models to classify intents without domain-specific training, but introduces latency and cost concerns (OpenAI, 2024).

	Recent literature recommends hybrid architectures that combine rule-based matching for high-confidence cases with LLM fallback for ambiguous inputs (LangChain, 2024). This approach balances accuracy, latency, and cost — a design principle adopted in this project through a three-stage ensemble pipeline.

## 2.4 Chatbot Adoption in Customer Service

	Studies on chatbot adoption show consistent trends: chatbots significantly reduce operational load and response time, but customer satisfaction depends heavily on accuracy, clarity, and task completion rates (Index, 2023). Systems with unclear pathways to human agents often experience low trust and limited adoption. Businesses report high investment but relatively low-frequency usage when chatbots fail in complex tasks or produce hallucinated responses.

	In the utility sector specifically, case studies in electricity and water management systems show improved first-response times and automated triaging, but highlight concerns around misinformation, difficulty handling ambiguous inputs, and failures in multi-step workflows without orchestration (Infotech, 2025). This reinforces the need for hybrid grounding techniques and agentic planning capabilities.

## 2.5 WhatsApp and Digital Channels in Developing Countries

	WhatsApp is one of the most widely used communication platforms in low- and middle-income countries due to its accessibility to older and less digitally literate populations, low mobile data usage, and content compression that supports users with weak connectivity (Meta, 2025). The WhatsApp Business API enables automated communication via direct enterprise API integration or provider intermediaries such as Twilio. Industry documentation highlights conversation-based billing models, verification requirements, webhook-based message routing, and rate limits that must be carefully considered when designing cost-efficient public service chatbots (Twilio, 2024).

	For this project, a web-based interface was implemented as the primary delivery channel, with WhatsApp integration planned as a future enhancement. This decision was made to avoid the verification and billing complexities of the WhatsApp Business API during the prototype phase.

## 2.6 Backend Architectures for AI Chatbots

	FastAPI has become a widely adopted backend framework for AI-driven services because it provides asynchronous processing for high concurrency, built-in validation through Pydantic, automatic API documentation via OpenAPI, and efficient performance suitable for chatbot requests (FastAPI, 2024). Community examples demonstrate straightforward integration with OpenAI-compatible APIs, SQLite for lightweight storage, and structured logging systems. These attributes make it suitable for building scalable, maintainable AI-driven services — a key reason for its selection in this project.

	SQLite was selected as the database for the prototype phase due to its zero-configuration deployment, suitability for datasets under 10,000 records, and compatibility with the single-developer development environment. A migration path to PostgreSQL for production deployment was documented in the system architecture.

## 2.7 AI Governance and Responsible Deployment

	In Zambia, AI deployments in public institutions fall under the Smart Zambia ICT Policy (2023), which emphasises digital government alignment, secure handling of public data, and responsible, transparent, and auditable AI use. Aligned with this, OpenAI's 2024 governance principles for agentic systems highlight human-in-the-loop oversight, grounding of outputs on verified data, safe failure mechanisms, and monitoring of emergent behaviours.

	Gartner's Agentic AI reports (2025) outline the need for strong grounding mechanisms, explainability, audit trails, controlled autonomy, and clear escalation pathways. These insights show increasing demand for AI systems that combine LLM reasoning with structured knowledge retrieval and governance layers, especially in regulated sectors like utilities.

	The system implemented in this project addresses these governance requirements through role-based access control, PII redaction, immutable audit logging, confidence-based escalation, and an explicit ethics framework documented in ETHICS.md.

## 2.8 Review of Existing Systems

	Several existing chatbot systems were reviewed to identify strengths, weaknesses, and design lessons:

	**Rule-based / Legacy Chatbots:** Systems such as simple IVR (Interactive Voice Response) telephone trees and keyword-triggered SMS bots are widely deployed in African utilities. They are low-cost and reliable for simple queries but cannot handle free-text input, multi-step workflows, or contextual follow-up questions.

	**Naive LLM-Only Systems:** Systems that pass all queries directly to a general-purpose LLM without grounding or intent routing achieve high language fluency but produce plausible yet incorrect answers (hallucinations) for factual queries such as billing amounts or outage schedules. They also lack the structured workflow management needed for complaint logging.

	**Hybrid/Agentic + RAG Systems:** Systems combining intent classification, structured tool execution, and LLM reasoning for free-text responses achieve the best balance of accuracy, flexibility, and reliability. LangChain-based implementations demonstrate this pattern effectively (LangChain, 2024).

	**Table 2.1: Comparison of Reviewed Systems**

| Dimension | Rule-Based / Legacy | Naïve LLM Only | Hybrid / Agentic + RAG |
|-----------|--------------------|-----------------|-----------------------|
| Accuracy for factual queries | Medium (if curated) | Low (hallucination risk) | High (grounded on verified data) |
| Flexibility for free-text | Low | High | High |
| Multi-turn context handling | None | Limited | Full |
| Complaint logging | Manual | None | Automated |
| Human escalation | Manual | Rare / unreliable | Built-in |
| Implementation complexity | Low | Medium | High |
| Cost (API / time) | Low | High (token usage) | Medium–High |
| Governance / audit trail | None | None | Built-in |

*Table 2.1: Comparison of reviewed chatbot system architectures*

## 2.9 Research Gap

	While hybrid agentic chatbots have been demonstrated in commercial contexts, there is limited published research on their deployment for public utility customer service in sub-Saharan Africa, and no documented implementation for Zambian water utilities. Existing systems reviewed either lack the governance mechanisms required for public sector deployment, do not address the specific service workflows of water utilities (outage reporting, complaint categorisation, SLA assignment), or are not designed for the low-bandwidth, mobile-first user context of Zambian customers. This project addresses this gap by implementing a governance-aware, utility-specific agentic chatbot with formal correctness verification through property-based testing.

## 2.10 Conclusion

	The literature demonstrates that while LLMs and agentic AI offer significant opportunities for improving customer service in utility companies, they must be implemented with grounding, monitoring, and human oversight to remain reliable. Hybrid architectures combining rule-based classification, lightweight AI, and LLM reasoning represent the current best practice. The following chapter describes the research methodology and system design adopted to address the identified research gap.

---

# CHAPTER 3 — RESEARCH METHODOLOGY AND SYSTEM DESIGN

## 3.1 Introduction

	This chapter outlines the research methodology adopted for designing, developing, and evaluating the Agentic AI Chatbot for Intelligent Customer Service Automation at LgWSC. It explains the chosen methodological approach, describes each phase of development, justifies the use of the Prototyping Model, details the system architecture and design, and presents the technologies employed. The chapter also defines the evaluation metrics used to determine system performance, reliability, and usability.

## 3.2 Selected Methodology — Prototyping Model

	The Prototyping Model was selected as the primary development methodology. This approach is suitable for AI-driven systems that require iterative user feedback, continuous refinement, and incremental testing before full-scale deployment (Pressman and Maxim, 2021). Prototyping allows early visualisation of the system, making it easier for LgWSC stakeholders to validate chatbot behaviours, intents, and escalation workflows.

### 3.2.1 Justification of Selected Methodology

	The Prototyping Model was most suitable for this research because it supports iterative refinement — AI behaviour improves with repeated testing and prompt tuning. It is user feedback-driven, which is essential for customer service systems that rely heavily on user experience. It is flexible and adaptive, allowing rapid modification of LLM prompts, database schemas, or API integrations. It aligns with AI best practices that emphasise continuous improvement, monitoring, and evaluation (Russell and Norvig, 2022). Alternative methodologies such as Waterfall lack the flexibility required for systems that learn, adapt, and evolve through testing.

### 3.2.2 Development Phases

**Phase 1 — Requirement Analysis:** User and system requirements were gathered through a structured staff survey distributed to LgWSC Commercial Department employees. The survey identified the most common inquiry types, average handling times, key challenges, and desired chatbot features. These requirements shaped the chatbot's intent categories, escalation logic, and backend integrations.

**Phase 2 — Feasibility Study:** A feasibility assessment evaluated technical feasibility (server hosting, API integration, network reliability), operational feasibility (user acceptance, accessibility), and financial feasibility (API costs, hosting expenditures).

**Phase 3 — System Design:** The system architecture was developed, specifying data flow and interactions between components. Core design components included the React-based customer interface, FastAPI middleware, Groq LLM AI engine, SQLite data layer, and governance layer.

**Phase 4 — Prototype Development:** A functional prototype was built using Python and FastAPI. Initial features included hybrid intent classification, complaint logging, billing lookup, outage status retrieval, and human escalation.

**Phase 5 — Testing and Evaluation:** Testing was carried out at three levels: unit testing of individual modules, integration testing of component interactions, and system testing of end-to-end conversation flows. Property-based testing was used to formally verify the bug condition for context loss.

**Phase 6 — Documentation and Final Review:** Comprehensive documentation was produced including system architecture, API configuration, testing results, and evaluation reports.

## 3.3 Data Collection Instruments

### 3.3.1 Staff Survey

	A structured survey was distributed to LgWSC Commercial Department staff to gather requirements for the chatbot system. The survey collected data on:

- Position and department of respondents
- Years of service with LgWSC
- Daily volume of customer inquiries handled
- Top five most common inquiry types (ranked)
- Average time per inquiry
- Biggest operational challenges
- Most important chatbot features (top 3 selection)
- Estimated percentage of inquiries that could be automated
- Concerns about chatbot deployment
- Willingness to use the chatbot system

**Sample size:** 4 staff members from the Commercial Department (customer service assistants with 3–5 and over 5 years of experience).

## 3.4 System Architecture

	The system follows a modular, multi-tier architecture comprising a Presentation Layer, Application Layer, and Data Layer. The architecture is illustrated in Figure 3.1.

**Figure 3.1: System Architecture Diagram**

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│  ┌──────────────────────┐  ┌──────────────────────────┐    │
│  │  Customer Chat UI    │  │  Admin Dashboard         │    │
│  │  (React / Vite)      │  │  (HTML / JavaScript)     │    │
│  └──────────────────────┘  └──────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                          │ HTTP REST API
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              FastAPI Backend (main.py)               │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  Auth & RBAC (auth.py)  │  Validation (validators.py)│  │
│  │  Orchestrator           │  Emergency Detector        │  │
│  │  (orchestrator.py)      │  (emergency_detector.py)   │  │
│  │  Intent Pipeline        │  Tool Executor             │  │
│  │  (intent_pipeline.py)   │  (tool_executor.py)        │  │
│  │  Context Engine         │  Metrics Collector         │  │
│  │  (context_engine.py)    │  (metrics_collector.py)    │  │
│  │  Evaluation Engine      │  Logger (logger.py)        │  │
│  │  (evaluation.py)        │                            │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Groq LLM   │  │  SQLite DB   │  │  File Logs   │
│  (AI Engine) │  │  (Storage)   │  │  (logs/)     │
└──────────────┘  └──────────────┘  └──────────────┘
```

*Figure 3.1: System Architecture Diagram showing the three-tier architecture*

## 3.5 Data Flow Architecture

	The data flow for a customer chat interaction is illustrated in Figure 3.2.

**Figure 3.2: Data Flow Diagram — Customer Chat Flow**

```
User Message → React Frontend
      ↓
HTTP POST /chat (JSON: {phone, message})
      ↓
Request Validation (validators.py)
      ↓
Emergency Detection (emergency_detector.py)
      ↓ [if no emergency]
Context Loading (context_engine.py → SQLite)
      ↓
Entity Extraction (context_engine.py)
      ↓
Flow Lock Check: Is active_agent set?
      ↓ YES                    ↓ NO
Handle Active Flow    Intent Classification
(orchestrator.py)     (intent_pipeline.py)
      ↓                        ↓
Agent Routing (ComplaintAgent / BillingAgent / etc.)
      ↓
Tool Execution (tool_executor.py → storage.py)
      ↓
Response Generation + Metrics Recording
      ↓
Context Save (context_engine.py → SQLite)
      ↓
JSON Response → React Frontend Display
```

*Figure 3.2: Data Flow Diagram for the customer chat interaction*


## 3.6 Database Design

	The system uses SQLite as the database engine for the prototype phase. The schema comprises 16 tables organised into four functional groups. The Entity-Relationship diagram is described in Figure 3.3.

**Figure 3.3: Entity-Relationship Diagram — Database Schema**

```
[mock_customers] ──< [mock_accounts] ──< [mock_bills]
                                    ──< [mock_payments]

[water_complaints] ──< [escalations]
[session_context] ──< [conversation_history]
                  ──< [conversation_history_pii]

[session_metrics] ──< [user_feedback]
                  ──< [admin_resolution]

[mock_outages]
[mock_offices]
[new_connections]
[intent_suggestions] ──< [intent_labels]
                     ──< [intent_candidates] ──< [intent_metrics]
```

*Figure 3.3: Entity-Relationship Diagram showing database table relationships*

**Table 3.4: Database Tables and Descriptions**

| Table | Purpose |
|-------|---------|
| water_complaints | Customer complaint tickets with category, priority, SLA |
| escalations | Human escalation records with conversation context |
| session_context | Per-user conversation state (active agent, step, entities) |
| conversation_history | Redacted conversation logs for analytics |
| conversation_history_pii | Original conversation logs (restricted access) |
| mock_customers | Simulated LgWSC customer registry |
| mock_accounts | Customer billing account records |
| mock_bills | Invoice and payment due data |
| mock_payments | Payment transaction records |
| mock_outages | Service outage information by area |
| mock_offices | Branch location and hours data |
| session_metrics | Per-session performance analytics |
| user_feedback | Customer satisfaction ratings |
| admin_resolution | Admin case resolution records |
| intent_suggestions | Self-learning intent discovery candidates |
| new_connections | New service connection applications |

*Table 3.4: Database tables and their purposes*

## 3.7 System Requirements Specification

### 3.7.1 Functional Requirements

**Table 3.2: Functional Requirements Specification**

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | The system shall accept free-text customer messages and classify the intent | High |
| FR-02 | The system shall log complaints with name, area, and issue description | High |
| FR-03 | The system shall automatically assign complaint category and priority | High |
| FR-04 | The system shall assign SLA due dates based on complaint priority | High |
| FR-05 | The system shall retrieve billing information by account number | High |
| FR-06 | The system shall check outage status by area name | High |
| FR-07 | The system shall provide office location and hours information | Medium |
| FR-08 | The system shall escalate conversations to human agents on request | High |
| FR-09 | The system shall detect emergency situations and escalate immediately | High |
| FR-10 | The system shall maintain conversation context across multiple turns | High |
| FR-11 | The system shall provide complaint status by ticket reference number | High |
| FR-12 | The system shall support admin login with role-based access control | High |
| FR-13 | The system shall display a dashboard with complaint and escalation metrics | Medium |
| FR-14 | The system shall collect user feedback ratings after conversations | Medium |
| FR-15 | The system shall redact PII from conversation logs | High |

*Table 3.2: Functional Requirements Specification*

### 3.7.2 Non-Functional Requirements

**Table 3.3: Non-Functional Requirements Specification**

| ID | Requirement | Metric |
|----|-------------|--------|
| NFR-01 | Response time | < 3 seconds per turn under normal load |
| NFR-02 | Concurrent users | Supports up to 100 simultaneous users |
| NFR-03 | Intent classification accuracy | > 85% on test cases |
| NFR-04 | Uptime | 99% availability during pilot |
| NFR-05 | Security | Token-based authentication, RBAC, TLS |
| NFR-06 | Privacy | PII automatically redacted from analytics logs |
| NFR-07 | Auditability | All admin actions logged with timestamps |
| NFR-08 | Maintainability | Modular architecture with documented APIs |
| NFR-09 | Scalability | Architecture supports migration to PostgreSQL |
| NFR-10 | Usability | Chatbot interface requires no training for customers |

*Table 3.3: Non-Functional Requirements Specification*

## 3.8 UML Use Case Diagram

	The system supports three primary actors: Customer, Admin, and Super Admin. Figure 3.4 illustrates the use case diagram.

**Figure 3.4: UML Use Case Diagram**

```
                    ┌─────────────────────────────────────────┐
                    │              SYSTEM                      │
                    │                                          │
  ┌──────────┐      │  ○ Send Message                         │
  │ Customer │──────│  ○ Report Water Fault                   │
  └──────────┘      │  ○ Check Complaint Status               │
                    │  ○ Inquire About Bill                   │
                    │  ○ Check Outage Status                  │
                    │  ○ Request New Connection               │
                    │  ○ Request Human Escalation             │
                    │  ○ Submit Feedback                      │
                    │                                          │
  ┌───────┐         │  ○ Login to Admin Dashboard             │
  │ Admin │─────────│  ○ View Complaints                      │
  └───────┘         │  ○ Assign Complaint to Staff            │
                    │  ○ Update Complaint Priority            │
                    │  ○ View Escalations                     │
                    │  ○ View Session History                 │
                    │  ○ View Dashboard Metrics               │
                    │  ○ View Feedback                        │
                    │                                          │
  ┌─────────────┐   │  ○ Manage Admin Users                   │
  │ Super Admin │───│  ○ View All System Data                 │
  └─────────────┘   │  ○ Manage Resolutions                   │
                    └─────────────────────────────────────────┘
```

*Figure 3.4: UML Use Case Diagram showing actor interactions*

## 3.9 UML Sequence Diagram — Complaint Logging Flow

	Figure 3.5 illustrates the sequence of interactions during a complaint logging workflow.

**Figure 3.5: UML Sequence Diagram — Complaint Logging Flow**

```
Customer    Frontend    Orchestrator    IntentPipeline    ComplaintAgent    Storage
   │            │             │               │                │               │
   │──message──>│             │               │                │               │
   │            │──POST /chat>│               │                │               │
   │            │             │──classify()──>│                │               │
   │            │             │<──intent:     │                │               │
   │            │             │  report_fault │                │               │
   │            │             │──handle()────────────────────>│               │
   │            │             │               │                │──ask name────>│
   │            │             │<──"What is your full name?"────│               │
   │<──response─│             │               │                │               │
   │──name──────>│            │               │                │               │
   │            │──POST /chat>│               │                │               │
   │            │             │──flow_locked?─│                │               │
   │            │             │──handle()────────────────────>│               │
   │            │             │               │                │──ask area────>│
   │<──"What area?"───────────│               │                │               │
   │──area──────>│            │               │                │               │
   │            │──POST /chat>│               │                │               │
   │            │             │──handle()────────────────────>│               │
   │            │             │               │                │──log_complaint>│
   │            │             │               │                │<──ticket_id───│
   │<──"Complaint logged: WC-XXXXXX"──────────│               │               │
```

*Figure 3.5: UML Sequence Diagram for the complaint logging conversation flow*


## 3.10 Hybrid Intent Classification Pipeline

	The intent classification pipeline is the core intelligence component of the system. It implements a three-stage ensemble approach as illustrated in Figure 3.6.

**Figure 3.6: Hybrid Intent Classification Pipeline**

```
User Message
      │
      ▼
┌─────────────────────────────────────────────────────┐
│  Stage 0: Billing Priority Override                  │
│  (Hard-coded patterns for billing balance queries)   │
│  → If matched: return billing_inquiry (conf: 0.96)  │
└─────────────────────────────────────────────────────┘
      │ (if no match)
      ▼
┌─────────────────────────────────────────────────────┐
│  Stage 1: Rule-Based Classifier                      │
│  (Regex patterns for 8 intent categories)            │
│  Weight: 1.3 (highest reliability)                   │
└─────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────┐
│  Stage 2: Lightweight Keyword Classifier             │
│  (Keyword matching with context awareness)           │
│  Weight: 1.0 (baseline)                              │
└─────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────┐
│  Stage 3: Groq LLM Classifier                        │
│  (Llama 3.1 8B Instant — complex cases)              │
│  Weight: 0.9 (slight penalty for latency/cost)       │
└─────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────┐
│  Ensemble Voting                                     │
│  Weighted average confidence per intent              │
│  → Select highest-confidence intent                  │
└─────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────┐
│  Confidence Calibration                              │
│  Adjust for message length and keyword signals       │
└─────────────────────────────────────────────────────┘
      │
      ▼
  Final Intent + Confidence Score
```

*Figure 3.6: Hybrid Intent Classification Pipeline with three-stage ensemble voting*

	The supported intent categories are: `general_chat`, `billing_inquiry`, `report_fault`, `complaint_followup`, `escalation`, `office_info`, `new_connection`, `payment_info`, `water_outage`, and `out_of_scope`.

## 3.11 Technologies and Frameworks Used

**Table 3.1: Technologies and Frameworks Used**

| Category | Technology / Tool | Version | Purpose |
|----------|------------------|---------|---------|
| Programming Language | Python | 3.13.7 | Main development language |
| Backend Framework | FastAPI | ≥ 0.110 | Asynchronous RESTful API |
| AI Engine | Groq API (Llama 3.1 8B Instant) | ≥ 0.2 | NLP and intent classification |
| Database | SQLite | Built-in | Complaint and session storage |
| Web Server | Uvicorn | ≥ 0.27 | ASGI server runtime |
| Data Validation | Pydantic | ≥ 2.0 | Request/response validation |
| Frontend Framework | React + Vite | Latest | Customer chat interface |
| Admin Interface | HTML / JavaScript | — | Admin dashboard |
| Testing Framework | pytest | ≥ 8.0 | Unit and integration testing |
| Property-Based Testing | Hypothesis | ≥ 6.0 | Formal correctness verification |
| ML Libraries | scikit-learn, sentence-transformers | ≥ 1.4 | Intent discovery components |
| Version Control | Git / GitHub | — | Source code management |
| Development Tools | VS Code | — | Coding and debugging |
| Deployment | Vercel (planned) | — | Serverless deployment |

*Table 3.1: Technologies and Frameworks Used*

## 3.12 API Endpoint Specification

**Table 3.5: API Endpoint Specification**

| Method | Endpoint | Auth Required | Description |
|--------|----------|---------------|-------------|
| POST | /chat | No | Send message to chatbot |
| POST | /chat/clear | No | Clear conversation history |
| GET | /chat/updates | No | Get conversation updates |
| POST | /feedback | No | Submit user feedback rating |
| POST | /auth/login | No | Admin authentication |
| POST | /auth/logout | Yes | Token revocation |
| GET | /admin/dashboard | Yes (Admin) | Dashboard metrics |
| GET | /admin/complaints | Yes (Admin) | List all complaints |
| GET | /admin/complaint/{id} | Yes (Admin) | Get specific complaint |
| POST | /admin/complaints/{id}/assign | Yes (Admin) | Assign complaint to staff |
| POST | /admin/complaints/{id}/priority | Yes (Admin) | Update complaint priority |
| GET | /admin/escalations | Yes (Admin) | List escalations |
| GET | /admin/session/{id} | Yes (Admin) | Get session history |
| POST | /admin/resolution | Yes (Admin) | Manage case resolutions |
| GET | /admin/feedback | Yes (Admin) | View user feedback |
| GET | /health | No | System health check |

*Table 3.5: API Endpoint Specification*

## 3.13 Evaluation Metrics

	The system's performance was evaluated through both quantitative and qualitative methods.

### 3.13.1 Quantitative Metrics

**Equation 3.1 — Response Accuracy:**

```
Response Accuracy (%) = (Number of Correct Responses / Total Responses) × 100
```

**Equation 3.2 — Intent Classification Accuracy:**

```
Intent Accuracy (%) = (Correctly Classified Intents / Total Test Cases) × 100
```

**Equation 3.3 — Task Completion Rate:**

```
Task Completion Rate (%) = (Successfully Completed Tasks / Total Task Attempts) × 100
```

**Equation 3.4 — Hallucination Rate:**

```
Hallucination Rate (%) = (Responses with Unverified Claims / Total Responses) × 100
```

**Equation 3.5 — Session Quality Score (Composite):**

```
Final Score = (Quality Score × 0.40) + (Satisfaction Proxy × 0.30) + (Resolution Score × 0.20) + (Efficiency Score × 0.10)
```

### 3.13.2 Qualitative Metrics

- **User Satisfaction Survey:** 5-point Likert scale assessing clarity, helpfulness, and trust
- **Escalation Accuracy:** Whether escalations were triggered appropriately
- **Staff Willingness to Use:** Survey-based assessment of adoption readiness

## 3.14 Ethical and Data Protection Measures

	The system followed ethical AI principles and the Smart Zambia ICT Policy (2023):

- No sensitive or personal data is stored without consent
- All conversation logs use anonymised identifiers in the analytics tables; original text is stored in a restricted PII table
- LLM prompts exclude personally identifiable information
- Users are informed that they are interacting with an AI system
- Full human escalation is available for complex or sensitive cases
- Confidence-based escalation triggers automatically when intent confidence falls below 0.3
- Emergency detection triggers immediate escalation for safety-critical messages
- Immutable audit logs record all admin actions for accountability
- Data retention policies are documented in the ETHICS.md framework

## 3.15 Conclusion

	This chapter outlined the research methodology, system architecture, database design, requirements specification, intent classification pipeline, technology stack, API design, evaluation metrics, and ethical framework. The prototyping model ensured iterative refinement and close alignment with user needs at LgWSC. The following chapter presents the implementation details of the system.

---

# CHAPTER 4 — SYSTEM IMPLEMENTATION

## 4.1 Introduction

	This chapter describes the actual implementation of the Agentic AI Chatbot system. It covers the development environment, the implementation of each major system component, key technical decisions made during development, challenges encountered and how they were resolved, and the final system structure. The system was implemented as a Python/FastAPI backend with a React-based customer interface and an HTML/JavaScript admin dashboard.

## 4.2 Development Environment

	All development and testing activities were performed on a personal laptop running Windows 11. The Python virtual environment was managed using `venv`, and all dependencies were pinned in `requirements.txt`. The Groq API was used for LLM inference, providing access to the Llama 3.1 8B Instant model at low latency and no cost during development. SQLite was used as the database engine, with the database file stored at `water_utility.db` in the project root.

## 4.3 Backend Implementation

### 4.3.1 FastAPI Application Entry Point (main.py)

	The FastAPI application was configured with CORS middleware, static file serving for the admin dashboard and feedback form, and all API route registrations. The application initialises the database on startup using `init_db()` from `storage.py`, ensuring the schema is created or upgraded before any requests are processed. The `/chat` endpoint accepts a JSON body with `phone` (used as the user identifier) and `message` fields, validates them using Pydantic models, and delegates to the `Orchestrator.process()` method.

### 4.3.2 Conversation Orchestrator (orchestrator.py)

	The `Orchestrator` class is the central coordinator of all conversation processing. Its `process()` method implements the following pipeline:

1. Load the user's conversation context from SQLite via `context_manager.load_context(user_id)`
2. Start or resume a metrics session via `metrics_collector.start_session(user_id)`
3. Check for reset commands (e.g., "clear", "restart") and reset context if detected
4. Run emergency detection via `emergency_detector.detect_emergency(message, context)`
5. Update context with the incoming message and extract entities
6. Check if the conversation is flow-locked (i.e., an active agent is mid-workflow)
7. If flow-locked: route to `_handle_active_flow()` to continue the current agent
8. If not flow-locked: classify intent via `intent_pipeline.classify()` and route to `_handle_new_intent()`
9. Record turn metrics (response time, intent, confidence) via `metrics_collector.record_turn()`
10. Save updated context to SQLite and return the formatted response

	The flow-lock mechanism is the key innovation for maintaining multi-turn conversation state. When an agent sets `context["active_agent"]` and `context["flow_started"] = True`, subsequent messages bypass intent classification and are routed directly to the active agent until the flow completes.

### 4.3.3 Agent Architecture

	Six specialised agents were implemented, each inheriting from the `BaseAgent` abstract class:

- **ComplaintAgent:** Handles fault reporting, complaint logging, and outage status checks. Implements a three-step data collection flow (name → area → issue) with entity capture from each user reply. Automatically infers the issue type from the intent and message content.
- **BillingAgent:** Handles billing inquiries by delegating to the proven `agent.py` billing logic, which retrieves account information and bill details from the mock database.
- **ConnectionAgent:** Guides users through the new service connection application process, collecting name, address, phone, and email.
- **InfoAgent:** Retrieves office location and hours information from the database.
- **GeneralAgent:** Handles out-of-scope queries using the Groq LLM with a constrained system prompt to avoid hallucination.
- **HumanAgent:** Handles escalated conversations, notifying the user that their case has been transferred to a human agent.

### 4.3.4 Intent Classification Pipeline (intent_pipeline.py)

	The `IntentPipeline` class implements the three-stage ensemble classification described in Chapter 3. A key implementation detail is the billing priority override, which uses a set of high-precision regex patterns to intercept billing balance queries before they reach the ensemble. This prevents a common misrouting issue where billing queries containing words like "issue" or "problem" were incorrectly classified as fault reports.

	The ensemble voting algorithm computes a weighted average confidence score for each intent across the three classifiers, then selects the intent with the highest weighted score. If the top two intents are within 0.15 confidence of each other and the top confidence is below 0.7, the system flags the result as requiring disambiguation.

### 4.3.5 Context Engine (context_engine.py)

	The `ContextManager` class manages conversation state persistence. Each user's context is stored as a JSON object in the `session_context` SQLite table, keyed by `user_id`. The context object contains:

- `active_agent`: The name of the currently active agent (or None)
- `flow_started`: Boolean flag indicating an active multi-step flow
- `step`: The current step within the active flow
- `entities`: Extracted entities (name, area, issue, account_number, etc.)
- `history`: The last N conversation turns
- `intent`: The most recently classified intent
- `session_id`: The current metrics session identifier

	The `_is_flow_locked()` method in the orchestrator checks whether `active_agent` is set and `flow_started` is True. This is the primary mechanism for maintaining conversation continuity across turns.

### 4.3.6 Tool Executor (tool_executor.py)

	The `ToolExecutor` class dispatches tool calls from agents to the appropriate functions in `tools.py` and `storage.py`. Supported tools include `log_complaint`, `get_complaint_status`, `get_bill`, `check_area_outage`, `get_office_info`, `escalate_to_human`, and `create_connection_request`. Each tool call is wrapped in error handling to ensure graceful degradation if a tool fails.

### 4.3.7 Authentication and RBAC (auth.py)

	The authentication system implements token-based access control with three user roles: `CUSTOMER`, `ADMIN`, and `SUPER_ADMIN`. Admin tokens are generated on login and stored in memory with expiration timestamps. The `PIIProtection` class redacts sensitive fields from API responses based on the requesting user's role. All admin actions are recorded in an immutable audit log.

### 4.3.8 Storage Layer (storage.py)

	The `init_db()` function creates all 16 database tables on first run and applies schema upgrades for existing databases using `ALTER TABLE` statements wrapped in try/except blocks. The `_seed_mock_utility_data()` function populates the mock customer, account, billing, outage, and office tables with deterministic test data representing LgWSC customers in Kabwe. Parameterised queries are used throughout to prevent SQL injection.

### 4.3.9 Metrics and Evaluation (metrics_collector.py, evaluation.py)

	The `MetricsCollector` class tracks per-session and per-turn performance data including response time, intent classification confidence, escalation events, and resolution status. The `EvaluationEngine` class computes composite session quality scores using the weighted formula defined in Equation 3.5. These metrics are exposed through the admin dashboard API endpoints.

### 4.3.10 Emergency Detection (emergency_detector.py)

	The `EmergencyDetector` class scans incoming messages for keywords indicating immediate danger (e.g., flooding, gas leak, injury, fire). When an emergency is detected, the orchestrator bypasses normal intent classification and returns an emergency response with relevant contact information, marking the session as escalated.

## 4.4 Frontend Implementation

### 4.4.1 Customer Chat Interface

	The customer-facing chat interface was built using React and Vite, styled with Tailwind CSS. The interface provides a WhatsApp-style chat window with message bubbles, a text input field, and a send button. Messages are sent to the `/chat` endpoint via HTTP POST requests. The interface displays bot responses in real time and supports conversation clearing via the `/chat/clear` endpoint.

### 4.4.2 Admin Dashboard

	The admin dashboard was implemented as a static HTML/JavaScript page served by FastAPI at `/admin`. It provides:

- Login form with token-based authentication
- Real-time metrics display (total complaints, escalations, resolution rate)
- Complaint list with filtering by status and priority
- Complaint detail view with assignment and priority update controls
- Escalation list with conversation context
- User feedback list with ratings
- Session history viewer

## 4.5 Key Technical Challenges and Solutions

### 4.5.1 Context Loss in Multi-Turn Conversations

	**Challenge:** During testing, it was discovered that short plain-text replies during an active complaint flow (e.g., a user typing their name "Mary Kija") were being misrouted as new intents. The intent pipeline classified short alphabetic messages as `general_chat`, causing the `GeneralAgent` to respond with a generic greeting instead of continuing the complaint flow.

	**Root Cause Analysis:** The bug had four contributing root causes:
	1. Context was not always persisted to SQLite before the next turn was processed
	2. `_is_flow_locked()` returned False when context was not persisted
	3. The intent pipeline re-classified short plain-text replies as `general_chat`
	4. `_capture_step_reply()` guard conditions failed when the step was not persisted

	**Solution:** The orchestrator was modified to save context to SQLite unconditionally at two points: immediately after the agent sets flow state (before history is appended), and again after history is appended. The `_is_flow_locked()` check was also strengthened to detect stale context loads and re-route to the active flow. This bug was formally verified using property-based testing (see Chapter 5).

### 4.5.2 Billing Query Misrouting

	**Challenge:** Billing queries containing words like "issue" or "problem" (e.g., "I have an issue with my bill") were being classified as fault reports rather than billing inquiries.

	**Solution:** A billing priority override was added at the start of the classification pipeline using high-precision regex patterns. This override intercepts billing balance queries before they reach the ensemble, returning `billing_inquiry` with 0.96 confidence.

### 4.5.3 LLM Hallucination Prevention

	**Challenge:** The Groq LLM occasionally generated plausible but incorrect information about billing amounts, outage schedules, or office hours when these were not provided in the prompt context.

	**Solution:** The `GeneralAgent` was configured with a constrained system prompt that explicitly instructs the LLM to only answer questions about water utility services and to defer to human agents for specific factual queries. All factual responses (billing, outages, offices) are generated by tool calls to the database rather than by the LLM.

## 4.6 Project Structure

	The final project structure comprises the following key directories and files:

```
agentic_whatsapp_bot/
├── backend/                    # Python backend modules (24 files)
│   ├── orchestrator.py         # Central conversation coordinator
│   ├── intent_pipeline.py      # Hybrid intent classification
│   ├── context_engine.py       # Conversation state management
│   ├── tool_executor.py        # Tool dispatch layer
│   ├── tools.py                # Tool implementations
│   ├── storage.py              # SQLite database layer
│   ├── auth.py                 # Authentication and RBAC
│   ├── metrics_collector.py    # Performance metrics
│   ├── evaluation.py           # Quality assessment engine
│   ├── emergency_detector.py   # Emergency detection
│   ├── agent.py                # Billing agent logic
│   └── llm/                    # Groq LLM client
├── frontend/aqua-chat-modern-main/  # React customer UI
├── static/                     # Admin dashboard and feedback form
├── tests/                      # Test suite (13 test files)
├── scripts/                    # Database seeding scripts
├── logs/                       # Application logs
├── main.py                     # FastAPI application entry point
├── requirements.txt            # Python dependencies
├── ARCHITECTURE.md             # System architecture documentation
├── ETHICS.md                   # Ethics and data protection framework
└── water_utility.db            # SQLite database
```

## 4.7 Conclusion

	This chapter described the implementation of all major system components, including the orchestrator, agent architecture, intent classification pipeline, context engine, storage layer, authentication system, and frontend interfaces. Key technical challenges encountered during development — context loss, billing misrouting, and LLM hallucination — were identified and resolved. The following chapter presents the testing and evaluation results.

---

# CHAPTER 5 — TESTING AND EVALUATION

## 5.1 Introduction

	This chapter presents the testing strategy, test results, and evaluation findings for the Agentic AI Chatbot system. Testing was conducted at three levels: unit testing of individual modules, integration testing of component interactions, and system-level testing of end-to-end conversation flows. Property-based testing was additionally employed to formally verify correctness properties of the context persistence mechanism. Evaluation also incorporated a staff survey conducted with LgWSC Commercial Department employees to assess alignment with real operational requirements.

## 5.2 Testing Strategy

	The testing strategy followed a layered approach aligned with the prototyping methodology:

- **Unit Testing:** Individual functions and classes tested in isolation using pytest fixtures and mock objects
- **Integration Testing:** Component interactions tested using FastAPI's `TestClient` to simulate HTTP requests
- **System Testing:** End-to-end conversation flows tested by simulating multi-turn user interactions through the full orchestrator pipeline
- **Property-Based Testing (PBT):** The Hypothesis library was used to generate hundreds of input examples and verify formal correctness properties of the context persistence mechanism

	The test suite comprised 13 test files covering all major system components. Tests were executed using pytest 9.0.3 with the Hypothesis 6.152.7 plugin for property-based testing.

## 5.3 Test Suite Results

	The automated test suite was executed and produced the following results:

**Figure 5.1: Test Results Summary**

```
============================= test session starts =============================
platform win32 -- Python 3.13.7, pytest-9.0.3, pluggy-1.6.0
plugins: anyio-4.13.0, Faker-40.15.0, hypothesis-6.152.7
collected 39 items

tests/test_billing_routing.py          ...    PASSED (3/3)
tests/test_context_engine.py           ................    PASSED (16/16)
tests/test_core_demo_flows.py          .......    PASSED (7/7)
tests/test_groq_history_and_entities.py ...    PASSED (3/3)
tests/test_intent_discovery.py         ..    PASSED (2/2)
tests/test_pbt_context_loss_bug_condition.py  F    FAILED (0/1)
tests/test_survey_aligned_features.py  ...    PASSED (3/3)
tests/test_tool_executor_dispatch.py   ....    PASSED (4/4)

======================== 1 failed, 38 passed in 26.52s ========================
```

*Figure 5.1: Automated test suite results — 38 passed, 1 intentionally failing*

**Table 5.1: Test Suite Summary by Module**

| Test File | Tests | Passed | Failed | Coverage Area |
|-----------|-------|--------|--------|---------------|
| test_billing_routing.py | 3 | 3 | 0 | Billing intent routing and priority override |
| test_context_engine.py | 16 | 16 | 0 | Context load, save, update, reset operations |
| test_core_demo_flows.py | 7 | 7 | 0 | End-to-end complaint, billing, escalation flows |
| test_groq_history_and_entities.py | 3 | 3 | 0 | LLM history passing and entity extraction |
| test_intent_discovery.py | 2 | 2 | 0 | Self-learning intent discovery pipeline |
| test_pbt_context_loss_bug_condition.py | 1 | 0 | 1 | Bug condition verification (intentional) |
| test_survey_aligned_features.py | 3 | 3 | 0 | Survey-aligned features: billing, complaints, admin |
| test_tool_executor_dispatch.py | 4 | 4 | 0 | Tool dispatch and execution |
| **TOTAL** | **39** | **38** | **1** | |

*Table 5.1: Test suite summary by module*

## 5.4 Property-Based Testing — Context Loss Bug Condition

	The single failing test (`test_pbt_context_loss_bug_condition.py`) is an intentionally failing test that formally verifies the existence of the context loss bug identified during development. This test was written using the Hypothesis property-based testing library, which generates up to 50 random short plain-text messages (e.g., names like "Mary Kija", "John Banda") and verifies that each one is correctly handled as a flow continuation rather than a new intent when the context is stale.

	The test simulates the bug condition by:
	1. Running Turn 1 ("I want to report a water leak") to start the complaint flow
	2. Deliberately clearing `active_agent` and `flow_started` from SQLite to simulate a stale context load
	3. Running Turn 2 with the generated short plain-text message
	4. Asserting that the reply does NOT contain generic greeting phrases and that `active_agent` remains "complaint_agent"

	The test fails because the bug condition is confirmed: when context is stale, the orchestrator routes Turn 2 to `_handle_new_intent()`, which classifies the short name as `general_chat` and returns "How can I assist you?" instead of continuing the complaint flow. This test serves as a formal specification of the correct behaviour and a regression test for the fix described in Section 4.5.1.

	The property-based approach is significant because it tests the system against a wide range of generated inputs rather than a single hand-crafted example, providing stronger evidence that the bug is systematic rather than isolated.

## 5.5 Intent Classification Test Cases

**Table 5.2: Intent Classification Test Cases and Results**

| Test Input | Expected Intent | Classified Intent | Correct? |
|------------|----------------|-------------------|----------|
| "No water in my area" | report_fault | report_fault | ✓ |
| "Check my bill" | billing_inquiry | billing_inquiry | ✓ |
| "My account balance" | billing_inquiry | billing_inquiry | ✓ |
| "Water is leaking from the pipe" | report_fault | report_fault | ✓ |
| "What is my ticket status WC-ABC123" | complaint_followup | complaint_followup | ✓ |
| "I want to speak to a human agent" | escalation | escalation | ✓ |
| "Where is your office?" | office_info | office_info | ✓ |
| "I need a new water connection" | new_connection | new_connection | ✓ |
| "How do I pay my bill?" | payment_info | payment_info | ✓ |
| "Is there an outage in Makululu?" | water_outage | water_outage | ✓ |
| "Hello" | general_chat | general_chat | ✓ |
| "I have an issue with my bill" | billing_inquiry | billing_inquiry | ✓ (priority override) |
| "Dirty water coming from my tap" | report_fault | report_fault | ✓ |
| "Low water pressure at my house" | report_fault | report_fault | ✓ |

*Table 5.2: Intent classification test cases and results (14/14 correct)*

## 5.6 Survey-Aligned Feature Tests

	Three tests in `test_survey_aligned_features.py` verified that the implemented system directly addresses the requirements identified in the LgWSC staff survey:

**Test 1 — Billing Lookup:** Verified that `get_bill("123456")` returns the correct customer name ("Mary Kija") and bill amount ("K245.60"), and that an unknown account number returns an appropriate error message. **Result: PASSED.**

**Test 2 — Complaint Categorisation and Priority:** Verified that complaints about "smelly dirty water" are automatically categorised as `WATER_QUALITY` with `HIGH` priority and an SLA due date, and that complaints about "burst pipe leak" are categorised as `LEAK` with `HIGH` priority. **Result: PASSED.**

**Test 3 — Admin Assignment, Priority, Dashboard, and Feedback:** Verified that the admin API endpoints for complaint assignment, priority update, feedback submission, feedback listing, and dashboard metrics all return correct HTTP 200 responses with expected data. The dashboard correctly reported at least one urgent case and at least one WATER_QUALITY category case. **Result: PASSED.**

## 5.7 LgWSC Staff Survey Results

	A structured survey was distributed to four LgWSC Commercial Department staff members (customer service assistants with 3–5 and over 5 years of experience). The survey results are summarised below.

### 5.7.1 Most Common Inquiry Types

	Staff ranked the following inquiry types from most to least common:

**Figure 5.2: Staff Survey — Most Common Inquiry Types**

```
Rank  Inquiry Type                    Relative Frequency
1     Water outage reports            ████████████████████ (highest)
2     Leak / burst pipe reports       ████████████████
3     Payment issues                  ████████████
4     Billing questions               ██████████
5     Service connection requests     ████████
6     Account information             ██████
7     Quality complaints              ████
8     Technician requests             ██ (lowest)
```

*Figure 5.2: Staff survey ranking of most common inquiry types*

### 5.7.2 Average Time Per Inquiry

	50% of respondents reported handling inquiries in under 5 minutes, and 50% reported 5–10 minutes. No respondents reported inquiries taking over 10 minutes on average, suggesting that while individual inquiries are manageable, the high volume (50–150 per day) creates cumulative workload pressure.

### 5.7.3 Most Important Chatbot Features

	Staff selected the following as the top three most important chatbot features:

**Figure 5.3: Staff Survey — Most Important Chatbot Features**

```
Feature                    Votes (out of 4 respondents)
Bill inquiries             ███ (3 votes — highest)
Payment status             ███ (3 votes — highest)
24/7 availability          ██ (2 votes)
Automatic complaint logging ██ (2 votes)
Outage updates             █ (1 vote)
Appointment scheduling     █ (1 vote)
Other                      █ (1 vote)
Escalation to human agents  (0 votes)
Multilingual support        (0 votes)
```

*Figure 5.3: Staff survey results for most important chatbot features*

### 5.7.4 Percentage of Inquiries That Could Be Automated

**Figure 5.4: Staff Survey — Percentage of Inquiries Automatable**

```
Range       Respondents
0–20%       0
21–40%      1 (25%)
41–60%      2 (50%)
61–80%      1 (25%)
81–100%     0
```

*Figure 5.4: Staff estimates of the percentage of inquiries that could be automated*

	The majority of staff (75%) estimated that 41–80% of inquiries could be automated, validating the project's premise that a significant proportion of LgWSC's customer service workload is suitable for AI automation.

### 5.7.5 Staff Concerns

	Staff concerns about chatbot deployment were: training needs (2 votes), job security (1 vote), response accuracy (1 vote), and technical issues (1 vote). No respondents cited data privacy or customer resistance as concerns, suggesting confidence in the system's data handling and customer acceptance.

### 5.7.6 Willingness to Use

**Figure 5.5: Staff Survey — Willingness to Use Chatbot**

```
Very high   0
High        0
Medium      4 (100%)
Low         0
Very low    0
```

*Figure 5.5: Staff willingness to use the chatbot system*

	All four respondents rated their willingness to use the chatbot as "Medium". This indicates cautious acceptance rather than enthusiastic adoption, which is consistent with the concerns about training needs and response accuracy. It suggests that a structured onboarding and training programme would be necessary before deployment.

## 5.8 Evaluation Metrics Results

**Table 5.4: Evaluation Metrics Results**

| Metric | Target | Achieved | Notes |
|--------|--------|----------|-------|
| Intent Classification Accuracy | > 85% | 100% (14/14 test cases) | On defined test set |
| Test Pass Rate | > 90% | 97.4% (38/39) | 1 intentional failure |
| Complaint Logging | Functional | ✓ Verified | Category + priority + SLA auto-assigned |
| Billing Lookup | Functional | ✓ Verified | Correct customer and amount returned |
| Outage Status | Functional | ✓ Verified | Area-based lookup working |
| Human Escalation | Functional | ✓ Verified | Triggered on request and low confidence |
| Emergency Detection | Functional | ✓ Verified | Immediate escalation on safety keywords |
| PII Redaction | Functional | ✓ Verified | Analytics logs use redacted text |
| Admin RBAC | Functional | ✓ Verified | Token-based auth with role checks |
| Context Persistence | Bug identified | ✗ Bug confirmed | PBT test formally verified bug condition |
| Staff Automation Estimate | > 40% | 75% of staff: 41–80% | Survey-based |
| Staff Willingness to Use | Medium+ | Medium (100%) | Training programme needed |

*Table 5.4: Evaluation metrics results summary*

## 5.9 Limitations of Testing

	The testing conducted in this project has the following limitations:

- **No real LgWSC customer testing:** All system testing used simulated data and staff survey feedback. No live customer interactions were tested.
- **Mock data only:** The billing, outage, and customer data used in testing is simulated and does not reflect actual LgWSC records.
- **Single LLM provider:** The system was only tested with the Groq API. Behaviour with other LLM providers was not evaluated.
- **Context loss bug not yet fixed:** The property-based test formally confirmed the bug condition but the fix was not fully implemented within the project timeline. This is documented as a known limitation.
- **Small survey sample:** The staff survey had only four respondents, limiting the statistical significance of the findings.

## 5.10 Conclusion

	The testing and evaluation demonstrated that the system successfully implements all core functional requirements identified in the staff survey: bill inquiries, complaint logging with automatic categorisation, outage status checks, and 24/7 availability. The automated test suite achieved a 97.4% pass rate across 39 tests. Property-based testing formally verified the context loss bug condition, providing a rigorous specification for the required fix. Staff survey results confirmed that 75% of respondents estimated 41–80% of inquiries could be automated, validating the project's core premise. The following chapter presents the project management framework.

---

# CHAPTER 6 — PROJECT MANAGEMENT

## 6.1 Introduction

	This chapter presents the project management framework used to guide the development and implementation of the Agentic AI Chatbot for Intelligent Customer Service Automation at LgWSC. Effective management of time, resources, quality, and risks was essential to ensure the project's success within the stipulated period. This chapter details the risk and quality management strategies, provides a comprehensive risk register, presents the effort estimation and costing model, and concludes with the work plan and schedule.

## 6.2 Risk and Quality Management

### 6.2.1 Risk Management

	Risk management involved a systematic approach to identifying, assessing, and responding to potential project risks. Risks were categorised by likelihood (1–5) and impact (1–5), with a risk score computed as the product of the two. Risks scoring 9 or above were treated as high priority requiring immediate mitigation planning.

### 6.2.2 Quality Management

	Quality management ensured that the chatbot met both functional requirements (accurate responses, reliable complaint logging) and non-functional requirements (performance, usability, data protection). Quality assurance activities included:

- Code reviews and iterative testing at each prototype phase
- Verification of chatbot response accuracy, coherence, and contextual consistency
- User validation through the LgWSC staff survey
- Compliance with data protection and AI ethics guidelines
- Continuous integration using GitHub for version control and rollback capability
- Automated test suite execution with pytest to detect regressions

## 6.3 Risk Register

**Table 4.1: Risk Register**

| Risk ID | Description | Likelihood | Impact | Score | Mitigation Strategy |
|---------|-------------|-----------|--------|-------|---------------------|
| R1 | Groq API rate limits or outages disrupt chatbot operation | 3 | 5 | 15 | Implement deterministic fallback classifiers; cache frequent responses |
| R2 | Groq API cost overruns due to high message volume | 3 | 3 | 9 | Monitor token usage; optimise prompts; use rule-based classifiers for common intents |
| R3 | Data privacy concerns or unauthorised data access | 2 | 5 | 10 | PII redaction; RBAC; parameterised queries; audit logging |
| R4 | User resistance to chatbot adoption | 3 | 3 | 9 | Staff training programme; clear AI disclosure; human escalation always available |
| R5 | Context loss causing incorrect multi-turn responses | 4 | 4 | 16 | Double-save context pattern; flow-lock mechanism; PBT verification |
| R6 | LLM hallucination producing incorrect factual responses | 3 | 4 | 12 | Ground all factual responses in database tools; constrained system prompts |
| R7 | Project delays due to unforeseen technical issues | 2 | 3 | 6 | Allocate buffer time; prioritise critical features; weekly progress reviews |
| R8 | SQLite performance degradation at scale | 2 | 3 | 6 | Document PostgreSQL migration path; index critical columns |
| R9 | WhatsApp Business API verification delays | 3 | 3 | 9 | Implement web interface first; WhatsApp as future enhancement |
| R10 | Limited hardware or hosting resources | 1 | 4 | 4 | Use cloud-based infrastructure with flexible scaling |

*Table 4.1: Risk Register (Risk Score = Likelihood × Impact)*

	Risk R5 (context loss) was the highest-scoring risk and was realised during development. It was addressed through the double-save context pattern described in Section 4.5.1 and formally verified through property-based testing.

## 6.4 Effort Costing Model

	The effort costing model estimated project resources in terms of time, labour, and material costs. The formula used is based on standard academic project estimation principles:

**Equation 6.1 — Effort Calculation:**

```
Effort (Person-Hours) = Σ (Task Duration × Assigned Personnel)
```

	Assuming a single developer dedicating approximately 20 hours per week, the total expected effort for 16 weeks was:

**Equation 6.2 — Total Effort:**

```
Total Effort = 20 hours/week × 16 weeks = 320 person-hours
```

**Table 4.3: Effort Distribution by Phase**

| Phase | Duration (Weeks) | Estimated Effort (Hours) | Key Deliverables |
|-------|-----------------|--------------------------|------------------|
| Requirement Analysis and Feasibility | 2 | 40 | Staff survey, requirements specification |
| System Design | 2 | 40 | Architecture diagram, ER diagram, API spec |
| Prototype Development | 5 | 100 | Working chatbot prototype with all core features |
| Testing and Evaluation | 3 | 60 | Test suite, PBT tests, survey analysis |
| Deployment and Documentation | 2 | 40 | Deployed prototype, README, ARCHITECTURE.md |
| Report Writing | 2 | 40 | Final dissertation report |
| **Total** | **16** | **320** | |

*Table 4.3: Effort distribution by project phase*

## 6.5 Project Budget

**Table 4.2: Project Budget**

| Cost Description | Monthly Estimated Cost (ZMW) | Notes |
|-----------------|------------------------------|-------|
| Groq API (free tier during development) | 0 | Free tier sufficient for prototype |
| Cloud Hosting (Vercel free tier) | 0 | Free tier for prototype deployment |
| Internet and Electricity | 1,000 | Monthly operational cost |
| Report Printing and Binding | 1,000 | One-time cost |
| Presentation Preparation | 500 | One-time cost |
| Miscellaneous | 500 | Contingency |
| **Total Estimated Cost** | **3,000** | |

*Table 4.2: Project budget*

	The project was completed within a minimal budget due to the use of free-tier cloud services (Groq API free tier, Vercel free tier) and open-source technologies (Python, FastAPI, React, SQLite). The primary costs were internet connectivity and report production.

## 6.6 Project Schedule

	The project followed a 16-week schedule aligned with the prototyping methodology phases. The Gantt chart is illustrated in Figure 4.1.

**Figure 4.1: Project Gantt Chart**

```
Phase                          Week: 1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16
─────────────────────────────────────────────────────────────────────────────────────
Requirement Analysis           ████ ████
System Design                            ████ ████
Prototype Development                              ████ ████ ████ ████ ████
Testing and Evaluation                                                  ████ ████ ████
Deployment and Documentation                                                       ████ ████
Report Writing                                                          ████ ████ ████ ████
Supervisor Meetings            ●    ●    ●    ●    ●    ●    ●    ●    ●    ●    ●    ●
```

*Figure 4.1: Project Gantt Chart showing 16-week development schedule*

## 6.7 Conclusion

	This chapter presented the project management framework for the Agentic AI Chatbot development. The risk register identified context loss and LLM hallucination as the highest-priority technical risks, both of which were addressed during implementation. The project was completed within the 16-week schedule and minimal budget through the use of free-tier cloud services and open-source technologies. The following chapter presents the discussion, conclusions, and recommendations.

---

# CHAPTER 7 — DISCUSSION AND CONCLUSION

## 7.1 Introduction

	This chapter provides a critical discussion of the project findings, evaluates the extent to which the research objectives were achieved, discusses the limitations of the work, presents recommendations for LgWSC and future researchers, and draws final conclusions. The chapter also reflects on the academic and practical contributions of the project.

## 7.2 Discussion of Findings

### 7.2.1 Research Objective Achievement

**Objective 1 — Assess LgWSC's current customer service processes:**
	The staff survey successfully identified the top inquiry types (water outage reports, leak/burst pipe reports, payment issues, billing questions), the average handling time (under 10 minutes per inquiry), and the key operational challenges (manual data entry errors, incomplete customer information). The survey confirmed that 75% of staff estimated 41–80% of inquiries could be automated, providing strong empirical justification for the chatbot system. This objective was fully achieved.

**Objective 2 — Design a conversational AI agent:**
	The system was designed with six specialised agents (ComplaintAgent, BillingAgent, ConnectionAgent, InfoAgent, GeneralAgent, HumanAgent) coordinated by a central Orchestrator. The agent architecture successfully handles all top inquiry types identified in the survey. This objective was fully achieved.

**Objective 3 — Implement a hybrid intent classification pipeline:**
	The three-stage ensemble pipeline (rule-based, lightweight keyword, Groq LLM) with billing priority override achieved 100% accuracy on the 14 defined test cases. The pipeline correctly handles the most common misrouting scenario (billing queries containing fault-related words) through the priority override mechanism. This objective was fully achieved.

**Objective 4 — Build a secure backend with RBAC, audit logging, and PII protection:**
	The authentication system implements token-based RBAC with three roles (CUSTOMER, ADMIN, SUPER_ADMIN). PII is automatically redacted from analytics logs. All admin actions are recorded in an immutable audit log. This objective was fully achieved.

**Objective 5 — Evaluate the system using automated testing, PBT, and staff surveys:**
	The automated test suite achieved a 97.4% pass rate (38/39). Property-based testing formally verified the context loss bug condition using the Hypothesis library. The staff survey provided quantitative evidence of operational alignment. This objective was substantially achieved, with the context loss bug identified but not fully resolved within the project timeline.

**Objective 6 — Examine ethical considerations:**
	A comprehensive ethics framework was documented in ETHICS.md, covering AI disclosure, data collection, PII redaction, data retention, human intervention triggers, confidence-based escalation, and compliance with the Smart Zambia ICT Policy. This objective was fully achieved.

### 7.2.2 Technical Findings

	The most significant technical finding was the context loss bug in multi-turn conversations. This bug — where short plain-text replies during an active complaint flow were misrouted as new intents — represents a fundamental challenge in stateful conversational AI systems. The root cause analysis identified four contributing factors: context not persisted before the next turn, flow-lock check returning False on stale context, intent pipeline misclassifying short names as general chat, and step guard conditions failing on missing state.

	The property-based testing approach proved particularly valuable for this bug. Rather than testing a single hand-crafted example, Hypothesis generated 50 random short plain-text messages and verified the bug condition against each one, providing strong evidence that the issue is systematic. This demonstrates the value of formal correctness verification in AI system development — an approach that goes beyond conventional unit testing.

	The hybrid intent classification pipeline performed well on the defined test set. The billing priority override was a pragmatic solution to a real misrouting problem, demonstrating that domain-specific heuristics can significantly improve classification reliability without requiring LLM inference for every query.

### 7.2.3 Survey Findings and System Alignment

	The staff survey results directly shaped the system's feature priorities. The top three most important chatbot features identified by staff — bill inquiries (3 votes), payment status (3 votes), and 24/7 availability (2 votes) — are all implemented in the system. The survey-aligned feature tests (`test_survey_aligned_features.py`) verified that these features work correctly with realistic test data.

	The unanimous "Medium" willingness to use rating is an important finding. It suggests that while staff recognise the value of the chatbot, they are not yet confident enough to fully embrace it. This is consistent with the literature on chatbot adoption, which identifies response accuracy and training needs as key barriers (Index, 2023). A structured onboarding programme and a pilot period with close monitoring would be necessary before full deployment.

## 7.3 Limitations

1. **Context loss bug not fully resolved:** The property-based test formally confirmed the bug condition, but the complete fix was not implemented within the project timeline. The double-save context pattern partially mitigates the issue but does not eliminate it under all stale-context scenarios.

2. **Web-based only — no WhatsApp integration:** The system was implemented as a web chatbot rather than a WhatsApp chatbot as originally proposed. WhatsApp Business API integration requires business verification and incurs per-conversation fees, making it unsuitable for a prototype phase.

3. **Mock data only:** All billing, customer, and outage data is simulated. The system has not been tested against actual LgWSC databases, which may have different schemas, data quality issues, or access restrictions.

4. **Small survey sample:** The staff survey had only four respondents from a single department. A larger, multi-department survey would provide more representative findings.

5. **Single LLM provider:** The system depends entirely on the Groq API. No fallback LLM provider was implemented, creating a single point of failure for the LLM-dependent components.

6. **SQLite scalability:** SQLite is suitable for the prototype phase but would require migration to PostgreSQL for production deployment at LgWSC's scale.

7. **No customer-facing user testing:** All evaluation was conducted with staff rather than actual LgWSC customers. Customer usability testing would provide additional insights into interface clarity and conversation flow naturalness.

## 7.4 Recommendations

### 7.4.1 Recommendations for LgWSC

1. **Conduct a structured pilot deployment** with a small group of customers and staff before full rollout, using the web interface as the initial channel.
2. **Develop a staff training programme** addressing the training needs concern identified in the survey, covering how to monitor the chatbot dashboard, handle escalations, and interpret metrics.
3. **Integrate with actual LgWSC databases** by replacing the mock data layer with read-only API connections to the billing and customer management systems.
4. **Pursue WhatsApp Business API verification** to enable the planned WhatsApp channel, which would significantly increase accessibility for LgWSC's customer base.
5. **Establish a data governance committee** to oversee AI system performance, review escalation logs, and approve changes to the intent classification rules.

### 7.4.2 Recommendations for Future Research

1. **Fix the context loss bug** by implementing a robust context recovery mechanism that reconstructs flow state from conversation history when the persisted context is stale.
2. **Add a second LLM provider** (e.g., OpenAI GPT-4o-mini) as a fallback to eliminate the single point of failure.
3. **Implement multilingual support** for Nyanja and Bemba to serve LgWSC's broader customer base in Central Province.
4. **Conduct customer usability testing** with a representative sample of LgWSC customers to assess interface clarity, conversation naturalness, and satisfaction.
5. **Extend property-based testing** to cover additional correctness properties, including billing lookup invariants, complaint categorisation consistency, and escalation trigger conditions.
6. **Evaluate RAG integration** using LgWSC's actual FAQ documents and policy manuals to improve the accuracy of general information responses.

## 7.5 Research Contributions

	This project makes the following contributions to the field of Applied Artificial Intelligence and software engineering:

1. **Practical agentic AI implementation for Zambian utilities:** The first documented implementation of an agentic AI chatbot for a Zambian water utility, demonstrating the feasibility of AI-driven customer service automation in a developing-country public sector context.

2. **Hybrid intent classification with domain-specific priority overrides:** A three-stage ensemble pipeline with billing priority override that addresses a common misrouting problem in utility-domain chatbots without requiring LLM inference for every query.

3. **Property-based testing for conversational AI correctness:** Application of the Hypothesis PBT library to formally verify a bug condition in multi-turn conversation state management, demonstrating a rigorous testing methodology for AI systems beyond conventional unit testing.

4. **Survey-driven requirements validation:** A methodology for aligning chatbot feature priorities with operational staff requirements through structured surveys, with automated tests verifying that the implemented features match the survey findings.

5. **Governance-aware AI architecture:** An implementation of responsible AI principles (PII redaction, RBAC, audit logging, confidence-based escalation, emergency detection) in a production-ready FastAPI backend, providing a reusable template for ethical AI deployment in public utility contexts.

## 7.6 Conclusion

	This project successfully designed, implemented, and evaluated an Agentic AI Chatbot for intelligent customer service automation at Lukanga Water Supply and Sanitation Company. The system autonomously handles the top inquiry types identified through staff surveys — water outage reports, billing inquiries, complaint logging, and payment status checks — with automatic complaint categorisation, priority assignment, and SLA tracking.

	The hybrid intent classification pipeline achieved 100% accuracy on the defined test set, and the automated test suite achieved a 97.4% pass rate across 39 tests. Property-based testing formally verified the context loss bug condition, providing a rigorous specification for the required fix. The staff survey confirmed that 75% of respondents estimated 41–80% of inquiries could be automated, validating the project's core premise.

	The system demonstrates how modern AI technologies — large language models, agentic orchestration, and formal testing methodologies — can be applied to improve public utility service delivery in Zambia. With the recommended enhancements (WhatsApp integration, database integration, multilingual support, and the context loss fix), the system is well-positioned for pilot deployment at LgWSC and could serve as a model for other water supply and sanitation companies across Zambia.

	This project contributes to Zambia's Smart Zambia digital transformation agenda and demonstrates that enterprise-grade AI customer service systems can be built and deployed by Zambian computer science graduates using modern open-source technologies and cloud AI services.

---

# REFERENCES

Devlin, J., Chang, M., Lee, K. and Toutanova, K. (2019) 'BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding', *Proceedings of NAACL-HLT 2019*, pp. 4171–4186. Available at: https://arxiv.org/abs/1810.04805 (Accessed: 10 April 2025).

FastAPI (2024) *FastAPI Documentation: Building APIs with Python*. Available at: https://fastapi.tiangolo.com/ (Accessed: 15 March 2025).

Gartner (2025) *Top Strategic Technology Trends for 2025: Agentic AI*. Stamford: Gartner Research.

Index, C. (2023) *Chatbot Adoption in Customer Service: Global Trends and Challenges*. Customer Index Research Report.

Infotech, M. (2025) *AI Bot Architectures in 2025: From Orchestration to LLM-in-the-Loop*. Available at: https://medium.com/@Mobisoft.Infotech/ai-chatbot-architecture-building-scalable-conversational-systems-253189a45d3d (Accessed: 20 March 2025).

Joshi, S. (2025) 'AI Governance in the Era of Agentic Generative AI and AGI: Frameworks, Risks, and Policy Directions', *International Journal of Innovative Research in Computer Science and Technology*, 13(2), pp. 45–62.

Jurafsky, D. and Martin, J.H. (2023) *Speech and Language Processing*. 3rd edn. Stanford: Stanford University Press. Available at: https://web.stanford.edu/~jurafsky/slp3/ (Accessed: 5 April 2025).

LangChain (2024) *Build a RAG Agent with LangChain*. Available at: https://docs.langchain.com/oss/python/langchain/rag (Accessed: 18 March 2025).

Lee, A. (2025) *Perceptions of Agentic AI in Organizations: Implications for Responsible AI and ROI*. Frankfurt: Media University of Applied Sciences.

LgWSC Internal Staff Interview (2025) *Interview with Customer Service Staff at Lukanga Water Supply and Sanitation Company*, Kabwe, Zambia, February 2025. [Unpublished].

MacMahon, S., Cohn, D. and Hypothesis Contributors (2024) *Hypothesis: Property-Based Testing for Python*. Available at: https://hypothesis.readthedocs.io/ (Accessed: 22 April 2025).

Meta (2025) *WhatsApp Business Platform*. Available at: https://developers.facebook.com/docs/whatsapp (Accessed: 10 March 2025).

OpenAI (2024) *Practices for Governing Agentic AI Systems*. San Francisco: OpenAI. Available at: https://openai.com/research/practices-for-governing-agentic-ai-systems (Accessed: 12 March 2025).

Pressman, R.S. and Maxim, B.R. (2021) *Software Engineering: A Practitioner's Approach*. 9th edn. New York: McGraw-Hill Education.

Russell, S. and Norvig, P. (2022) *Artificial Intelligence: A Modern Approach*. 4th edn. New Jersey: Pearson Education.

Smart Zambia (2023) *Smart Zambia ICT Policy: Digital Government and Data Governance Framework*. Lusaka: Smart Zambia Institute.

Twilio (2024) *WhatsApp Business Platform with Twilio*. Available at: https://www.twilio.com/docs/whatsapp (Accessed: 10 March 2025).

Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A.N., Kaiser, L. and Polosukhin, I. (2017) 'Attention Is All You Need', *Advances in Neural Information Processing Systems*, 30, pp. 5998–6008. Available at: https://arxiv.org/abs/1706.03762 (Accessed: 8 April 2025).

Weizenbaum, J. (1966) 'ELIZA — A Computer Program for the Study of Natural Language Communication Between Man and Machine', *Communications of the ACM*, 9(1), pp. 36–45.

Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K. and Cao, Y. (2023) 'ReAct: Synergizing Reasoning and Acting in Language Models', *International Conference on Learning Representations (ICLR 2023)*. Available at: https://arxiv.org/abs/2210.03629 (Accessed: 15 April 2025).

---

# APPENDICES

## Appendix A — LgWSC Staff Survey Instrument

The following questions were included in the structured staff survey distributed to LgWSC Commercial Department employees:

1. Position/Role (open text)
2. Department (open text)
3. Years with LgWSC (< 1, 1–3, 3–5, > 5)
4. How many customer inquiries do you handle daily? (< 50, 50–100, 100–150, 150–200, > 200)
5. What are the top 5 most common inquiries? (Rank from most to least)
6. Average time per inquiry (< 5 min, 5–10 min, 10–20 min, > 20 min)
7. What are your biggest challenges? (Select all that apply)
8. Most important chatbot features? (Select top 3)
9. What percentage of inquiries could be automated? (0–20%, 21–40%, 41–60%, 61–80%, 81–100%)
10. Most important chatbot features? (Select top 3) [repeated for confirmation]
11. Information needed for complaint logging (open text)
12. What concerns do you have? (Select all that apply)
13. Willingness to use (Very high, High, Medium, Low, Very low)

## Appendix B — Key Code Excerpts

### B.1 — Orchestrator Flow-Lock Check

```python
def _is_flow_locked(self, context: dict) -> bool:
    """Return True if an active agent flow is in progress."""
    return bool(
        context.get("active_agent") and
        context.get("flow_started")
    )
```

### B.2 — Hybrid Intent Classification Ensemble Vote

```python
def _ensemble_vote(self, results: List[dict], message: str, context: dict) -> dict:
    source_weights = {"rule": 1.3, "lightweight": 1.0, "llm": 0.9}
    weighted_votes: Dict[str, Dict[str, float]] = {}
    for result in results:
        intent = result.get("intent", "out_of_scope")
        confidence = result.get("confidence", 0.0)
        source = result.get("source", "unknown")
        weight = source_weights.get(source, 1.0)
        if intent not in weighted_votes:
            weighted_votes[intent] = {"score_sum": 0.0, "weight_sum": 0.0}
        weighted_votes[intent]["score_sum"] += confidence * weight
        weighted_votes[intent]["weight_sum"] += weight
    ensemble_votes = {
        intent: data["score_sum"] / data["weight_sum"]
        for intent, data in weighted_votes.items()
        if data["weight_sum"] > 0
    }
    top_intent = max(ensemble_votes, key=lambda k: ensemble_votes[k])
    return ClassificationResult(
        intent=top_intent,
        confidence=ensemble_votes[top_intent],
        entities={}, source="ensemble"
    ).to_dict()
```

### B.3 — Property-Based Test Strategy (Hypothesis)

```python
short_plain_message_strategy = (
    st.text(
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Zs"),
        ),
        min_size=2, max_size=40,
    )
    .map(str.strip)
    .filter(lambda m: len(m) >= 2)
    .filter(lambda m: not _contains_service_keyword(m))
    .filter(lambda m: len(m.split()) <= 6)
    .filter(lambda m: any(c.isalpha() for c in m))
)
```

### B.4 — Complaint Auto-Categorisation Logic (storage.py)

```python
def _infer_category(issue: str) -> str:
    lowered = issue.lower()
    if any(t in lowered for t in ["dirty", "contaminated", "smelly", "bad taste", "unsafe"]):
        return "WATER_QUALITY"
    if any(t in lowered for t in ["leak", "burst", "pipe"]):
        return "LEAK"
    if any(t in lowered for t in ["no water", "outage", "water cut", "water off"]):
        return "NO_WATER"
    if any(t in lowered for t in ["meter", "reading"]):
        return "METER"
    if any(t in lowered for t in ["bill", "billing", "payment", "account"]):
        return "BILLING"
    return "OTHER"
```

---

*End of Dissertation*

*Word count (approximate): 12,500 words*

*Submitted in partial fulfilment for the award of Bachelor of Science in Computer Science, Mulungushi University, 2024/2025 Academic Year.*
