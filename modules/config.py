"""Shared config. MODEL_NAME is the single source of truth for the embedding model, imported by
modules/matching.py, notebooks/encode_mpnet_lean.py and notebooks/02_embeddings.ipynb so job and
resume embeddings can't drift onto different models.
"""

MODEL_NAME = "multi-qa-mpnet-base-cos-v1"
