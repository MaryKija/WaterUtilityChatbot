"""backend/learning/intent_discovery.py

Dynamic intent discovery using sentence-transformers for agentic behavior.

This module enables the system to identify new conversation patterns
and create intent clusters beyond the predefined set, allowing for
autonomous adaptation to user needs.
"""

from __future__ import annotations

import json
import numpy as np
from typing import Dict, List, Tuple, Optional, Union, Any
from dataclasses import dataclass
from sklearn.cluster import DBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer
from sentence_transformers import SentenceTransformer
from scipy.sparse import csr_matrix
import sqlite3
from datetime import datetime

from ..config import config
from ..logger import logger
from ..intents import ALLOWED_INTENTS


@dataclass
class IntentCluster:
    """Represents a discovered intent cluster."""
    cluster_id: int
    centroid: str
    examples: List[str]
    confidence: float
    suggested_name: str
    is_known: bool = False


class IntentDiscoveryAgent:
    """Agentic intent discovery and clustering system."""
    
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
        self.min_samples_for_cluster = 3
        self.similarity_threshold = 0.7
        
    def encode_messages(self, messages: List[str]) -> np.ndarray:
        """Encode messages using sentence transformers."""
        try:
            embeddings = self.model.encode(messages, convert_to_numpy=True)
            return embeddings
        except Exception as e:
            logger.error(f"Error encoding messages: {e}")
            # Fallback to TF-IDF
            tfidf_matrix: Union[csr_matrix, Any] = self.vectorizer.fit_transform(messages)
            return tfidf_matrix.toarray()
    
    def discover_intents(self, messages: List[str], min_cluster_size: int = 3) -> List[IntentCluster]:
        """Discover intent clusters from conversation messages."""
        if len(messages) < min_cluster_size:
            logger.warning(f"Insufficient messages for clustering: {len(messages)} < {min_cluster_size}")
            return []
        
        try:
            # Encode messages
            embeddings = self.encode_messages(messages)
            
            # Use DBSCAN for density-based clustering (can discover arbitrary number of clusters)
            clustering = DBSCAN(eps=0.3, min_samples=min_cluster_size, metric='cosine')
            cluster_labels = clustering.fit_predict(embeddings)
            
            # Analyze clusters
            clusters = []
            unique_labels = set(cluster_labels)
            
            for label in unique_labels:
                if label == -1:  # Noise points in DBSCAN
                    continue
                    
                # Get messages in this cluster
                cluster_indices = [i for i, l in enumerate(cluster_labels) if l == label]
                cluster_messages = [messages[i] for i in cluster_indices]
                
                if len(cluster_messages) >= self.min_samples_for_cluster:
                    # Calculate cluster centroid
                    cluster_embeddings = embeddings[cluster_indices]
                    centroid = np.mean(cluster_embeddings, axis=0)
                    
                    # Find most representative message
                    representative_msg = self._find_representative_message(cluster_messages, centroid)
                    
                    # Check if similar to known intents
                    suggested_name, is_known = self._match_to_known_intent(representative_msg)
                    confidence = len(cluster_messages) / len(messages)
                    
                    cluster = IntentCluster(
                        cluster_id=int(label),
                        centroid=representative_msg,
                        examples=cluster_messages[:5],  # Keep top 5 examples
                        confidence=confidence,
                        suggested_name=suggested_name,
                        is_known=is_known
                    )
                    clusters.append(cluster)
            
            logger.info(f"Discovered {len(clusters)} intent clusters from {len(messages)} messages")
            return clusters
            
        except Exception as e:
            logger.error(f"Error in intent discovery: {e}")
            return []
    
    def _find_representative_message(self, messages: List[str], centroid: np.ndarray) -> str:
        """Find the message most similar to cluster centroid."""
        if len(messages) == 1:
            return messages[0]
        
        try:
            message_embeddings = self.encode_messages(messages)
            similarities = np.dot(message_embeddings, centroid)
            most_similar_idx = np.argmax(similarities)
            return messages[most_similar_idx]
        except:
            return messages[0]  # Fallback
    
    def _match_to_known_intent(self, message: str) -> Tuple[str, bool]:
        """Check if cluster matches any known intent."""
        message_lower = message.lower()
        
        # Simple keyword matching for known intents
        intent_keywords = {
            'leak_report': ['leak', 'burst', 'pipe', 'water leaking'],
            'billing_inquiry': ['bill', 'payment', 'charge', 'cost'],
            'new_connection': ['new', 'connect', 'install', 'setup'],
            'complaint_followup': ['follow up', 'status', 'update'],
            'meter_problem': ['meter', 'reading', 'measurement'],
            'payment_info': ['pay', 'payment method', 'how to pay'],
            'office_info': ['office', 'location', 'hours', 'contact'],
            'general_chat': ['hello', 'hi', 'help', 'question'],
        }
        
        for intent, keywords in intent_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                return intent, True
        
        # Generate new intent name based on content
        if any(word in message_lower for word in ['problem', 'issue', 'wrong', 'broken']):
            return 'issue_report', False
        elif any(word in message_lower for word in ['ask', 'question', 'want to know']):
            return 'information_request', False
        else:
            return 'unknown_intent', False
    
    def learn_from_conversation(self, user_id: str, message: str, intent_result: Dict) -> None:
        """Learn from conversation outcomes for future improvement."""
        try:
            # Store conversation data for learning
            self._store_learning_data(user_id, message, intent_result)
            
            # Periodically retrain models
            if self._should_retrain():
                self._retrain_models()
                
        except Exception as e:
            logger.error(f"Error learning from conversation: {e}")
    
    def _store_learning_data(self, user_id: str, message: str, intent_result: Dict) -> None:
        """Store conversation data for learning analytics."""
        # This would connect to a learning database
        # For now, just log the learning opportunity
        confidence = intent_result.get('confidence', 0.0)
        predicted_intent = intent_result.get('intent', 'unknown')
        
        if confidence > 0.8:  # Only learn from high-confidence predictions
            logger.info(f"Learning data: user={user_id}, intent={predicted_intent}, confidence={confidence}")
    
    def _should_retrain(self) -> bool:
        """Check if models should be retrained based on new data."""
        # Simple heuristic: retrain every 100 new high-confidence examples
        # In production, this would be more sophisticated
        return False  # Disable for now to avoid heavy computation
    
    def _retrain_models(self) -> None:
        """Retrain intent discovery models with new data."""
        # This would implement incremental learning
        logger.info("Model retraining triggered - not implemented yet")
        pass
    
    def suggest_intent_expansion(self, clusters: List[IntentCluster]) -> List[str]:
        """Suggest new intents to add to the system based on clusters."""
        suggestions = []
        
        for cluster in clusters:
            if not cluster.is_known and cluster.confidence > 0.05:  # 5% of messages
                suggestions.append(f"New intent '{cluster.suggested_name}' with {len(cluster.examples)} examples")
        
        return suggestions


# Global instance for agentic intent discovery
intent_discovery_agent = IntentDiscoveryAgent()
