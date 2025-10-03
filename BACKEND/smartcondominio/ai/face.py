# BACKEND/smartcondominio/ai/face.py
import os, json
from pathlib import Path
import numpy as np
import cv2
from functools import lru_cache
from sklearn.metrics.pairwise import cosine_similarity

from django.conf import settings

# InsightFace
from insightface.app import FaceAnalysis

DATA_DIR = Path(settings.MEDIA_ROOT) / "face_data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
VECTORS_PATH = DATA_DIR / "vectors.jsonl"

THRESHOLD = float(getattr(settings, "FACE_THRESHOLD", 0.40))

@lru_cache(maxsize=1)
def _get_face_app():
    """
    Carga única del modelo ArcFace (CPU).
    Se mantiene en memoria durante el proceso de Django.
    """
    app = FaceAnalysis(name="buffalo_l")
    app.prepare(ctx_id=-1, det_size=(640, 640))  # CPU
    return app

def _read_image(file_bytes: bytes):
    arr = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return img

def embed_from_bytes(file_bytes: bytes):
    app = _get_face_app()
    img = _read_image(file_bytes)
    if img is None:
        return None
    faces = app.get(img)
    if not faces:
        return None
    face = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0])*(f.bbox[3]-f.bbox[1]))
    return face.normed_embedding.astype(np.float32)

def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    return float(cosine_similarity([a], [b])[0][0])

def register_embedding(person_id: str, file_bytes: bytes) -> dict:
    emb = embed_from_bytes(file_bytes)
    if emb is None:
        return {"ok": False, "detail": "No face detected"}
    item = {"person_id": person_id, "embedding": emb.tolist()}
    with open(VECTORS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(item) + "\n")
    return {"ok": True, "person_id": person_id}

def identify_bytes(file_bytes: bytes, threshold: float | None = None, top_k: int = 5) -> dict:
    thr = threshold if threshold is not None else THRESHOLD
    probe = embed_from_bytes(file_bytes)
    if probe is None:
        return {"ok": False, "detail": "No face detected"}

    if not VECTORS_PATH.exists():
        return {"ok": True, "match": False, "best_id": None, "best_similarity": None, "candidates": []}

    sims = []
    with open(VECTORS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            v = np.array(row["embedding"], dtype=np.float32)
            sims.append((row["person_id"], cosine_sim(probe, v)))

    if not sims:
        return {"ok": True, "match": False, "best_id": None, "best_similarity": None, "candidates": []}

    sims.sort(key=lambda x: x[1], reverse=True)
    best_id, best_sim = sims[0]
    return {
        "ok": True,
        "match": best_sim >= thr,
        "best_id": best_id,
        "best_similarity": float(best_sim),
        "candidates": [{"person_id": pid, "similarity": float(s)} for pid, s in sims[:top_k]],
    }
