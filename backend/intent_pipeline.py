"""backend/intent_pipeline.py

Hybrid intent classification pipeline.

Combines:
1. Rule-based classification for obvious intents
2. Lightweight AI classifier for common cases
3. LLM classifier for complex cases
4. Arbitration to select highest-confidence result
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

import requests

from .config import config
from .intents import ALLOWED_INTENTS_SET
from .logger import logger
from .llm.groq_client import classify_intent as groq_classify_intent


class IntentPipeline:
    """Hybrid intent classification pipeline."""

    def __init__(self):
        self.rule_patterns = {
            "general_chat": [
                r"\b(hi|hello|hey|good\s+(morning|afternoon|evening)|thanks?|thank\s+you)\b",
                r"\b(how\s+are\s+you|what's\s+up|how\s+do\s+you\s+do)\b",
                r"\b(who\s+are\s+you|what\s+are\s+you|what\s+do\s+you\s+do)\b",
            ],
            "report_fault": [
                r"\b(no\s+water|water\s+is\s+off|water\s+cut|water\s+outage)\b",
                r"\b(leak|leaking|burst\s+pipe|pipe\s+burst)\b",
                r"\b(dirty\s+water|water\s+is\s+dirty|contaminated\s+water)\b",
                r"\b(low\s+pressure|water\s+pressure\s+low)\b",
            ],
            "billing_inquiry": [
                r"\b(bill|billing|account|balance|charges?|due|payment)\b",
                r"\b(how\s+much|what\s+is\s+my|check\s+my)\b.*\b(bill|balance|account)\b",
            ],
            "complaint_followup": [
                r"\b(ticket|reference|wc-|status|check|update)\b",
                r"\b(complaint|issue|problem|fault)\b.*\b(status|update|check)\b",
            ],
            "escalation": [
                r"\b(speak\s+to|talk\s+to|connect\s+me|transfer\s+me)\b.*\b(agent|person|human|representative)\b",
                r"\b(agent|human|person|representative|manager|supervisor)\b",
            ],
            "office_info": [
                r"\b(office|location|address|hours|open|close|contact|phone|email)\b",
                r"\b(where\s+is|how\s+to\s+find|directions?)\b",
            ],
            "payment_info": [
                r"\b(payment|pay|how\s+to\s+pay|payment\s+methods?|options?)\b",
                r"\b(mobile|money|bank|transfer|cash|office)\b.*\b(payment|pay)\b",
            ],
        }

    def classify(self, message: str, context: dict) -> dict:
        """Run hybrid intent classification pipeline."""
        message_lower = message.lower().strip()

        # Step 1: Rule-based classification
        rule_result = self._rule_based_classify(message_lower)
        if rule_result["confidence"] >= 0.9:
            rule_result["source"] = "rule"
            return rule_result

        # Step 2: Lightweight AI classification
        lightweight_result = self._lightweight_classify(message, context)
        if lightweight_result["confidence"] >= 0.8:
            lightweight_result["source"] = "lightweight"
            return lightweight_result

        # Step 3: LLM classification
        llm_result = self._llm_classify(message, context)
        llm_result["source"] = "llm"

        # Step 4: Arbitration
        return self._arbitrate([rule_result, lightweight_result, llm_result])

    def _rule_based_classify(self, message_lower: str) -> dict:
        """Rule-based classification for obvious intents."""
        for intent, patterns in self.rule_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower, re.IGNORECASE):
                    return {
                        "intent": intent,
                        "confidence": 0.9,
                        "entities": {},
                        "source": "rule"
                    }

        return {
            "intent": "out_of_scope",
            "confidence": 0.1,
            "entities": {},
            "source": "rule"
        }

    def _lightweight_classify(self, message: str, context: dict) -> dict:
        """Lightweight AI classification using patterns and context."""
        # Simple keyword-based classification with context awareness
        message_lower = message.lower()

        # Check for greetings
        if any(word in message_lower for word in ["hi", "hello", "hey", "good morning", "good afternoon"]):
            return {
                "intent": "general_chat",
                "confidence": 0.85,
                "entities": {},
                "source": "lightweight"
            }

        # Check for billing-related
        billing_keywords = ["bill", "billing", "account", "balance", "payment", "due", "amount"]
        if any(word in message_lower for word in billing_keywords):
            return {
                "intent": "billing_inquiry",
                "confidence": 0.75,
                "entities": {},
                "source": "lightweight"
            }

        # Check for complaints
        complaint_keywords = ["leak", "fault", "problem", "issue", "no water", "water cut", "pressure"]
        if any(phrase in message_lower for phrase in complaint_keywords):
            return {
                "intent": "report_fault",
                "confidence": 0.8,
                "entities": {},
                "source": "lightweight"
            }

        # Check for follow-up
        followup_keywords = ["ticket", "reference", "wc-", "status", "check", "update"]
        if any(word in message_lower for word in followup_keywords):
            return {
                "intent": "complaint_followup",
                "confidence": 0.8,
                "entities": {},
                "source": "lightweight"
            }

        return {
            "intent": "out_of_scope",
            "confidence": 0.3,
            "entities": {},
            "source": "lightweight"
        }

    def _llm_classify(self, message: str, context: dict) -> dict:
        """LLM-based classification for complex cases."""
        try:
            return groq_classify_intent(message, context)
        except Exception as e:
            logger.warning(f"LLM classification failed: {e}")
            return {
                "intent": "out_of_scope",
                "confidence": 0.5,
                "entities": {},
                "source": "llm"
            }

    def _arbitrate(self, results: list[dict]) -> dict:
        """Arbitrate between multiple classification results."""
        if not results:
            return {
                "intent": "out_of_scope",
                "confidence": 0.0,
                "entities": {},
                "source": "arbitration"
            }

        # Sort by confidence
        sorted_results = sorted(results, key=lambda x: x.get("confidence", 0), reverse=True)
        top_result = sorted_results[0]

        # Check if top two results are close (within 0.1 confidence)
        if len(sorted_results) >= 2:
            top_conf = top_result.get("confidence", 0)
            second_conf = sorted_results[1].get("confidence", 0)

            if top_conf - second_conf <= 0.1 and top_conf < 0.7:
                # Close results, request clarification
                logger.info(f"Arbitration: close results between {top_result['intent']} ({top_conf:.2f}) and {sorted_results[1]['intent']} ({second_conf:.2f})")
                return {
                    "intent": "clarification_needed",
                    "confidence": 0.5,
                    "entities": {},
                    "source": "arbitration",
                    "clarification_options": [top_result["intent"], sorted_results[1]["intent"]]
                }

        # Return highest confidence result
        top_result["source"] = "arbitration"
        return top_result


# Global pipeline instance
intent_pipeline = IntentPipeline()