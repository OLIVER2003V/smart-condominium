# views_face_dry.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser
from rest_framework.authentication import TokenAuthentication

from .rekognition_client import search_by_image

class FaceIdentifyAWSDryRunView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        img = request.data.get("image")
        if not img:
            return Response({"ok": False, "detail": "image es requerido"}, status=400)
        img_bytes = img.read()
        try:
            result = search_by_image(img_bytes, max_faces=5)
            return Response({"ok": True, **result})
        except Exception as e:
            return Response({"ok": False, "detail": f"rekognition_error: {e.__class__.__name__}: {e}"}, status=502)
