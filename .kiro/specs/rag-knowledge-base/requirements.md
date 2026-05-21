# Requirements Document

## Introduction

This feature adds a Retrieval-Augmented Generation (RAG) knowledge base to the Kabwe Water agentic WhatsApp bot. Currently, the `GeneralAgent` calls Groq with only conversation history and no grounding context, causing the bot to hallucinate or admit ignorance when users ask about tariff schedules, service areas, office procedures, or utility policies. The RAG knowledge base will embed curated utility documents into a persistent ChromaDB vector store, retrieve the most relevant chunks at query time, and inject them as grounding context into the Groq system prompt — eliminating hallucination for factual utility questions. A semantic intent fallback will also improve classification accuracy when the rule-based pipeline confidence is low. All components must run fully offline using local sentence-transformers embeddings.

---

## Glossary

- **Chunk**: A fixed-size, overlapping text segment produced by splitting a knowledge base document. Each chunk is the unit of storage and retrieval in ChromaDB.
- **ChromaDB**: The open-source, embedded vector database used to persist document embeddings to disk (`chroma_db/` directory).
- **Embedding**: A dense numerical vector representation of a text string produced by the `SentenceTransformer` model `all-MiniLM-L6-v2`.
- **GeneralAgent**: The agent class in `backend/orchestrator.py` that handles messages not routed to billing, complaint, connection, or info agents. It calls `generate_response()` from `backend/llm/groq_client.py`.
- **Intent_Pipeline**: The hybrid classification pipeline in `backend/intent_pipeline.py` that combines rule-based, lightweight, and LLM classifiers.
- **Knowledge_Base**: The collection of Markdown documents stored in `backend/knowledge_base/` covering tariffs, service areas, FAQs, office hours, and outage procedures.
- **RAG_Retriever**: The module `backend/rag_retriever.py` responsible for embedding a query and returning the top-k most relevant chunks from ChromaDB.
- **Reindex_Endpoint**: The FastAPI admin endpoint `POST /admin/knowledge-base/reindex` that triggers re-chunking and re-embedding of all knowledge base documents.
- **Seeding_Script**: The script `scripts/seed_knowledge_base.py` that performs the initial chunking and indexing of all knowledge base documents into ChromaDB.
- **Semantic_Fallback**: The mechanism that uses vector similarity against known intent examples when the rule-based pipeline confidence falls below a threshold.
- **SentenceTransformer**: The local embedding model `all-MiniLM-L6-v2` from the `sentence-transformers` library, running entirely on-device without any external API calls.
- **Structured_Flow**: Any of the existing rule-driven conversation flows — billing, complaint, connection, or info — that must not be disrupted by RAG context injection.

---

## Requirements

### Requirement 1: Knowledge Base Document Storage

**User Story:** As a Kabwe Water support bot maintainer, I want to store utility knowledge in structured Markdown files, so that the content can be updated independently of the application code and re-indexed on demand.

#### Acceptance Criteria

1. THE Knowledge_Base SHALL store all documents as `.md` files under `backend/knowledge_base/`.
2. THE Knowledge_Base SHALL include at minimum the following document categories: water tariff schedules (residential, commercial, industrial rates), service area coverage (Kabwe, Makululu, Riverside, Industrial Area, and surrounding areas), FAQ (meter reading, leak reporting, payment methods, connection process), office hours and contact information, and outage notification procedures.
3. WHEN a knowledge base document is created or updated, THE Knowledge_Base SHALL use UTF-8 encoding and SHALL apply Unicode NFC normalisation to all text so that Zambian place names and currency symbols (K) are preserved without corruption.
4. WHEN a knowledge base document is read by the Seeding_Script, THE Seeding_Script SHALL validate that the decoded text contains no replacement characters (U+FFFD) and, IF replacement characters are detected, THEN THE Seeding_Script SHALL log a warning with the filename and the byte offset of the first invalid sequence before continuing.
5. THE Knowledge_Base SHALL include a document-level metadata header in each file specifying at minimum: `title`, `category`, and `last_updated` (in ISO 8601 date format, e.g. `2026-05-20`) fields, so that the Seeding_Script can attach metadata to each chunk stored in ChromaDB.
6. IF a knowledge base document is missing the required metadata header or any of the three required fields, THEN THE Seeding_Script SHALL log a warning with the filename and the missing field names, and SHALL skip that document rather than indexing it with incomplete metadata.

---

### Requirement 2: Document Chunking and Indexing

**User Story:** As a Kabwe Water support bot maintainer, I want documents to be automatically chunked and indexed into ChromaDB, so that the RAG pipeline can retrieve relevant passages at query time.

#### Acceptance Criteria

1. WHEN the Seeding_Script is executed, THE Seeding_Script SHALL read all `.md` files from `backend/knowledge_base/`, split each file into overlapping text chunks, embed each chunk using the SentenceTransformer model `all-MiniLM-L6-v2`, and upsert the resulting embeddings into the ChromaDB collection.
2. THE Seeding_Script SHALL use a chunk size of 300–500 tokens and an overlap of 50–100 tokens so that context is not lost at chunk boundaries.
3. WHEN a document is re-indexed, THE Seeding_Script SHALL upsert chunks by a deterministic chunk ID derived from the source filename and the zero-based chunk index (e.g. `"tariffs_0"`, `"tariffs_1"`) so that re-running the script does not create duplicate entries.
4. THE Seeding_Script SHALL attach the following metadata to each chunk stored in ChromaDB: `source` (filename), `title`, `category`, and `chunk_index`.
5. IF the `sentence-transformers` model files are not present locally, THEN THE Seeding_Script SHALL download and cache them before proceeding; the download SHALL time out after 60 seconds per file and SHALL log progress at least once per file downloaded.
6. WHEN the Seeding_Script completes successfully, THE Seeding_Script SHALL log the total number of documents processed, total chunks created, and total time elapsed in seconds.
7. IF the Seeding_Script fails to embed or upsert a chunk mid-run, THEN THE Seeding_Script SHALL log a warning with the chunk ID and the error message, skip that chunk, and continue processing remaining chunks rather than aborting.

---

### Requirement 3: Persistent Vector Store

**User Story:** As a Kabwe Water support bot operator, I want the ChromaDB vector store to persist to disk, so that embeddings survive server restarts and do not need to be recomputed on every startup.

#### Acceptance Criteria

1. THE RAG_Retriever SHALL initialise ChromaDB in persistent mode using the directory path `chroma_db/` relative to the project root, so that the collection survives process restarts.
2. WHILE the FastAPI server is running, THE RAG_Retriever SHALL reuse the same ChromaDB client instance across requests to avoid repeated disk I/O on every query.
3. IF the `chroma_db/` directory does not exist at startup, THEN THE RAG_Retriever SHALL create it automatically before attempting to open the collection.
4. THE RAG_Retriever SHALL use a single named ChromaDB collection (e.g. `"kabwe_water_kb"`) so that all knowledge base chunks are stored and queried from one place.

---

### Requirement 4: Query Embedding and Retrieval

**User Story:** As a WhatsApp user of the Kabwe Water bot, I want the bot to retrieve relevant knowledge base passages when I ask factual questions, so that I receive accurate, grounded answers instead of hallucinated responses.

#### Acceptance Criteria

1. WHEN a user message is received by the RAG_Retriever, THE RAG_Retriever SHALL embed the message using the same SentenceTransformer model used during indexing (`all-MiniLM-L6-v2`) and query ChromaDB for the top-3 most semantically similar chunks.
2. THE RAG_Retriever SHALL return retrieved chunks as a list of plain-text strings in the format `"[Source: <title>] <chunk_text>"`, one string per chunk, containing only chunks whose cosine similarity meets the threshold in AC3.
3. WHEN no chunks exceed a minimum relevance threshold (cosine similarity ≥ 0.30), THE RAG_Retriever SHALL return an empty list rather than injecting low-relevance noise into the prompt.
4. THE RAG_Retriever SHALL complete a single retrieval query (embed + ChromaDB search) within 600 milliseconds regardless of system load.
5. IF ChromaDB is unavailable or raises an exception during retrieval, THEN THE RAG_Retriever SHALL log the exception class and message at ERROR level and return an empty list so that the GeneralAgent can still respond without RAG context.

---

### Requirement 5: GeneralAgent RAG Integration

**User Story:** As a WhatsApp user of the Kabwe Water bot, I want the bot's general responses to be grounded in official utility information, so that answers about tariffs, service areas, and procedures are accurate and consistent.

#### Acceptance Criteria

1. WHEN the GeneralAgent handles a user message, THE GeneralAgent SHALL call the RAG_Retriever before calling `generate_response()` and, IF the retriever returns a non-empty list, inject the chunks into the Groq system prompt as a block beginning with the literal header `"FACTS:"` followed by each chunk on a new line.
2. WHEN retrieved chunks are injected, THE GeneralAgent SHALL include an instruction in the system prompt stating that the model must not state facts about tariffs, service areas, or procedures that are not present in the FACTS block.
3. WHEN the RAG_Retriever returns an empty list (no relevant chunks found), THE GeneralAgent SHALL call `generate_response()` without a FACTS block, preserving existing behaviour.
4. WHEN a Structured_Flow is active (the conversation is being handled by a service agent other than GeneralAgent), THE RAG_Retriever SHALL NOT be called.
5. WHEN the GeneralAgent is invoked, THE GeneralAgent SHALL pass the user's original (non-redacted) message to the RAG_Retriever for embedding.
6. WHEN the GeneralAgent is invoked, THE GeneralAgent SHALL pass the PII-redacted version of the message to `generate_response()`, maintaining the existing privacy boundary.
7. IF the RAG_Retriever raises an exception during the GeneralAgent call, THEN THE GeneralAgent SHALL log the exception at ERROR level and proceed to call `generate_response()` without a FACTS block rather than propagating the exception to the caller.

---

### Requirement 6: Semantic Intent Fallback

**User Story:** As a Kabwe Water support bot operator, I want the intent pipeline to use semantic similarity as a fallback when rule-based confidence is low, so that ambiguous user messages are classified more accurately.

#### Acceptance Criteria

1. WHEN the Intent_Pipeline produces a classification result with confidence below 0.50, THE Intent_Pipeline SHALL invoke the Semantic_Fallback by embedding the user message and computing cosine similarity against the pre-computed intent example embeddings.
2. THE Semantic_Fallback SHALL maintain a static set of at least 3 example utterances per supported intent (covering: `billing_inquiry`, `report_fault`, `complaint_followup`, `new_connection`, `payment_info`, `office_info`, `escalation`, `general_chat`), and SHALL pre-compute and cache the embeddings for all examples at application startup.
3. WHEN the Semantic_Fallback finds a best-matching intent with cosine similarity strictly greater than 0.55, THE Intent_Pipeline SHALL replace the low-confidence result with the semantically matched intent and set the confidence to the cosine similarity score.
4. WHEN the Semantic_Fallback finds no match above 0.55, THE Intent_Pipeline SHALL retain the original low-confidence result unchanged.
5. THE Semantic_Fallback SHALL use the same SentenceTransformer model instance as the RAG_Retriever to avoid loading the model twice.
6. WHEN the Semantic_Fallback is invoked, THE Intent_Pipeline SHALL log the original intent, original confidence, matched intent, and similarity score at DEBUG level for observability.
7. IF the Semantic_Fallback raises an exception during invocation, THEN THE Intent_Pipeline SHALL log the exception at WARNING level and return the original low-confidence result unchanged, so that a fallback failure does not break intent classification.

---

### Requirement 7: Knowledge Base Seeding Script

**User Story:** As a Kabwe Water support bot maintainer, I want a standalone script to seed the ChromaDB vector store from the knowledge base documents, so that I can initialise or refresh the index without restarting the server.

#### Acceptance Criteria

1. THE Seeding_Script SHALL be executable as `python scripts/seed_knowledge_base.py` from the project root without requiring any command-line arguments for a default full re-index.
2. THE Seeding_Script SHALL support a `--dry-run` flag that logs what would be indexed without writing to ChromaDB, so that maintainers can verify document parsing before committing changes.
3. WHEN the Seeding_Script is run and the ChromaDB collection already contains chunks from a previous run, THE Seeding_Script SHALL upsert (not duplicate) existing chunks using deterministic IDs.
4. IF a knowledge base document cannot be read or parsed, THEN THE Seeding_Script SHALL log a warning with the filename and continue processing remaining documents rather than aborting.
5. WHEN a knowledge base document is successfully processed, THE Seeding_Script SHALL log an informational message with the filename and the number of chunks created.
6. THE Seeding_Script SHALL print a summary table to stdout upon completion showing: document name, number of chunks created, and indexing status (success / skipped / error) for each file.

---

### Requirement 8: Admin Re-index Endpoint

**User Story:** As a Kabwe Water support bot administrator, I want an HTTP endpoint to trigger knowledge base re-indexing, so that I can refresh the vector store after updating documents without restarting the server.

#### Acceptance Criteria

1. THE Reindex_Endpoint SHALL be accessible at `POST /admin/knowledge-base/reindex` and SHALL trigger the same chunking, embedding, and upsert logic used by the Seeding_Script.
2. WHEN the re-index operation completes successfully, THE Reindex_Endpoint SHALL return a JSON response containing: `status: "success"`, `documents_processed` (integer), `chunks_upserted` (integer), and `elapsed_seconds` (float).
3. IF the re-index operation fails (e.g. a document cannot be read), THEN THE Reindex_Endpoint SHALL return HTTP 500 with a JSON body containing `status: "error"` and a `detail` field describing the failure.
4. THE Reindex_Endpoint SHALL run the re-index operation synchronously within the request so that the response confirms completion, not just initiation.
5. WHERE an admin API key is configured via the `ADMIN_API_KEY` environment variable, THE Reindex_Endpoint SHALL require the caller to supply it in the `X-Admin-Key` request header and SHALL return HTTP 403 if the key is missing or incorrect.

---

### Requirement 9: Offline Operation Constraint

**User Story:** As a Kabwe Water support bot operator in Zambia, I want all embedding operations to run locally without calling any external API, so that the bot continues to function during internet outages.

#### Acceptance Criteria

1. WHEN the SentenceTransformer model is loaded and the application is running, THE model SHALL NOT make any outbound network calls — including update checks, telemetry, or metadata requests — during runtime operation.
2. WHEN the SentenceTransformer model is not yet cached locally, THE Seeding_Script SHALL download it once and cache it to disk so that subsequent runs are fully offline.
3. THE RAG_Retriever SHALL NOT depend on any external API — including embedding APIs (e.g. OpenAI, Cohere, Hugging Face Inference API), metadata enrichment services, or query expansion services — at any point in the retrieval pipeline.
4. THE ChromaDB instance SHALL operate in embedded (in-process) mode and SHALL NOT require a running ChromaDB server process.
5. IF the local SentenceTransformer model cache is corrupt or missing at runtime (after the initial download), THEN THE RAG_Retriever SHALL log an ERROR and return an empty list for all queries rather than attempting a network download, so that the bot remains available in a degraded state.

---

### Requirement 10: Non-Disruption of Existing Structured Flows

**User Story:** As a WhatsApp user of the Kabwe Water bot, I want billing, complaint, connection, and office-info flows to continue working exactly as before, so that the RAG feature does not break existing functionality.

#### Acceptance Criteria

1. WHEN a Structured_Flow is active (i.e. the conversation is being handled by a billing, complaint, connection, or info agent), THE Orchestrator SHALL route the message to the active agent without invoking the RAG_Retriever.
2. THE RAG_Retriever SHALL be invoked only from within the GeneralAgent and SHALL NOT be called from BillingAgent, ComplaintAgent, ConnectionAgent, or InfoAgent.
3. WHEN the GeneralAgent injects RAG context into the Groq prompt, THE system prompt SHALL still contain the existing out-of-scope guardrail instructions that were present before the RAG feature was added, so that the bot continues to decline non-utility topics.
4. WHEN a message is handled by a Structured_Flow agent, THE code path SHALL NOT call the RAG_Retriever at any point, ensuring that RAG retrieval adds zero latency to structured flow responses.

---

### Requirement 11: Dependency Management

**User Story:** As a Kabwe Water support bot developer, I want all new dependencies to be declared in `requirements.txt`, so that the environment can be reproduced consistently.

#### Acceptance Criteria

1. THE `requirements.txt` SHALL include `chromadb` pinned to a specific version compatible with the existing `sentence-transformers>=2.6` and `numpy>=1.21` entries already present.
2. THE `requirements.txt` SHALL NOT duplicate the `sentence-transformers` entry that already exists, since it is already declared.
3. WHEN a developer runs `pip install -r requirements.txt` on a clean Python environment, THE environment SHALL contain all packages required to run the RAG pipeline, the Seeding_Script, and the Reindex_Endpoint without additional manual installs.
