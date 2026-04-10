"""backend/intent_pipeline.py

Advanced hybrid intent classification pipeline with:
1. Rule-based classification for obvious intents
2. Lightweight AI classifier for common cases
3. LLM classifier for complex cases
4. Ensemble voting with confidence calibration
5. Entity extraction and refinement
6. Context-aware disambiguation
7. Classification telemetry
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime


from .config import config
from .intents import ALLOWED_INTENTS_SET
from .logger import logger
from .llm.groq_client import classify_intent as groq_classify_intent


@dataclass
class ClassificationResult:
    """Structured classification result with metadata."""
    intent: str
    confidence: float
    entities: Dict[str, Any]
    source: str
    timestamp: Optional[str] = None
    ensemble_votes: Dict[str, float] = field(default_factory=dict)
    disambiguation_needed: bool = False
    reasoning: str = ""

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.ensemble_votes is None:
            self.ensemble_votes = {}

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "intent": self.intent,
            "confidence": self.confidence,
            "entities": self.entities,
            "source": self.source,
            "timestamp": self.timestamp,
            "disambiguation_needed": self.disambiguation_needed,
        }


class IntentPipeline:
    """Advanced hybrid intent classification pipeline."""

    def __init__(self):
        self.rule_patterns = {
            "general_chat": [
                r"\b(hi|hello|hey|good\s+(morning|afternoon|evening)|thanks?|thank\s+you)\b",
                r"\b(how\s+are\s+you|what's\s+up|how\s+do\s+you\s+do)\b",
                r"\b(who\s+are\s+you|what\s+are\s+you|what\s+do\s+you\s+do)\b",
            ],
            "billing_inquiry": [
                r"\b(bill|billing|balance|check.*bill|my.*bill)\b",
                r"\b(account|owe|due|charges?|how.*much)\b",
                r"\b(check|view)\s+(?:my\s+)?(?:account|bill|balance)\b",
            ],
            "report_fault": [
                r"\b(no\s+water|water\s+is\s+off|water\s+cut|water\s+outage)\b",
                r"\b(leak|leaking|burst\s+pipe|burst\s+water\s+pipe|pipe\s+burst)\b",
                r"\b(dirty\s+water|water\s+is\s+dirty|contaminated\s+water)\b",
                r"\b(low\s+pressure|water\s+pressure\s+low)\b",
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
            "new_connection": [
                r"new\s+connection",
                r"need.*new.*connection",
            ],
            "payment_info": [
                r"\b(how\s+to\s+pay|payment\s+methods?|pay|options?)\b",
                r"\b(mobile|money|bank|transfer|cash|office)\b.*\b(payment|pay)\b",
            ],
        }

    def classify(self, message: str, context: dict) -> dict:
        """Run advanced hybrid intent classification pipeline with ensemble voting."""
        message_lower = message.lower().strip()

        # Step 1: Extract entities
        entities = self._extract_entities(message, context)

        # Step 2: Get classifications from all sources
        rule_result = self._rule_based_classify(message_lower)
        lightweight_result = self._lightweight_classify(message, context)
        llm_result = self._llm_classify(message, context)

        # Step 3: Ensemble voting with weighted calibration
        ensemble_result = self._ensemble_vote(
            [rule_result, lightweight_result, llm_result],
            message,
            context
        )

        # Step 4: Merge entities
        ensemble_result["entities"].update(entities)

        # Step 5: Confidence calibration based on source reliability
        ensemble_result = self._calibrate_confidence(ensemble_result, message_lower)

        return ensemble_result

    def _extract_entities(self, message: str, context: dict) -> Dict[str, Any]:
        """Extract entities from message (locations, account numbers, etc)."""
        entities = {}
        message_lower = message.lower()

        # Extract account/reference numbers (WC-XXXX or ticket IDs)
        ticket_match = re.search(r'\b(wc-\d+|\d{8,})\b', message_lower)
        if ticket_match:
            entities["ticket_id"] = ticket_match.group(1).upper()

        # Extract location/area mentions
        area_keywords = ["kabwe", "lusaka", "ndola", "kitwe", "livingstone", "chingola", "mufulira"]
        for area in area_keywords:
            if area in message_lower:
                entities["area"] = area.capitalize()
                break

        # Extract account number patterns
        account_match = re.search(r'\b\d{6,}\b', message)
        if account_match and not ticket_match:
            entities["account_number"] = account_match.group(0)

        # Extract named entities for complaint details
        if "leak" in message_lower or "burst" in message_lower:
            entities["fault_type"] = "leak" if "leak" in message_lower else "burst_pipe"
        elif "no water" in message_lower or "outage" in message_lower:
            entities["fault_type"] = "outage"
        elif "dirty" in message_lower or "contaminated" in message_lower:
            entities["fault_type"] = "water_quality"
        elif "pressure" in message_lower:
            entities["fault_type"] = "low_pressure"

        return entities

    def _ensemble_vote(self, results: List[dict], message: str, context: dict) -> dict:
        """Ensemble voting with weighted confidence calibration."""
        if not results:
            return ClassificationResult(
                intent="out_of_scope",
                confidence=0.0,
                entities={},
                source="ensemble",
                reasoning="No classification results available"
            ).to_dict()

        # Assign weights based on source reliability
        source_weights = {
            "rule": 1.3,      # Rule-based is highly reliable
            "lightweight": 1.0,  # Baseline
            "llm": 0.9,       # LLM slightly lower confidence
        }

        # Create weighted vote dictionary
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

        # Calculate normalized confidence per intent based on agreeing sources.
        ensemble_votes = {
            intent: vote_data["score_sum"] / vote_data["weight_sum"]
            for intent, vote_data in weighted_votes.items()
            if vote_data["weight_sum"] > 0
        }

        # Get highest voted intent
        top_intent = max(ensemble_votes, key=lambda k: ensemble_votes[k])
        top_confidence = ensemble_votes[top_intent]

        # Check for disambiguation
        disambiguation_needed = False
        clarification_options = []

        if top_confidence < 0.7:
            # Low confidence - may need disambiguation
            sorted_intents = sorted(ensemble_votes.items(), key=lambda x: x[1], reverse=True)
            if len(sorted_intents) >= 2:
                top1_score = sorted_intents[0][1]
                top2_score = sorted_intents[1][1]
                if top1_score - top2_score < 0.15:  # Close race
                    disambiguation_needed = True
                    clarification_options = [sorted_intents[0][0], sorted_intents[1][0]]

        reasoning = f"Ensemble voted: {top_intent} (confidence: {top_confidence:.2f}) from {len(results)} classifiers"

        return ClassificationResult(
            intent=top_intent if not disambiguation_needed else "clarification_needed",
            confidence=top_confidence,
            entities={},
            source="ensemble",
            ensemble_votes=ensemble_votes,
            disambiguation_needed=disambiguation_needed,
            reasoning=reasoning
        ).to_dict()

    def _calibrate_confidence(self, result: dict, message_lower: str) -> dict:
        """Calibrate confidence based on message length and clarity."""
        intent = result.get("intent", "out_of_scope")
        confidence = result.get("confidence", 0.0)

        # Adjust for message length (shorter = more ambiguous)
        word_count = len(message_lower.split())
        if word_count < 3:
            confidence *= 0.85  # Reduce confidence for very short messages
        elif word_count > 20:
            confidence *= 0.9  # Slight reduction for very long messages

        # Boost confidence for clear intents with specific keywords
        high_signal_keywords = {
            "general_chat": ["hi", "hello", "hey", "how are you"],
            "billing_inquiry": ["budget", "amount due", "balance"],
            "report_fault": ["leak", "burst", "outage", "no water"],
            "new_connection": ["new connection", "apply", "install"],
            "escalation": ["agent", "speak", "human", "representative"],
        }

        if intent in high_signal_keywords:
            if any(kw in message_lower for kw in high_signal_keywords[intent]):
                confidence = min(0.98, confidence * 1.05)  # Boost but cap at 0.98

        # Ensure confidence is in valid range
        result["confidence"] = max(0.0, min(1.0, confidence))
        return result

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

        # Check for billing-related (PRIORITY HIGH)
        billing_keywords = ["bill", "billing", "balance", "account", "check.*bill", "my bill", "owe", "due"]
        if any(re.search(kw, message_lower) for kw in billing_keywords):
            return {
                "intent": "billing_inquiry",
                "confidence": 0.95,
                "entities": {},
                "source": "lightweight"
            }

        # Check for complaints
        complaint_keywords = ["leak", "burst", "fault", "problem", "issue", "no water", "water cut", "pressure", "spraying"]
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

        # Check for new connection
        connection_keywords = ["new connection", "apply for connection", "set up connection"]
        if any(phrase in message_lower for phrase in connection_keywords):
            return {
                "intent": "new_connection",
                "confidence": 0.8,
                "entities": {},
                "source": "lightweight"
            }

        # Check for new connection
        connection_keywords = ["new connection", "apply for connection", "set up connection"]
        if any(phrase in message_lower for phrase in connection_keywords):
            return {
                "intent": "new_connection",
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
                "confidence": 0.1,
                "entities": {},
                "source": "llm"
            }

    def _arbitrate(self, results: list[dict]) -> dict:
        """Legacy method - kept for compatibility. Use ensemble_vote instead."""
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
