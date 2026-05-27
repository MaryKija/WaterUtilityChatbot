"""backend/knowledge_manager.py

In-memory knowledge manager for the Lukanga Water Supply and Sanitation Company (LgWSC).
Stores, indexes, and searches structured utility facts (tariffs, offices, procedures)
using keyword + semantic hybrid search.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np

from .logger import logger


class KnowledgeManager:
    """Manages utility knowledge base, providing keyword + semantic hybrid lookup."""

    def __init__(self, knowledge_dir: Optional[str] = None):
        if knowledge_dir:
            self.knowledge_dir = Path(knowledge_dir)
        else:
            self.knowledge_dir = Path(__file__).resolve().parent / "knowledge"

        self.facts: List[Dict[str, Any]] = []
        self.model: Any = None
        self.embeddings: Optional[np.ndarray] = None

        self.load_knowledge()
        self.initialize_semantic_search()

    def load_knowledge(self) -> None:
        """Load structured facts from JSON files in the knowledge directory."""
        self.facts = []
        if not self.knowledge_dir.exists():
            logger.warning(f"Knowledge directory {self.knowledge_dir} does not exist.")
            return

        for filename in ["tariffs.json", "offices.json", "procedures.json"]:
            filepath = self.knowledge_dir / filename
            if not filepath.exists():
                logger.warning(f"Knowledge file {filepath} not found.")
                continue

            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.facts.extend(data)
                        logger.info(f"Loaded {len(data)} facts from {filename}")
                    else:
                        logger.warning(f"Invalid format in {filename}: expected a list.")
            except Exception as e:
                logger.error(f"Error loading knowledge file {filename}: {e}")

    def initialize_semantic_search(self) -> None:
        """Initialize SentenceTransformer and pre-embed all loaded facts."""
        if not self.facts:
            logger.warning("No facts loaded. Skipping semantic search initialization.")
            return

        try:
            from sentence_transformers import SentenceTransformer
            # Using the pre-installed high-quality lightweight model matching the intent discovery agent
            logger.info("Initializing SentenceTransformer('all-MiniLM-L6-v2')...")
            self.model = SentenceTransformer("all-MiniLM-L6-v2")
            
            # Combine title and content to form the search document
            documents = [f"{fact.get('title', '')}\n{fact.get('content', '')}" for fact in self.facts]
            
            # Compute embeddings and normalize them for easy cosine similarity (dot product)
            self.embeddings = self.model.encode(
                documents, 
                convert_to_numpy=True, 
                normalize_embeddings=True,
                show_progress_bar=False
            )
            logger.info(f"Successfully embedded {len(self.facts)} utility facts for semantic search.")
        except Exception as e:
            logger.warning(
                f"SentenceTransformer initialization failed: {e}. "
                "KnowledgeManager will gracefully fall back to keyword-only search."
            )
            self.model = None
            self.embeddings = None

    def _keyword_overlap_score(self, query_words: List[str], fact: Dict[str, Any]) -> float:
        """Compute normalized word overlap score between a query and a fact."""
        if not query_words:
            return 0.0

        # Extract fact terms
        fact_keywords = {w.lower() for w in fact.get("keywords", [])}
        content_text = fact.get("content", "").lower() + " " + fact.get("title", "").lower()
        content_words = set(re.findall(r"\b\w{3,}\b", content_text))  # ignore very short words
        
        all_fact_words = fact_keywords.union(content_words)

        overlap = sum(1 for w in query_words if w in all_fact_words)
        return float(overlap / len(query_words))

    def get_relevant_context(
        self, 
        query: str, 
        k: int = 2, 
        threshold: float = 0.15, 
        alpha: float = 0.5
    ) -> str:
        """Perform keyword + semantic hybrid search to retrieve the top K relevant facts.

        Args:
            query: The user query string.
            k: Number of relevant facts to retrieve.
            threshold: Minimum relevance score required.
            alpha: Mixing weight for search scoring (alpha * semantic + (1 - alpha) * keyword).

        Returns:
            A clean formatted string of relevant facts, or empty string.
        """
        cleaned_query = (query or "").strip()
        if not cleaned_query:
            return ""

        # Clean and tokenize query words (ignoring short words and common stop words)
        STOP_WORDS = {
            "the", "and", "for", "you", "with", "your", "this", "that", "how", "what", 
            "where", "who", "when", "why", "are", "have", "has", "had", "can", "but", 
            "not", "from", "out", "off", "our", "their", "them", "they", "she", "his", 
            "her", "him", "its", "one", "two", "all", "any", "some", "such", "than", 
            "very", "about", "above", "after", "again", "against", "into", "over", 
            "under", "will", "would", "shall", "should"
        }
        query_words = [
            w.lower() for w in re.findall(r"\b\w{3,}\b", cleaned_query)
            if w.lower() not in STOP_WORDS
        ]
        if not query_words:
            return ""

        fact_scores = []

        # If semantic embeddings are active, embed query once
        query_emb = None
        if self.model is not None and self.embeddings is not None:
            try:
                query_emb = self.model.encode(cleaned_query, normalize_embeddings=True)
            except Exception as e:
                logger.error(f"Failed to encode query semantic embedding: {e}")

        for i, fact in enumerate(self.facts):
            # 1. Keyword Score
            keyword_score = self._keyword_overlap_score(query_words, fact)

            # 2. Semantic Score
            semantic_score = 0.0
            if query_emb is not None and self.embeddings is not None:
                # Normalised dot product is equivalent to cosine similarity
                semantic_score = float(np.dot(self.embeddings[i], query_emb))
                # Map from [-1, 1] range to [0, 1] range
                semantic_score = max(0.0, (semantic_score + 1.0) / 2.0)

            # 3. Hybrid Score
            if self.model is not None:
                score = alpha * semantic_score + (1.0 - alpha) * keyword_score
            else:
                score = keyword_score  # Full keyword search fallback

            fact_scores.append((fact, score))

        # Sort by score descending
        fact_scores.sort(key=lambda x: x[1], reverse=True)

        # Filter above threshold and select top K
        retrieved = []
        for fact, score in fact_scores:
            if score >= threshold:
                retrieved.append(fact)
            if len(retrieved) >= k:
                break

        if not retrieved:
            return ""

        # Format context block
        formatted_lines = []
        for fact in retrieved:
            formatted_lines.append(f"- {fact.get('title', 'Fact')}: {fact.get('content', '')}")

        return "\n".join(formatted_lines)


# Global singleton instance of the KnowledgeManager
knowledge_manager = KnowledgeManager()
