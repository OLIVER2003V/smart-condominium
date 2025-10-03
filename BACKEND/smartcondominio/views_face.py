import os
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from .rekognition_client import index_face, search_by_image
from .models import AccessEvent
from .serializers import AccessEventSerializer
from django.core.files.base import ContentFile

def build_person_id(kind: str, obj_id: int | str) -> str:
    k = (kind or "").lower()
    if k not in ("resident", "visitor", "staff"):
        raise ValueError("kind inválido")
    return f"{k}:{obj_id}"

class FaceRegisterAWSView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        kind = request.data.get("kind")
        obj_id = request.data.get("obj_id")
        img = request.data.get("image")
        if not kind or not obj_id or not img:
            return Response({"detail": "kind, obj_id, image son requeridos"}, status=400)

        person_id = build_person_id(kind, obj_id)
        data = index_face(img.read(), external_id=person_id)
        return Response({"ok": True, "person_id": person_id, **data})

class FaceIdentifyAndLogAWSView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        img = request.data.get("image")
        camera_id = request.data.get("camera_id") or ""
        if not img:
            return Response({"ok": False, "detail": "image es requerido"}, status=400)

        img_bytes = img.read()

        # 1) Buscar coincidencias en Rekognition
        try:
            result = search_by_image(img_bytes, max_faces=5)
        except Exception as e:
            return Response({"ok": False, "detail": f"rekognition_error: {e.__class__.__name__}: {e}"}, status=502)

        matches = result.get("Matches", [])
        match = bool(matches)
        best = matches[0] if match else None

        # 2) Mapear a tu AccessEvent (de placas) reutilizando campos
        #    - decision: ALLOW_RESIDENT / DENY_UNKNOWN
        #    - score: similarity (0..1)
        #    - reason: ExternalImageId (ej: resident:31)
        #    - payload: guardamos el resultado completo de Rekognition
        try:
            evt = AccessEvent.objects.create(
                camera_id=camera_id,
                plate_raw="",          # no aplica a rostros
                plate_norm="",         # no aplica
                score=(best["Similarity"] / 100.0) if match else None,
                decision="ALLOW_RESIDENT" if match else "DENY_UNKNOWN",
                reason=(best.get("ExternalImageId") if match else "no_match"),
                vehicle=None,
                visit=None,
                payload=result,        # guarda todo el dict de AWS
                triggered_by=getattr(request, "user", None),
            )
        except Exception as e:
            return Response({"ok": False, "detail": f"db_event_error: {e}"}, status=500)

        # 3) Responder
        try:
            data = AccessEventSerializer(evt).data
        except Exception as e:
            data = {"id": evt.id, "warn": f"serializer_error: {e}"}

        return Response({
            "ok": True,
            "match": match,
            "best": best,
            "candidates": matches,
            "event": data
        })
