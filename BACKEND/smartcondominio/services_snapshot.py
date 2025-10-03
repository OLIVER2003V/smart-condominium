# services_snapshot.py
import requests
from django.conf import settings

SNAPSHOT_URL = "https://api.platerecognizer.com/v1/plate-reader/"

def _normalize_regions(regions):
    if not regions:
        return []
    if isinstance(regions, (list, tuple, set)):
        return [str(r).strip() for r in regions if str(r).strip()]
    return [r.strip() for r in str(regions).split(",") if r.strip()]

class PlateRecognizerSnapshot:
    @staticmethod
    def read_image(fileobj, regions=None, camera_id=None, timeout=12):
        headers = {"Authorization": f"Token {settings.PLATE_RECOG_TOKEN}"}
        data = []
        for r in _normalize_regions(regions or settings.PLATE_REGIONS):
            data.append(("regions", r))
        if camera_id:
            data.append(("camera_id", camera_id))

        resp = requests.post(
            SNAPSHOT_URL,
            headers=headers,
            files={"upload": fileobj},
            data=data,  # lista de tuplas => múltiples 'regions'
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()

def best_plate_from_result(payload: dict):
    results = (payload or {}).get("results", [])
    if not results:
        return "", None
    best = results[0]
    return (best.get("plate") or "").upper(), best.get("score")
