"""Standalone mpnet encoding for 02_embeddings.ipynb -- running this in-notebook OOM'd on 7.3GB
RAM, so it runs alone with a smaller batch size and caches to notebooks/.cache/ (gitignored).
Re-run directly to regenerate the cache: venv/Scripts/python notebooks/encode_mpnet_lean.py

Reads data/jobs_entry.csv (not jobs_entry_skills.csv) and extracts skills/languages itself via
modules/job_text.py, using the current modules/skill_dictionary.py. jobs_entry_skills.csv is only
produced by notebook 02 section 6, which itself needs this script's cache to get that far --
reading it here would be circular, and would silently re-embed whichever skill_dictionary.py was
current the last time notebook 02 ran, not now.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))
from modules.config import MODEL_NAME  # noqa: E402
from modules.job_text import build_texts, extract_skills_and_languages, hash_texts  # noqa: E402

BATCH_SIZE = 8
OUT_DIR = ROOT / "notebooks" / ".cache"
OUT_DIR.mkdir(exist_ok=True)

jobs = pd.read_csv(ROOT / "data" / "jobs_entry.csv")

print("Extracting skills/languages with the current dictionary ...", flush=True)
t0 = time.time()
jobs = extract_skills_and_languages(jobs)
print(f"Extraction took {time.time() - t0:.1f}s", flush=True)

texts = build_texts(jobs)
texts_hash = hash_texts(texts)
del jobs

print(f"Loading {MODEL_NAME} ...", flush=True)
model = SentenceTransformer(MODEL_NAME)
print("max_seq_length:", model.max_seq_length, flush=True)

t0 = time.time()
embeddings = model.encode(
    texts, batch_size=BATCH_SIZE, normalize_embeddings=True, show_progress_bar=True
).astype(np.float32)
elapsed = time.time() - t0
print(f"\nmpnet embedding took {elapsed:.1f}s, shape {embeddings.shape}", flush=True)

np.save(OUT_DIR / "mpnet_embeddings.npy", embeddings)
(OUT_DIR / "mpnet_encode_meta.json").write_text(
    json.dumps({"model": MODEL_NAME, "texts_hash": texts_hash, "encode_time_s": elapsed,
                "batch_size": BATCH_SIZE, "shape": list(embeddings.shape)})
)
print("Saved to", OUT_DIR / "mpnet_embeddings.npy", flush=True)
