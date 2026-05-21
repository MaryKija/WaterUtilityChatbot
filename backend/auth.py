"""backend/auth.py

Authentication and authorization system for admin access.

This module provides:
- Token-based authentication for admin users
- Role-based access control (RBAC)
- PII protection for public endpoints
- Audit logging for admin actions
"""

from __future__ import annotations

import hashlib
import os
import secrets
import time
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum

from .logger import logger
from .storage import _connect, ADMIN_RESOLUTION_TABLE


class UserRole(Enum):
    """User roles with different permission levels."""
    CUSTOMER = "customer"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class Permission(Enum):
    """System permissions for role-based access control."""
    # Customer permissions
    VIEW_OWN_COMPLAINTS = "view_own_complaints"
    SUBMIT_COMPLAINTS = "submit_complaints"
    VIEW_OWN_BILLING = "view_own_billing"
    
    # Admin permissions
    VIEW_ALL_COMPLAINTS = "view_all_complaints"
    VIEW_DASHBOARD = "view_dashboard"
    MANAGE_RESOLUTIONS = "manage_resolutions"
    VIEW_ANALYTICS = "view_analytics"
    
    # Super admin permissions
    MANAGE_ADMINS = "manage_admins"
    VIEW_AUDIT_LOGS = "view_audit_logs"
    SYSTEM_CONFIG = "system_config"


@dataclass
class AdminUser:
    """Admin user account with role and permissions."""
    user_id: str
    username: str
    email: str
    role: UserRole
    permissions: List[Permission]
    created_at: str
    last_login: Optional[str] = None
    active: bool = True
    failed_login_attempts: int = 0
    locked_until: Optional[str] = None


@dataclass
class AuthToken:
    """Authentication token with metadata."""
    token_id: str
    user_id: str
    token_hash: str
    expires_at: str
    created_at: str
    last_used: Optional[str] = None
    permissions: List[Permission] = field(default_factory=list)
    active: bool = True


@dataclass
class AuditLog:
    """Audit log entry for security tracking."""
    log_id: str
    user_id: str
    action: str
    resource: str
    timestamp: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    success: bool = True
    details: Optional[Dict[str, Any]] = None


class AuthenticationError(Exception):
    """Authentication failed error."""
    pass


class AuthorizationError(Exception):
    """Authorization failed error."""
    pass


class AuthService:
    """Authentication and authorization service."""
    
    def __init__(self):
        # Default admin users (in production, these would be in database)
        self._default_admins = {
            "admin": {
                "user_id": "admin_001",
                "username": "admin",
                "email": "admin@waterutility.ai",
                "role": UserRole.ADMIN,
                "permissions": [
                    Permission.VIEW_ALL_COMPLAINTS,
                    Permission.VIEW_DASHBOARD,
                    Permission.MANAGE_RESOLUTIONS,
                    Permission.VIEW_ANALYTICS
                ],
                "created_at": datetime.now(timezone.utc).isoformat()
            },
            "superadmin": {
                "user_id": "admin_000", 
                "username": "superadmin",
                "email": "superadmin@waterutility.ai",
                "role": UserRole.SUPER_ADMIN,
                "permissions": list(Permission),  # All permissions
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        }
        
        # Token storage (in production, these would be in database)
        self._active_tokens: Dict[str, AuthToken] = {}
        
        # Initialize database tables for audit logging
        self._init_audit_tables()
    
    def _init_audit_tables(self):
        """Initialize audit logging and token persistence tables."""
        with _connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_logs (
                    log_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    success BOOLEAN NOT NULL,
                    details TEXT
                )
                """
            )
            # Persist session tokens so they survive server restarts
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_tokens (
                    token_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    token_secret TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_used TEXT,
                    active INTEGER NOT NULL DEFAULT 1
                )
                """
            )
            # Clean up expired tokens on startup
            conn.execute(
                "DELETE FROM auth_tokens WHERE expires_at < ?",
                (datetime.now(timezone.utc).isoformat(),)
            )
    
    def authenticate_user(self, username: str, password: str) -> AdminUser:
        """Authenticate user with username and password.

        Passwords are read from environment variables so they are never
        hardcoded in source.  Variable lookup order:
          1. ADMIN_PASSWORD_<USERNAME_UPPER>  (e.g. ADMIN_PASSWORD_ADMIN)
          2. ADMIN_DEFAULT_PASSWORD           (fallback for both accounts)

        If neither variable is set the login is rejected — this prevents
        accidental access when the env file has not been configured.
        """
        import hmac as _hmac

        if username not in self._default_admins:
            self._log_security_event("failed_login", "auth", {
                "username": username,
                "reason": "user_not_found",
            })
            raise AuthenticationError("Invalid credentials")

        # Resolve expected password from environment — never from source code
        env_key = f"ADMIN_PASSWORD_{username.upper()}"
        expected_pw = os.getenv(env_key) or os.getenv("ADMIN_DEFAULT_PASSWORD", "")

        if not expected_pw:
            self._log_security_event("failed_login", "auth", {
                "username": username,
                "reason": "password_not_configured",
            })
            raise AuthenticationError("Invalid credentials")

        # Constant-time comparison prevents timing-based enumeration
        if not _hmac.compare_digest(password, expected_pw):
            self._log_security_event("failed_login", "auth", {
                "username": username,
                "reason": "invalid_password",
            })
            raise AuthenticationError("Invalid credentials")

        user_data = self._default_admins[username].copy()
        user_data["last_login"] = datetime.now(timezone.utc).isoformat()

        self._log_security_event("successful_login", "auth", {
            "username": username,
            "user_id": user_data["user_id"],
        })

        return AdminUser(**user_data)
    
    def generate_token(self, user: AdminUser, expires_hours: int = 24) -> AuthToken:
        """Generate authentication token for user and persist it to SQLite."""
        token_id = f"TKN_{secrets.token_hex(16)}"
        token_secret = secrets.token_urlsafe(32)

        expires_at = (datetime.now(timezone.utc) + timedelta(hours=expires_hours)).isoformat()
        created_at = datetime.now(timezone.utc).isoformat()

        # Persist to database so the token survives server restarts
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO auth_tokens (token_id, user_id, token_secret, expires_at, created_at, active)
                VALUES (?, ?, ?, ?, ?, 1)
                """,
                (token_id, user.user_id, token_secret, expires_at, created_at),
            )

        self._log_security_event("token_generated", "auth", {
            "user_id": user.user_id,
            "token_id": token_id,
            "expires_at": expires_at,
        })

        return AuthToken(
            token_id=token_id,
            user_id=user.user_id,
            token_hash=token_secret,   # Return the secret to the caller
            expires_at=expires_at,
            created_at=created_at,
            permissions=user.permissions,
            active=True,
        )

    def verify_token(self, token: str) -> Optional[AdminUser]:
        """Verify authentication token against SQLite (survives restarts)."""
        if not token:
            return None

        now = datetime.now(timezone.utc).isoformat()

        with _connect() as conn:
            row = conn.execute(
                """
                SELECT token_id, user_id, expires_at, active
                FROM auth_tokens
                WHERE token_secret = ? AND active = 1 AND expires_at > ?
                """,
                (token, now),
            ).fetchone()

        if not row:
            self._log_security_event("invalid_token", "auth", {
                "reason": "not_found_or_expired",
            })
            return None

        token_id, user_id, expires_at, active = row

        # Update last_used timestamp
        with _connect() as conn:
            conn.execute(
                "UPDATE auth_tokens SET last_used = ? WHERE token_id = ?",
                (now, token_id),
            )

        # Resolve user from in-memory registry
        user_data = None
        for admin_data in self._default_admins.values():
            if admin_data["user_id"] == user_id:
                user_data = admin_data
                break

        if not user_data:
            return None

        return AdminUser(**user_data)

    def revoke_token(self, token: str) -> bool:
        """Revoke authentication token in SQLite."""
        with _connect() as conn:
            cur = conn.execute(
                "UPDATE auth_tokens SET active = 0 WHERE token_secret = ?",
                (token,),
            )
            revoked = cur.rowcount > 0

        if revoked:
            self._log_security_event("token_revoked", "auth", {"token_prefix": token[:12] + "..."})

        return revoked
    
    def check_permission(self, user: AdminUser, permission: Permission) -> bool:
        """Check if user has required permission."""
        return permission in user.permissions
    
    def require_permission(self, user: AdminUser, permission: Permission):
        """Require user to have specific permission or raise error."""
        if not self.check_permission(user, permission):
            self._log_security_event("permission_denied", "auth", {
                "user_id": user.user_id,
                "permission": permission.value,
                "user_role": user.role.value
            })
            raise AuthorizationError(f"Permission required: {permission.value}")
    
    def _log_security_event(self, action: str, resource: str, details: Dict[str, Any]):
        """Log security event for audit trail."""
        log_id = f"AUD_{secrets.token_hex(12)}"
        timestamp = datetime.now(timezone.utc).isoformat()
        
        audit_log = AuditLog(
            log_id=log_id,
            user_id=details.get("user_id", "system"),
            action=action,
            resource=resource,
            timestamp=timestamp,
            details=details
        )
        
        # Store in database
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO audit_logs (log_id, user_id, action, resource, timestamp, ip_address, user_agent, success, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit_log.log_id,
                    audit_log.user_id,
                    audit_log.action,
                    audit_log.resource,
                    audit_log.timestamp,
                    audit_log.ip_address,
                    audit_log.user_agent,
                    audit_log.success,
                    str(details) if audit_log.details else None
                )
            )
        
        # Also log to application logger
        logger.warning(
            f"security.{action}",
            extra={"extra_data": details}
        )


class PIIProtection:
    """PII protection for public endpoints."""
    
    @staticmethod
    def redact_complaint_data(complaint_data: Dict[str, Any], user_role: UserRole) -> Dict[str, Any]:
        """Redact PII from complaint data based on user role."""
        if user_role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            # Admins can see all data
            return complaint_data
        
        # For customers, redact sensitive information
        redacted = complaint_data.copy()
        
        # Redact full name, show only first initial
        if "name" in redacted:
            name = redacted["name"]
            if isinstance(name, str) and len(name) > 1:
                redacted["name"] = name[0] + "***"
        
        # Redact specific address details
        if "area" in redacted:
            area = redacted["area"]
            if isinstance(area, str) and len(area) > 10:
                redacted["area"] = area[:10] + "***"
        
        # Remove phone numbers if present
        if "phone" in redacted:
            redacted["phone"] = "***-***-****"
        
        # Remove email addresses if present
        if "email" in redacted:
            email = redacted["email"]
            if isinstance(email, str) and "@" in email:
                local, domain = email.split("@", 1)
                redacted["email"] = local[0] + "***@" + domain
        
        return redacted
    
    @staticmethod
    def redact_conversation_history(history: List[Dict[str, Any]], user_role: UserRole) -> List[Dict[str, Any]]:
        """Redact PII from conversation history."""
        if user_role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            return history
        
        redacted_history = []
        
        for entry in history:
            redacted_entry = entry.copy()
            
            # Redact PII from user messages
            if entry.get("role") == "user":
                text = entry.get("text", "")
                # Simple PII redaction patterns
                text = re.sub(r'\b\d{10,}\b', '***-***-****', text)  # Phone numbers
                text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '***@***.***', text)  # Emails
                text = re.sub(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', '*** ***', text)  # Names
                
                redacted_entry["text"] = text
            
            redacted_history.append(redacted_entry)
        
        return redacted_history


# Global auth service instance
auth_service = AuthService()


# Decorators for endpoint protection
def require_auth(permission: Optional[Permission] = None):
    """Decorator to require authentication and optional permission."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # This would be used with FastAPI dependencies
            # For now, return the function as-is
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_admin():
    """Decorator to require admin role."""
    return require_auth(Permission.VIEW_DASHBOARD)
