# Requirements Document

## Introduction

This feature adds customer-level PIN authentication to the Kabwe Water agentic Chatbot. Currently, any caller can retrieve billing data for any account number without proving ownership — a significant privacy and security gap. This feature closes that gap by introducing a 4-digit PIN per account, a secure `customer_auth` table, a conversational PIN verification flow inside the bot, account lockout after repeated failures, an admin-only PIN reset endpoint, and a migration of the three existing demo accounts to zero-padded sequential account numbers with seeded PINs.

The design follows the existing admin authentication pattern in `auth.py` (PBKDF2-SHA256 hashing, salted, constant-time comparison) and integrates into the `BillingAgent` conversation flow in `orchestrator.py` without breaking any other agent flows.

---

## Glossary

- **Account_Number**: A zero-padded 6-digit string (e.g. `"000001"`) that uniquely identifies a customer's water service account. New accounts are auto-incremented from the highest existing value.
- **PIN**: A 4-digit numeric Personal Identification Number chosen by or assigned to a customer, used to verify account ownership before sensitive data is returned.
- **PIN_Hash**: The PBKDF2-SHA256 digest of the PIN combined with the PIN_Salt, stored in `customer_auth` as a hexadecimal string. The plaintext PIN is never persisted.
- **PIN_Salt**: A cryptographically random 32-byte value generated per account, stored as a hexadecimal string alongside the PIN_Hash to prevent rainbow-table attacks.
- **Customer_Auth_Table**: The SQLite table `customer_auth` that stores `account_number`, `pin_salt`, `pin_hash`, `failed_attempts`, and `locked_until` for every account.
- **Auth_Service**: The Python module/class responsible for PIN hashing, PIN verification, lockout enforcement, and PIN reset — the customer-facing counterpart to the existing `AuthService` in `auth.py`.
- **BillingAgent**: The agent class in `orchestrator.py` that handles billing inquiries. It must gate the `get_bill` tool call behind successful PIN verification.
- **Lockout**: A temporary suspension of PIN verification for an account after 3 consecutive failed attempts, lasting 15 minutes from the time of the third failure.
- **Admin_Reset_Endpoint**: A FastAPI HTTP endpoint, protected by the existing admin token, that allows an administrator to set a new PIN for any account.
- **Demo_Customer**: One of the three pre-seeded test customers (CUST-001 Mary Kija, CUST-002 John Banda, CUST-003 Aisha Phiri) whose accounts are migrated and given known demo PINs.
- **Sequential_Counter**: A persistent SQLite sequence (or `MAX(account_number) + 1` query) used to assign the next available zero-padded 6-digit account number.

---

## Requirements

### Requirement 1: Sequential Zero-Padded Account Numbers

**User Story:** As a system administrator, I want all account numbers to follow a consistent zero-padded 6-digit format starting at `000001`, so that account numbers are uniform, sortable, and unambiguous across the system.

#### Acceptance Criteria

1. THE `mock_accounts` table SHALL store `account_number` as a zero-padded 6-digit string (e.g. `"000001"`, `"000002"`, `"000003"`).
2. WHEN a new account is created and the table is empty, THE system SHALL assign `"000001"` as the first account number; WHEN the table is non-empty, THE system SHALL assign the next number by incrementing the current maximum numeric value and zero-padding the result to 6 digits.
3. IF two concurrent account creation requests arrive simultaneously, THEN each request SHALL receive a distinct `Account_Number` with no duplicates produced.
4. THE system SHALL migrate the existing demo accounts `"123456"` → `"000001"`, `"789012"` → `"000002"`, `"555666"` → `"000003"`, updating all foreign-key references in `mock_bills`, `mock_payments`, and `customer_auth`; IF the migration fails for any account, THEN the entire migration SHALL be rolled back and no partial changes SHALL persist.
5. WHEN a customer provides an account number with fewer than 6 digits, THE `BillingAgent` SHALL zero-pad the input to 6 digits before performing any lookup.
6. IF a customer provides an account number longer than 6 digits or containing non-numeric characters, THEN THE `BillingAgent` SHALL reject the input, prompt the customer to re-enter a valid 6-digit account number, and SHALL allow up to 3 re-entry attempts before ending the billing flow.
7. IF the account number counter reaches `"999999"`, THEN THE system SHALL reject new account creation with a descriptive error and SHALL NOT wrap around or produce a 7-digit number.

---

### Requirement 2: Customer Auth Table and PIN Storage

**User Story:** As a security engineer, I want customer PINs stored as salted PBKDF2-SHA256 hashes in a dedicated table, so that plaintext PINs are never persisted and a database breach does not expose customer credentials.

#### Acceptance Criteria

1. THE `Auth_Service` SHALL create a SQLite table named `customer_auth` with columns: `account_number TEXT PRIMARY KEY`, `pin_salt TEXT NOT NULL`, `pin_hash TEXT NOT NULL`, `failed_attempts INTEGER NOT NULL DEFAULT 0`, `locked_until TEXT`.
2. WHEN a PIN is set for an account, THE `Auth_Service` SHALL generate a cryptographically random 32-byte salt, encode it as a hexadecimal string, derive the hash using PBKDF2-SHA256 with at least 260,000 iterations, encode the hash as a hexadecimal string, and store only the encoded salt and hash — never the plaintext PIN.
3. THE `customer_auth` table SHALL be created (or schema-upgraded) during the `init_db()` call in `storage.py` so it is always present before any other operation runs.
4. IF a row for a given `account_number` already exists in `customer_auth`, THEN calling `set_pin` SHALL overwrite the existing salt, hash, `failed_attempts` (reset to `0`), and `locked_until` (reset to `NULL`) rather than inserting a duplicate.
5. THE `Auth_Service` SHALL expose a `set_pin(account_number: str, pin: str) -> None` function that validates the PIN format before hashing and storing it.
6. IF the PIN provided to `set_pin` is not exactly 4 decimal digits, THEN THE `Auth_Service` SHALL raise a `ValueError` whose message states that the PIN must be exactly 4 decimal digits, before any hashing occurs.
7. IF `set_pin` is called with an `account_number` that does not exist in `mock_accounts`, THEN THE `Auth_Service` SHALL raise a `ValueError` with no side effects on the `customer_auth` table.
8. WHEN `set_pin` completes successfully, THE `customer_auth` row for that account SHALL have `failed_attempts = 0` and `locked_until = NULL`.

---

### Requirement 3: PIN Verification

**User Story:** As a customer, I want to verify my identity with my 4-digit PIN before the bot returns my billing information, so that my account data is protected from unauthorised access.

#### Acceptance Criteria

1. WHEN a customer requests billing information, THE `BillingAgent` SHALL prompt for the customer's `Account_Number` if it is not already present in the conversation context.
2. WHEN the `BillingAgent` has an `Account_Number` but no verified PIN for the current session, THE `BillingAgent` SHALL prompt the customer to enter their 4-digit PIN before calling `get_bill`.
3. WHEN a customer submits a PIN, THE `Auth_Service` SHALL compare the candidate PIN hash against the stored `PIN_Hash` in a way that takes the same amount of time regardless of whether the PIN is correct or incorrect.
4. WHEN PIN verification succeeds, THE `BillingAgent` SHALL mark the session as PIN-verified in the conversation context and proceed to call `get_bill` with the verified `Account_Number`.
5. WHEN PIN verification succeeds, THE `Auth_Service` SHALL reset `failed_attempts` to `0` for that account.
6. IF PIN verification fails and the account is not locked, THEN THE `BillingAgent` SHALL inform the customer that the PIN is incorrect, state that they have `(3 - failed_attempts)` attempts remaining before the account is locked, and prompt for re-entry.
7. THE `BillingAgent` SHALL NOT call `get_bill` or return any billing data until PIN verification has succeeded for the current session.
8. WHEN the customer sends a new message after the conversation context has been reset (e.g. after typing "reset" or starting a fresh session), THE `BillingAgent` SHALL require PIN verification again on the next billing request.
9. IF PIN verification fails and the account is already locked, THEN THE `BillingAgent` SHALL inform the customer that the account is locked and state the approximate time remaining before the lock expires, without prompting for PIN re-entry.

---

### Requirement 4: Account Lockout

**User Story:** As a security engineer, I want accounts to be temporarily locked after 3 consecutive failed PIN attempts, so that brute-force PIN guessing is prevented.

#### Acceptance Criteria

1. WHEN a PIN verification attempt fails, THE `Auth_Service` SHALL increment `failed_attempts` for that `account_number` in `customer_auth` as part of the same operation as the verification check, so that the counter is always consistent with the number of failures.
2. WHEN `failed_attempts` reaches 3, THE `Auth_Service` SHALL set `locked_until` to the current UTC time plus 15 minutes and return a response that includes a locked indicator and the ISO 8601 unlock timestamp.
3. WHILE an account is locked (current UTC time is before `locked_until`), THE `Auth_Service` SHALL reject all PIN verification attempts and return a response that includes a locked indicator and the ISO 8601 unlock timestamp, without incrementing `failed_attempts` further.
4. WHILE an account is locked, THE `BillingAgent` SHALL inform the customer that the account is locked and state the time remaining before the lock expires, accurate to within 1 minute.
5. WHEN the current UTC time is at or after `locked_until`, THE `Auth_Service` SHALL treat the account as unlocked and allow PIN verification to proceed.
6. WHEN PIN verification succeeds on an account whose `locked_until` has expired, THE `Auth_Service` SHALL reset `failed_attempts` to `0`.
7. IF an admin resets the PIN for a locked account, THEN the account SHALL become immediately unlocked with `failed_attempts` reset to `0`.
8. WHEN a PIN verification attempt fails and `failed_attempts` is 1 or 2 (not yet locked), THE `Auth_Service` SHALL include the number of remaining attempts in its response so the `BillingAgent` can relay this to the customer.

---

### Requirement 5: Conversational PIN Flow in BillingAgent

**User Story:** As a customer using the WhatsApp bot, I want the bot to guide me through account number and PIN entry in a natural conversational sequence, so that authentication feels seamless and I always know what to do next.

#### Acceptance Criteria

1. WHEN a billing intent is detected and no `Account_Number` is in context, THE `BillingAgent` SHALL respond with a prompt asking for the 6-digit account number.
2. WHEN a billing intent is detected and an `Account_Number` is in context but the session is not PIN-verified, THE `BillingAgent` SHALL respond with a prompt asking for the 4-digit PIN.
3. WHEN the customer provides a PIN and verification succeeds, THE `BillingAgent` SHALL immediately return the billing information without asking for the PIN again in the same session.
4. WHEN the customer provides a PIN and verification fails, THE `BillingAgent` SHALL NOT reveal whether the account number exists; it SHALL only state that the PIN is incorrect and how many attempts remain.
5. WHEN the customer provides a PIN and the account is locked, THE `BillingAgent` SHALL state the account is temporarily locked and provide the time remaining before the lock expires, expressed in whole minutes.
6. WHEN the customer asks for billing information again within the same session after successful PIN verification, THE `BillingAgent` SHALL return the billing data directly without re-prompting for the PIN.
7. WHEN the conversation context is reset by any of the following events — the customer sends "reset", the customer starts a new session, or the session context is cleared by the system — THE `BillingAgent` SHALL require PIN verification again on the next billing request.
8. THE `BillingAgent` SHALL store the PIN-verified flag under the key `"pin_verified"` in the conversation context `entities` dict, set to `True` only after a successful `Auth_Service` verification call.

---

### Requirement 6: Admin PIN Reset Endpoint

**User Story:** As a system administrator, I want a protected API endpoint to reset a customer's PIN, so that I can assist customers who have forgotten their PIN or been locked out.

#### Acceptance Criteria

1. THE system SHALL expose a `POST /admin/accounts/{account_number}/reset-pin` endpoint that accepts a JSON body `{"new_pin": "<4-digit string>"}`.
2. WHEN a request is received at the reset endpoint, THE system SHALL verify the caller's admin token using the existing `auth_service.verify_token()` mechanism before processing the request.
3. IF the admin token is missing or invalid, THEN THE system SHALL return HTTP 401 with a JSON error body and SHALL NOT modify any PIN data.
4. IF the `account_number` path parameter does not exist in `mock_accounts`, THEN THE system SHALL return HTTP 404 with a descriptive JSON error body.
5. IF the `new_pin` value is not exactly 4 decimal digits, THEN THE system SHALL return HTTP 422 with a descriptive JSON error body.
6. WHEN all validations pass, THE system SHALL update `customer_auth` with the new PIN hash, reset `failed_attempts` to `0`, and clear `locked_until`; IF any part of this update fails, THEN the `customer_auth` row SHALL remain unchanged.
7. WHEN the reset succeeds, THE system SHALL return HTTP 200 with a JSON body `{"status": "ok", "account_number": "<account_number>"}`.
8. THE system SHALL write an audit log entry for every PIN reset request — including requests that fail validation — recording the admin user ID, the target account number, the outcome (success or failure reason), and the timestamp.

---

### Requirement 7: Demo Data Seeding

**User Story:** As a developer or tester, I want the three existing demo customers to have known PINs and migrated account numbers after the feature is deployed, so that I can test the full authentication flow without manual setup.

#### Acceptance Criteria

1. THE `_seed_mock_utility_data` function in `storage.py` SHALL migrate account numbers: `"123456"` → `"000001"`, `"789012"` → `"000002"`, `"555666"` → `"000003"`.
2. THE seeding function SHALL update all foreign-key references in `mock_bills` and `mock_payments` to use the new account numbers.
3. WHEN `init_db()` is called, THE system SHALL set PINs `"1234"` for `"000001"`, `"5678"` for `"000002"`, and `"9012"` for `"000003"` only if no PIN already exists for those accounts, so that re-running `init_db()` does not overwrite PINs that have already been changed.
4. WHEN the application starts with an existing database that still contains the old account numbers (`"123456"`, `"789012"`, `"555666"`), THE migration SHALL detect the old values and rename them before seeding PINs; IF only some old account numbers are present, THE migration SHALL process only those that remain.
5. THE seeded demo PINs SHALL be documented in a comment inside `storage.py` adjacent to the seed call so that developers can find them without reading this document.

---

### Requirement 8: Security and Non-Functional Properties

**User Story:** As a security engineer, I want the PIN authentication system to follow secure coding practices, so that customer data is protected against common attacks.

#### Acceptance Criteria

1. THE `Auth_Service` SHALL use `hmac.compare_digest` (or an equivalent constant-time comparison function) when comparing a candidate PIN hash against the stored `PIN_Hash`, so that the comparison takes the same time regardless of the result.
2. THE `Auth_Service` SHALL use PBKDF2-SHA256 with a minimum of 260,000 iterations (matching OWASP 2023 recommendations) for all PIN hashing operations.
3. THE system SHALL never include a plaintext PIN in any log message, API response body, or conversation reply.
4. WHEN the `BillingAgent` prompts for a PIN, THE bot reply SHALL NOT include the account number in the same message.
5. THE `customer_auth` table SHALL NOT be accessible through any endpoint that is not under the `/admin/` path prefix.
6. IF a request to the admin reset endpoint is made with a token that does not have admin privileges, THEN THE system SHALL return HTTP 403 and log the unauthorised access attempt.
7. THE `Auth_Service` SHALL validate that the `account_number` argument to all its public functions is a non-empty string of exactly 6 decimal digits before performing any database operation, raising `ValueError` otherwise.
