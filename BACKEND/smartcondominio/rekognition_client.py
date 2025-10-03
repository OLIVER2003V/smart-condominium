import os, io, boto3
from typing import List, Dict, Any

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
COLLECTION_ID = os.getenv("REKOG_COLLECTION_ID", "smartcondo-faces")
MATCH_THRESHOLD = float(os.getenv("REKOG_MATCH_THRESHOLD", "90"))  # 0–100

_client = boto3.client("rekognition", region_name=AWS_REGION)

def ensure_collection():
    # Idempotente: crea si no existe
    cols = _client.list_collections().get("CollectionIds", [])
    if COLLECTION_ID not in cols:
        _client.create_collection(CollectionId=COLLECTION_ID)
    return COLLECTION_ID

def index_face(image_bytes: bytes, external_id: str) -> Dict[str, Any]:
    """
    Registra una cara en la colección con un external_image_id = external_id.
    Si hay varias caras, indexa todas (puedes filtrar si quieres solo la mayor).
    """
    ensure_collection()
    resp = _client.index_faces(
        CollectionId=COLLECTION_ID,
        Image={"Bytes": image_bytes},
        ExternalImageId=external_id,      # guarda tu person_id
        DetectionAttributes=[],            # atributos si quieres (AgeRange, etc.)
        QualityFilter="AUTO"               # filtra caras de baja calidad
    )
    # Devuelve faceIds creados
    return {
        "FaceRecords": [
            {"FaceId": fr["Face"]["FaceId"], "ExternalImageId": fr["Face"]["ExternalImageId"]}
            for fr in resp.get("FaceRecords", [])
        ]
    }

def search_by_image(image_bytes: bytes, max_faces: int = 5) -> Dict[str, Any]:
    """
    Busca en la colección por la cara más grande de la imagen.
    Devuelve matches con Similarity (%) y datos de la cara (ExternalImageId).
    """
    ensure_collection()
    resp = _client.search_faces_by_image(
        CollectionId=COLLECTION_ID,
        Image={"Bytes": image_bytes},
        FaceMatchThreshold=MATCH_THRESHOLD,  # % mínimo
        MaxFaces=max_faces,
        QualityFilter="AUTO"
    )
    matches = []
    for m in resp.get("FaceMatches", []):
        face = m["Face"]
        matches.append({
            "FaceId": face["FaceId"],
            "ExternalImageId": face.get("ExternalImageId"),
            "Similarity": float(m["Similarity"])  # 0..100
        })
    return {"Matches": matches}
