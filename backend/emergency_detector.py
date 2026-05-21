"""backend/emergency_detector.py

Emergency detection and escalation system.

This module detects emergency situations and automatically escalates
to human agents or provides emergency contact information.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from .logger import logger


@dataclass
class EmergencyAlert:
    """Represents an emergency detection alert."""
    emergency_type: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    confidence: float
    detected_keywords: List[str]
    recommended_action: str
    emergency_contacts: List[str]


class EmergencyDetector:
    """Detects emergency situations in user messages."""
    
    def __init__(self):
        # Emergency keyword patterns with severity levels
        self.emergency_patterns = {
            # Medical emergencies
            "medical_emergency": {
                "severity": "CRITICAL",
                "keywords": [
                    "heart attack", "stroke", "unconscious", "not breathing", "chest pain",
                    "difficulty breathing", "severe bleeding", "emergency room", "ambulance",
                    "medical emergency", "fainted", "collapsed", "can't breathe"
                ],
                "action": "Call emergency medical services immediately",
                "contacts": ["Call 991 (Zambia Emergency Medical Services)"]
            },
            
            # Safety emergencies
            "safety_emergency": {
                "severity": "HIGH", 
                "keywords": [
                    "fire", "burning", "smoke", "explosion", "electrocution", "electric shock",
                    "gas leak", "chemical spill", "dangerous", "unsafe", "hazard", "emergency"
                ],
                "action": "Evacuate area and call emergency services",
                "contacts": ["Call 991 (Emergency)", "Call 993 (Fire Brigade)"]
            },
            
            # Water utility emergencies
            "utility_emergency": {
                "severity": "MEDIUM",
                "keywords": [
                    "main break", "water main burst", "flooding", "severe leak", "contamination",
                    "no water for days", "burst pipe", "water everywhere", "emergency repair"
                ],
                "action": "Contact water utility emergency line",
                "contacts": ["Water Utility Emergency: +260 211 000 999"]
            },
            
            # Financial emergencies
            "financial_emergency": {
                "severity": "LOW",
                "keywords": [
                    "disconnection notice", "water shut off", "urgent payment", "immediate payment",
                    "emergency bill", "can't pay", "financial hardship"
                ],
                "action": "Contact customer service for payment assistance",
                "contacts": ["Customer Service: +260 211 000 000"]
            }
        }
        
        # Distress indicators
        self.distress_patterns = [
            r"\b(help|urgent|emergency|asap|immediately|right now)\b",
            r"\b(danger|unsafe|risk|threat|hazard)\b",
            r"\b(scared|afraid|worried|panic|frightened)\b",
            r"\b(children|elderly|disabled|pregnant)\b.*\b(stuck|trapped|alone)\b"
        ]
    
    def detect_emergency(self, message: str, context: Optional[Dict] = None) -> Optional[EmergencyAlert]:
        """
        Detect if message indicates an emergency situation.
        
        Args:
            message: User message to analyze
            context: Conversation context for additional analysis
            
        Returns:
            EmergencyAlert if emergency detected, None otherwise
        """
        message_lower = message.lower()
        
        # Check each emergency category
        for emergency_type, config in self.emergency_patterns.items():
            matches = []
            confidence = 0.0
            
            # Check for keyword matches
            for keyword in config["keywords"]:
                if keyword in message_lower:
                    matches.append(keyword)
                    confidence += 0.3  # Base confidence per keyword
            
            # Check for distress patterns
            for pattern in self.distress_patterns:
                if re.search(pattern, message_lower):
                    confidence += 0.2
                    matches.append("distress_indicator")
            
            # Normalize confidence
            confidence = min(confidence, 1.0)
            
            # Require minimum confidence for emergency detection
            if confidence >= 0.4 and matches:
                logger.warning(
                    "emergency.detected",
                    extra={"extra_data": {
                        "emergency_type": emergency_type,
                        "severity": config["severity"],
                        "confidence": confidence,
                        "keywords": matches,
                        "message": message[:100] + "..." if len(message) > 100 else message
                    }}
                )
                
                return EmergencyAlert(
                    emergency_type=emergency_type,
                    severity=config["severity"],
                    confidence=confidence,
                    detected_keywords=matches,
                    recommended_action=config["action"],
                    emergency_contacts=config["contacts"]
                )
        
        return None
    
    def get_emergency_response(self, alert: EmergencyAlert) -> str:
        """Generate appropriate emergency response."""
        response_parts = [
            "EMERGENCY ALERT",
            "",
            f"I have detected a potential {alert.emergency_type.replace('_', ' ').title()}.",
            "",
            f"Recommended Action: {alert.recommended_action}",
            "",
            "Emergency Contacts:"
        ]
        
        for contact in alert.emergency_contacts:
            response_parts.append(f"- {contact}")
        
        response_parts.extend([
            "",
            "I am connecting you with a human agent immediately who can assist you further.",
            "",
            "Please stay safe and follow the recommended emergency procedures."
        ])
        
        return "\n".join(response_parts)
    
    def should_escalate_to_human(self, alert: EmergencyAlert) -> bool:
        """Determine if emergency requires immediate human escalation."""
        return alert.severity in ["HIGH", "CRITICAL"]
    
    def get_escalation_priority(self, alert: EmergencyAlert) -> str:
        """Get escalation priority for routing."""
        priority_map = {
            "CRITICAL": "URGENT",
            "HIGH": "HIGH", 
            "MEDIUM": "MEDIUM",
            "LOW": "NORMAL"
        }
        return priority_map.get(alert.severity, "NORMAL")


# Global emergency detector instance
emergency_detector = EmergencyDetector()
