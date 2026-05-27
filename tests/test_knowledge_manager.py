"""tests/test_knowledge_manager.py

Unit tests for backend/knowledge_manager.py.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch
import pytest
import numpy as np

from backend.knowledge_manager import KnowledgeManager, knowledge_manager


def test_global_instance_loaded():
    """Verify that the global knowledge_manager instance loaded facts successfully."""
    assert len(knowledge_manager.facts) > 0
    categories = {fact.get("category") for fact in knowledge_manager.facts}
    assert "tariffs" in categories
    assert "offices" in categories
    assert "procedures" in categories


def test_keyword_overlap_score():
    """Test token overlap scoring logic directly."""
    # Create a fresh temp instance to test cleanly
    km = KnowledgeManager()
    
    fact = {
        "keywords": [" Zanaco ", "Bank", "payment"],
        "content": "This is how you pay via ZANACO bank transfer."
    }
    
    # Perfect overlap on query words
    score1 = km._keyword_overlap_score(["zanaco", "bank"], fact)
    assert score1 == 1.0

    # Partial overlap
    score2 = km._keyword_overlap_score(["zanaco", "office", "leak"], fact)
    assert score2 == pytest.approx(1.0 / 3.0)

    # Zero overlap
    score3 = km._keyword_overlap_score(["office", "leak"], fact)
    assert score3 == 0.0


def test_fallback_search_without_transformer():
    """Test that when self.model is None, the ranker falls back fully to keyword search."""
    km = KnowledgeManager()
    km.model = None
    km.embeddings = None
    
    # We should still be able to successfully retrieve facts using keyword overlap
    context = km.get_relevant_context("Airtel MTN Mobile Money", k=1, threshold=0.1)
    assert context != ""
    assert "payment" in context.lower() or "money" in context.lower() or "mobile" in context.lower()


@patch("sentence_transformers.SentenceTransformer")
def test_graceful_fallback_on_init_failure(mock_transformer):
    """Verify that if SentenceTransformer fails to load, it falls back without raising an error."""
    mock_transformer.side_effect = RuntimeError("Neural model file not found offline.")
    
    # Should initialize without raising exception, but setting model/embeddings to None
    km = KnowledgeManager()
    
    assert km.model is None
    assert km.embeddings is None
    assert len(km.facts) > 0  # Facts are still loaded successfully!


def test_get_relevant_context_filtering():
    """Verify threshold and top-K filtering."""
    km = KnowledgeManager()
    km.model = None
    km.embeddings = None
    
    # Top 1 retrieval
    ctx_1 = km.get_relevant_context("Zanaco Bank Transfer", k=1, threshold=0.01)
    assert len(ctx_1.split("\n")) == 1
    
    # Trivial query returns nothing
    ctx_trivial = km.get_relevant_context("the a to", threshold=0.1)
    assert ctx_trivial == ""
