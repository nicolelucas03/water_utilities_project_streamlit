# modules/semantic_index.py

import os
import json
import hashlib
import pandas as pd
from typing import Dict, Any, List

import chromadb
from chromadb.utils import embedding_functions

EMBED_MODEL_NAME = "all-MiniLM-L6-v2"  
COLLECTION_NAME = "water_semantic_index"
META_DOC_ID = "__meta__"


class SemanticIndex:
    """
    Vector index over:
      - dataset descriptions
      - column descriptions + notes + sample values

    Embeddings are cached on disk via Chroma's PersistentClient.
    We also store a lightweight 'signature' of the dataset config + file mtimes.
    If that signature changes, we automatically rebuild the index.
    """

    def __init__(self, datasets_config: Dict[str, Dict[str, Any]], persist_dir: str = "chroma_db"):
        self.datasets_config = datasets_config
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBED_MODEL_NAME
        )

        # Always attach embedding function when we get/create collection
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self.embedding_fn,
        )

        # Compute a signature of the current datasets config + CSV mtimes
        self.current_signature = self._compute_signature(datasets_config)

        # Decide whether to reuse or rebuild
        self._ensure_index_is_up_to_date()


    def _compute_signature(self, datasets_config: Dict[str, Dict[str, Any]]) -> str:
        """
        Build a stable hash of:
          - dataset_name
          - path
          - file mtime (if exists)
          - description
          - column_notes

        If a CSV changes or the config changes, this signature will change.
        """
        payload = []

        for dataset_name, cfg in sorted(datasets_config.items()):
            path = cfg.get("path", "")
            description = cfg.get("description", "")
            column_notes = cfg.get("column_notes", "")

            if os.path.exists(path):
                mtime = os.path.getmtime(path)
            else:
                mtime = None

            payload.append({
                "dataset_name": dataset_name,
                "path": path,
                "mtime": mtime,
                "description": description,
                "column_notes": column_notes,
            })

        payload_json = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()

    def _get_stored_signature(self) -> str:
        """
        Try to read the stored signature from the special meta doc.
        Returns '' if not present.
        """
        try:
            meta = self.collection.get(ids=[META_DOC_ID])
        except Exception:
            return ""

        if not meta or not meta.get("ids"):
            return ""

        if not meta["ids"]:
            return ""

        # We store the signature as the document text for META_DOC_ID
        docs = meta.get("documents", [[]])
        if not docs or not docs[0]:
            return ""

        return docs[0]

    def _store_signature(self, signature: str) -> None:
        """
        Store the current signature as a special document in the collection.
        Overwrite if already present.
        """
        # Delete old meta doc if it exists
        try:
            self.collection.delete(ids=[META_DOC_ID])
        except Exception:
            pass

        self.collection.add(
            documents=[signature],
            metadatas=[{"kind": "meta"}],
            ids=[META_DOC_ID],
        )


    def _ensure_index_is_up_to_date(self) -> None:
        """
        If the collection is empty, (first run) -> build index and store signature.
        If there's a stored signature and it != current_signature -> rebuild.
        Otherwise, reuse cached embeddings.
        """
        count = self.collection.count()

        if count == 0:
            # Fresh collection: build from scratch
            print("[SemanticIndex] Empty collection – building index...")
            self._build_index()
            self._store_signature(self.current_signature)
            return

        stored_signature = self._get_stored_signature()

        if stored_signature == "":
            print("[SemanticIndex] No stored signature – rebuilding index once for safety...")
            self._rebuild_index()
            return

        if stored_signature != self.current_signature:
            print("[SemanticIndex] Dataset config or files changed – rebuilding semantic index...")
            self._rebuild_index()
        else:
            print("[SemanticIndex] Using cached semantic index (signatures match).")

    def _rebuild_index(self) -> None:
        """
        Delete the old collection and rebuild everything.
        """
        # Drop and recreate collection with same name and embedding fn
        self.client.delete_collection(COLLECTION_NAME)
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self.embedding_fn,
        )
        self._build_index()
        self._store_signature(self.current_signature)


    def _build_index(self) -> None:
        docs: List[str] = []
        metadatas: List[Dict[str, Any]] = []
        ids: List[str] = []

        for dataset_name, cfg in self.datasets_config.items():
            path = cfg["path"]
            if not os.path.exists(path):
                print(f"[SemanticIndex] Missing file for dataset '{dataset_name}': {path}")
                continue

            df = pd.read_csv(path)
            column_notes = cfg.get("column_notes", "")

            # Dataset-level doc
            dataset_doc = f"""
DATASET: {dataset_name}
DESCRIPTION: {cfg.get("description", "")}
COLUMNS: {', '.join(df.columns)}
""".strip()
            docs.append(dataset_doc)
            metadatas.append({"kind": "dataset", "dataset": dataset_name})
            ids.append(f"dataset::{dataset_name}")

            # Column-level docs
            for col in df.columns:
                values = df[col].dropna().unique()[:5]
                values_str = ", ".join(map(str, values))

                note = ""
                for line in column_notes.splitlines():
                    if col in line:
                        note = line.strip()
                        break

                text = f"""
DATASET: {dataset_name}
COLUMN: {col}
NOTE: {note}
EXAMPLE_VALUES: {values_str}
""".strip()

                docs.append(text)
                metadatas.append({
                    "kind": "column",
                    "dataset": dataset_name,
                    "column": col,
                })
                ids.append(f"column::{dataset_name}::{col}")

        if docs:
            self.collection.add(documents=docs, metadatas=metadatas, ids=ids)
            print(f"[SemanticIndex] Indexed {len(docs)} docs (datasets + columns).")
        else:
            print("[SemanticIndex] No docs to index.")


    def retrieve(self, question: str, top_k: int = 8) -> List[Dict[str, Any]]:
        """
        Return top-k relevant docs (datasets + columns) for a question.
        """
        results = self.collection.query(
            query_texts=[question],
            n_results=top_k,
        )

        items: List[Dict[str, Any]] = []
        if not results["ids"] or len(results["ids"][0]) == 0:
            return items

        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            items.append({
                "text": doc,
                "metadata": meta,
            })
        return items


