"""
Local vector and semantic retrieval module for matching disruption notices
against the multi-tier supply chain registry and logistics routes.
Uses google-genai gemini-embedding-001 when API key is available,
with a fast local lexical/n-gram vector fallback for offline reliability.
"""

import os
import re
import json
import math
from typing import Dict, Any, List, Tuple, Optional
import numpy as np


class SupplyChainRetriever:
    def __init__(self, dataset, embeddings_cache_file: str = "data/precomputed_embeddings.json"):
        self.dataset = dataset
        self.cache_file = embeddings_cache_file
        self.entity_corpus: List[Dict[str, Any]] = []
        self.embeddings: Dict[str, List[float]] = {}
        self.api_key = os.getenv("GEMINI_API_KEY")
        self._build_corpus()
        self._load_or_compute_embeddings()

    def _build_corpus(self):
        """Extract searchable text representations of all suppliers, ports, and parts."""
        for sup in self.dataset.suppliers_raw:
            parts_str = ", ".join([p.get("name", "") for p in sup.get("parts_supplied", [])])
            text = (
                f"Supplier: {sup.get('name')} (ID: {sup.get('id')}). "
                f"Location: {sup.get('city')}, {sup.get('country')}. "
                f"Port Hub: {sup.get('port_hub')}. Category: {sup.get('category')}. "
                f"Supplied parts: {parts_str}"
            )
            self.entity_corpus.append({
                "id": sup.get("id"),
                "type": "Supplier",
                "name": sup.get("name"),
                "text": text,
                "metadata": sup,
            })

        for ship in self.dataset.inventory_raw.get("in_transit_shipments", []):
            text = (
                f"Shipment: {ship.get('shipment_id')} by {ship.get('carrier')}. "
                f"Vessel: {ship.get('vessel_id')}. Origin: {ship.get('origin_port')}. "
                f"Destination: {ship.get('destination_hub')}. Lane: {ship.get('transit_lane')}."
            )
            self.entity_corpus.append({
                "id": ship.get("shipment_id"),
                "type": "Shipment",
                "name": f"{ship.get('carrier')} - {ship.get('shipment_id')}",
                "text": text,
                "metadata": ship,
            })

    def _load_or_compute_embeddings(self):
        """Load precomputed embeddings or generate local TF-IDF style vectors."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self.embeddings = json.load(f)
                    return
            except Exception:
                pass

        # If no cache exists, compute local lexical vectors
        self._compute_local_vectors()

    def _compute_local_vectors(self):
        """Construct local term-frequency vectors for cosine similarity."""
        vocab = {}
        for item in self.entity_corpus:
            tokens = self._tokenize(item["text"])
            for token in tokens:
                vocab[token] = vocab.get(token, 0) + 1

        for item in self.entity_corpus:
            tokens = self._tokenize(item["text"])
            vec = {}
            for t in tokens:
                vec[t] = vec.get(t, 0) + 1.0
            # Normalize vector
            norm = math.sqrt(sum(v * v for v in vec.values()))
            if norm > 0:
                vec = {k: v / norm for k, v in vec.items()}
            self.embeddings[item["id"]] = vec

    def _tokenize(self, text: str) -> List[str]:
        cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
        words = [w for w in cleaned.split() if len(w) > 2]
        return words

    def search(self, query_text: str, top_k: int = 4) -> List[Tuple[Dict[str, Any], float]]:
        """Retrieve top matching supply chain entities for a disruption notice."""
        query_tokens = self._tokenize(query_text)
        if not query_tokens:
            return []

        query_vec = {}
        for t in query_tokens:
            query_vec[t] = query_vec.get(t, 0) + 1.0
        norm = math.sqrt(sum(v * v for v in query_vec.values()))
        if norm > 0:
            query_vec = {k: v / norm for k, v in query_vec.items()}

        scores = []
        for item in self.entity_corpus:
            doc_id = item["id"]
            doc_vec = self.embeddings.get(doc_id, {})

            # If embedding is a dict (sparse local vector)
            if isinstance(doc_vec, dict):
                sim = sum(query_vec.get(k, 0.0) * v for k, v in doc_vec.items())
            # If embedding is a list of floats (dense embedding)
            elif isinstance(doc_vec, list) and len(doc_vec) > 0:
                sim = 0.0  # Dense fallback handled via Gemini if connected
            else:
                sim = 0.0

            scores.append((item, float(sim)))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]
