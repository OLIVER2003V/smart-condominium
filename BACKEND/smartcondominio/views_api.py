# === IMPORTS LIMPIOS Y CORREGIDOS ===
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.conf import settings  # ✅ necesario para STRIPE_*
from django.db import IntegrityError
from django.db.models import Q, Sum, F, DecimalField, ExpressionWrapper
from django.db.models.deletion import ProtectedError, RestrictedError
from django.utils.decorators import method_decorator  # ✅ para @method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.contrib.auth.models import Permission

from rest_framework import status, permissions, viewsets, filters, generics
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import (
    api_view, permission_classes, authentication_classes, action
)
from rest_framework.permissions import IsAuthenticated, AllowAny  # ✅ Allowny → AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet  # ✅

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from datetime import date
from decimal import Decimal
import csv
import stripe

from .models import Rol, Profile, Unidad, Cuota, Pago, Infraccion, OnlinePayment
from .permissions import IsAdmin
from .serializers import (
    RegisterSerializer, MeSerializer, AdminUserSerializer, MeUpdateSerializer,
    ChangePasswordSerializer, RolSimpleSerializer, PermissionBriefSerializer,
    UnidadSerializer, CuotaSerializer, PagoCreateSerializer, PagoSerializer,
    GenerarCuotasSerializer, InfraccionSerializer, PagoEstadoCuentaSerializer,
    UnidadBriefECSerializer, OnlinePayInitSerializer
)

User = get_user_model()
stripe.api_key = settings.STRIPE_API_KEY
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

# 👥 Admin de usuarios
class AdminUserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.select_related("profile__role").all().order_by("id")
    serializer_class = AdminUserSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]

    # búsquedas y orden
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["username", "first_name", "last_name", "email", "profile__role__code", "profile__role__name"]
    ordering_fields = ["id", "username", "email", "first_name", "last_name", "is_active"]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.pk == request.user.pk:
            return Response({"detail": "No puedes eliminar tu propia cuenta."},
                            status=status.HTTP_400_BAD_REQUEST)

        if getattr(instance, "is_superuser", False) and not getattr(request.user, "is_superuser", False):
            return Response({"detail": "Solo un superusuario puede eliminar a otro superusuario."},
                            status=status.HTTP_403_FORBIDDEN)

        if getattr(instance, "is_superuser", False) and not User.objects.filter(
            is_superuser=True, is_active=True
        ).exclude(pk=instance.pk).exists():
            return Response({"detail": "No se puede eliminar el último superusuario activo."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            self.perform_destroy(instance)
        except (ProtectedError, RestrictedError):
            return Response(
                {"detail": "No se puede eliminar: tiene registros relacionados (integridad referencial)."},
                status=status.HTTP_409_CONFLICT
            )
        except IntegrityError as e:
            return Response(
                {"detail": "No se puede eliminar por integridad referencial.", "error": str(e)},
                status=status.HTTP_409_CONFLICT
            )
        except Exception as e:
            return Response({"detail": "Error inesperado al eliminar.", "error": str(e)},
                            status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_204_NO_CONTENT)

# 🔒 Perfil del usuario autenticado
@api_view(["GET"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(MeSerializer(request.user).data)

@api_view(["PATCH"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def me_update(request):
    ser = MeUpdateSerializer(data=request.data, context={"request": request})
    ser.is_valid(raise_exception=True)
    user = ser.save()
    return Response(MeSerializer(user).data, status=status.HTTP_200_OK)

@api_view(["POST"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def change_password(request):
    ser = ChangePasswordSerializer(data=request.data, context={"request": request})
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response({"detail": "Contraseña actualizada correctamente."}, status=status.HTTP_200_OK)

# 🧩 Roles
class RolViewSet(viewsets.ModelViewSet):
    queryset = Rol.objects.all().order_by("code")
    serializer_class = RolSimpleSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]

    def destroy(self, request, *args, **kwargs):
        rol = self.get_object()
        if getattr(rol, "is_system", False):
            return Response({"detail":"No se puede borrar un rol de sistema."}, status=status.HTTP_400_BAD_REQUEST)
        if Profile.objects.filter(role=rol).exists():
            return Response({"detail":"No se puede borrar: hay usuarios usando este rol."}, status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"], url_path="add-permissions")
    def add_permissions(self, request, pk=None):
        rol = self.get_object()
        ids = request.data.get("permission_ids", [])
        perms = Permission.objects.filter(id__in=ids)
        rol.permissions.add(*perms)
        return Response(self.get_serializer(rol).data)

    @action(detail=True, methods=["post"], url_path="remove-permissions")
    def remove_permissions(self, request, pk=None):
        rol = self.get_object()
        ids = request.data.get("permission_ids", [])
        perms = Permission.objects.filter(id__in=ids)
        rol.permissions.remove(*perms)
        return Response(self.get_serializer(rol).data)
    
    @action(detail=True, methods=["get"], url_path="permissions")
    def list_permissions(self, request, pk=None):
        rol = self.get_object()
        perms = rol.permissions.select_related("content_type").all().order_by(
            "content_type__app_label", "codename"
        )
        data = PermissionBriefSerializer(perms, many=True).data
        return Response(data)

# ✅ Mejor: solo lectura con GET (list/retrieve) para catálogo de permisos
class PermissionViewSet(ReadOnlyModelViewSet):
    queryset = Permission.objects.select_related("content_type").all() \
        .order_by("content_type__app_label","codename")
    serializer_class = PermissionBriefSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_queryset(self):
        q = self.request.query_params.get("q")
        qs = super().get_queryset()
        if q:
            qs = qs.filter(
                Q(codename__icontains=q) |
                Q(name__icontains=q) |
                Q(content_type__app_label__icontains=q) |
                Q(content_type__model__icontains=q)
            )
        return qs
#-----UNIDAD GESTION
class UnidadViewSet(viewsets.ModelViewSet):
    queryset = Unidad.objects.select_related("propietario", "residente").all()
    serializer_class = UnidadSerializer

    authentication_classes = [TokenAuthentication]
    # Solo admin escribe; cualquiera autenticado puede leer (cámbialo si quieres solo admin total)
    permission_classes = [IsAuthenticated, IsAdmin]

    # backends correctos
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["torre", "bloque", "estado", "tipo", "is_active", "propietario", "residente"]
    search_fields = ["torre", "bloque", "numero"]
    ordering_fields = ["torre", "bloque", "numero", "updated_at"]
    ordering = ["torre", "bloque", "numero"]

    @action(methods=["post"], detail=True, url_path="desactivar")
    def desactivar(self, request, pk=None):
        obj = self.get_object()
        obj.is_active = False
        obj.estado = "INACTIVA"
        obj.save(update_fields=["is_active", "estado"])
        return Response(self.get_serializer(obj).data, status=status.HTTP_200_OK)

    @action(methods=["post"], detail=True, url_path="asignar")
    def asignar(self, request, pk=None):
        """
        Body: { "propietario": user_id | null, "residente": user_id | null }
        """
        obj = self.get_object()
        ser = self.get_serializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        obj = ser.save()
        return Response(self.get_serializer(obj).data, status=status.HTTP_200_OK)

#PAGOS Y CUOTAS
class CuotaViewSet(viewsets.ModelViewSet):
    queryset = Cuota.objects.select_related("unidad").all()
    serializer_class = CuotaSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]  # + tu IsAdmin si aplica

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["unidad", "periodo", "concepto", "estado", "is_active", "unidad__torre"]
    search_fields = ["periodo", "concepto", "unidad__torre", "unidad__bloque", "unidad__numero"]
    ordering_fields = ["vencimiento", "updated_at", "total_a_pagar", "pagado"]
    ordering = ["-periodo", "unidad_id"]

    # ---------- generar ----------
    def get_serializer_class(self):
        if getattr(self, "action", None) == "generar":
            return GenerarCuotasSerializer
        return super().get_serializer_class()

    @action(detail=False, methods=["post"], url_path="generar")
    def generar(self, request):
        s = self.get_serializer(data=request.data)  # GenerarCuotasSerializer
        s.is_valid(raise_exception=True)
        data = s.validated_data

        periodo        = data["periodo"]
        concepto       = data["concepto"]
        monto_base     = data["monto_base"]
        usa_coeficiente= data["usa_coeficiente"]
        vencimiento    = data["vencimiento"]

        afectadas = []
        for u in Unidad.objects.filter(is_active=True):
            c, _ = Cuota.objects.get_or_create(
                unidad=u, periodo=periodo, concepto=concepto, is_active=True,
                defaults={
                    "monto_base": monto_base,
                    "usa_coeficiente": usa_coeficiente,
                    "coeficiente_snapshot": u.coeficiente or 0,
                    "vencimiento": vencimiento,
                }
            )
            # actualizar si ya existía
            c.monto_base = monto_base
            c.usa_coeficiente = usa_coeficiente
            if usa_coeficiente:
                c.coeficiente_snapshot = u.coeficiente or 0
            c.vencimiento = vencimiento
            c.recalc_importes()
            c.recalc_estado()
            c.save()
            afectadas.append(c.id)

        return Response({"ok": True, "cuotas_afectadas": afectadas, "total": len(afectadas)}, status=status.HTTP_201_CREATED)

    # ---------- pagar desde la cuota ----------
    @action(detail=True, methods=["post"], url_path="pagos")
    def registrar_pago(self, request, pk=None):
        cuota = self.get_object()
        data = {**request.data, "cuota": cuota.id}  # forzar la cuota correcta
        ser = PagoCreateSerializer(data=data, context={"request": request})
        ser.is_valid(raise_exception=True)
        pago = ser.save()  # aplica automáticamente
        return Response(PagoSerializer(pago).data, status=status.HTTP_201_CREATED)

    # ---------- anular cuota ----------
    @action(detail=True, methods=["post"], url_path="anular")
    def anular_cuota(self, request, pk=None):
        cuota = self.get_object()
        if cuota.pagado > 0:
            return Response({"detail": "No se puede anular una cuota con pagos. Anule los pagos primero."}, status=400)
        cuota.is_active = False
        cuota.recalc_estado()
        cuota.save(update_fields=["is_active", "estado", "updated_at"])
        return Response(CuotaSerializer(cuota).data, status=200)

class PagoViewSet(viewsets.ModelViewSet):
    queryset = Pago.objects.select_related("cuota", "creado_por").all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]  # agrega tu IsAdmin si aplica
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["cuota", "valido", "medio"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        return PagoCreateSerializer if self.action == "create" else PagoSerializer

    def create(self, request, *args, **kwargs):
        ser_in = self.get_serializer(data=request.data, context={"request": request})
        ser_in.is_valid(raise_exception=True)
        pago = ser_in.save()
        ser_out = PagoSerializer(pago, context={"request": request})
        return Response(ser_out.data, status=status.HTTP_201_CREATED)
    
class InfraccionViewSet(viewsets.ModelViewSet):
    queryset = Infraccion.objects.select_related("unidad", "residente", "creado_por").all()
    serializer_class = InfraccionSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["unidad", "residente", "estado", "tipo", "is_active", "fecha"]
    search_fields = ["descripcion", "unidad__torre", "unidad__bloque", "unidad__numero"]
    ordering_fields = ["fecha", "monto", "updated_at"]
    ordering = ["-fecha"]

    def perform_create(self, serializer):
        serializer.save(creado_por=self.request.user)

    @action(detail=True, methods=["post"])
    def resolver(self, request, pk=None):
        obj = self.get_object()
        obj.estado = "RESUELTA"
        obj.save(update_fields=["estado", "updated_at"])
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=["post"])
    def anular(self, request, pk=None):
        obj = self.get_object()
        obj.estado = "ANULADA"
        obj.is_active = False
        obj.save(update_fields=["estado", "is_active", "updated_at"])
        return Response(self.get_serializer(obj).data)


class EstadoCuentaView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_user_unidades(self, user):
        # Unidades donde es propietario o residente
        return Unidad.objects.filter(Q(propietario=user) | Q(residente=user)).order_by("torre", "bloque", "numero")

    def get(self, request):
        user = request.user
        unidades = self.get_user_unidades(user)
        if not unidades.exists():
            return Response({"detail": "No tiene unidades asociadas."}, status=404)

        # unidad elegida (si no, la primera)
        unidad_id = request.query_params.get("unidad")
        if unidad_id:
            unidad = unidades.filter(id=unidad_id).first()
            if not unidad:
                return Response({"detail": "Unidad inválida para este usuario."}, status=403)
        else:
            unidad = unidades.first()

        # Cuotas de esa unidad (puedes ajustar límites si quieres)
        cuotas_qs = Cuota.objects.select_related("unidad").filter(unidad=unidad).order_by("-vencimiento", "-updated_at")

        # Pagos de esa unidad
        pagos_qs = Pago.objects.select_related("cuota", "creado_por", "cuota__unidad").filter(cuota__unidad=unidad).order_by("-created_at")

        # Resumen
        saldo_expr = ExpressionWrapper(F("total_a_pagar") - F("pagado"), output_field=DecimalField(max_digits=12, decimal_places=2))
        agg = cuotas_qs.aggregate(
            saldo_pendiente=Sum(saldo_expr),
            total_pagado=Sum("pagado"),
            total_cobrado=Sum("total_a_pagar"),
        )
        cuotas_pendientes = cuotas_qs.filter(estado__in=["PENDIENTE", "VENCIDO", "PARCIAL"]).count()
        ultimo_pago = pagos_qs.first()

        data = {
            "unidades": UnidadBriefECSerializer(unidades, many=True).data,
            "unidad": UnidadBriefECSerializer(unidad).data,
            "resumen": {
                "saldo_pendiente": str(agg.get("saldo_pendiente") or 0),
                "total_pagado_historico": str(agg.get("total_pagado") or 0),
                "total_cobrado_historico": str(agg.get("total_cobrado") or 0),
                "cuotas_pendientes": cuotas_pendientes,
                "ultimo_pago": PagoEstadoCuentaSerializer(ultimo_pago).data if ultimo_pago else None,
                "fecha_corte": date.today().isoformat(),
            },
            "cuotas": CuotaSerializer(cuotas_qs, many=True).data,
            "pagos": PagoEstadoCuentaSerializer(pagos_qs, many=True).data,
        }
        return Response(data, status=200)


class EstadoCuentaExportCSV(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_user_unidades(self, user):
        return Unidad.objects.filter(Q(propietario=user) | Q(residente=user)).order_by("torre", "bloque", "numero")

    def get(self, request):
        user = request.user
        unidades = self.get_user_unidades(user)
        if not unidades.exists():
            return Response({"detail": "No tiene unidades asociadas."}, status=404)

        unidad_id = request.query_params.get("unidad")
        if unidad_id:
            unidad = unidades.filter(id=unidad_id).first()
            if not unidad:
                return Response({"detail": "Unidad inválida para este usuario."}, status=403)
        else:
            unidad = unidades.first()

        cuotas_qs = Cuota.objects.select_related("unidad").filter(unidad=unidad).order_by("-vencimiento", "-updated_at")
        pagos_qs = Pago.objects.select_related("cuota", "cuota__unidad").filter(cuota__unidad=unidad).order_by("-created_at")

        # Generar CSV
        resp = HttpResponse(content_type="text/csv")
        filename = f"estado_cuenta_unidad_{unidad.id}_{date.today().isoformat()}.csv"
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        writer = csv.writer(resp)

        writer.writerow([f"Estado de cuenta - Unidad {unidad.torre}-{unidad.bloque}-{unidad.numero} (ID {unidad.id})"])
        writer.writerow(["Fecha de corte", date.today().isoformat()])
        writer.writerow([])

        writer.writerow(["CUOTAS"])
        writer.writerow(["ID", "Periodo", "Concepto", "Vencimiento", "Total", "Pagado", "Saldo", "Estado"])
        for c in cuotas_qs:
            saldo = (c.total_a_pagar or 0) - (c.pagado or 0)
            writer.writerow([c.id, c.periodo, c.concepto, c.vencimiento, c.total_a_pagar, c.pagado, saldo, c.estado])

        writer.writerow([])
        writer.writerow(["PAGOS"])
        writer.writerow(["ID", "Fecha pago", "Monto", "Medio", "Referencia", "Cuota (Periodo)", "Concepto"])
        for p in pagos_qs:
            writer.writerow([p.id, p.fecha_pago, p.monto, p.medio, p.referencia, getattr(p.cuota, "periodo", ""), getattr(p.cuota, "concepto", "")])

        return resp
#PAGO
class OnlinePayInitView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        s = OnlinePayInitSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        cuota = s.validated_data["cuota"]
        amount = s.validated_data["amount"]

        # Crear PaymentIntent (USD en test)
        intent = stripe.PaymentIntent.create(
            amount=int(Decimal(amount) * 100),  # centavos
            currency="usd",
            metadata={"cuota_id": cuota.id, "user_id": request.user.id},
            automatic_payment_methods={"enabled": True},
        )

        op = OnlinePayment.objects.create(
            cuota=cuota, amount=amount, currency="USD",
            provider="STRIPE", provider_intent_id=intent["id"],
            status=intent["status"].upper(), created_by=request.user,
            metadata={"client_secret": intent["client_secret"]},
        )

        # Comprobante provisional inicial
        provisional = {
            "online_payment_id": op.id,
            "provider": op.provider,
            "intent_id": op.provider_intent_id,
            "amount": str(op.amount),
            "currency": op.currency,
            "status": op.status,
        }

        return Response({"client_secret": intent["client_secret"], "provisional": provisional}, status=201)


# ✅ Webhook Stripe sin auth, con AllowAny y method_decorator correcto
@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(APIView):
    authentication_classes = []  # Stripe no envía token
    permission_classes = [AllowAny]

    def post(self, request):
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
        endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
        try:
            event = stripe.Webhook.construct_event(
                payload=payload,
                sig_header=sig_header,
                secret=endpoint_secret
            )
        except Exception:
            return HttpResponse(status=400)

        if event["type"] in ("payment_intent.succeeded", "payment_intent.payment_failed", "payment_intent.canceled"):
            pi = event["data"]["object"]
            intent_id = pi["id"]
            status_ = pi["status"].upper()

            op = OnlinePayment.objects.filter(
                provider_intent_id=intent_id
            ).select_related("cuota", "created_by").first()
            if not op:
                return HttpResponse(status=200)

            op.status = status_
            meta = op.metadata or {}
            meta.update({"last_event": event["type"]})
            op.metadata = meta
            op.save(update_fields=["status", "metadata", "updated_at"])

            if status_ == "SUCCEEDED":
                from decimal import Decimal as D
                if not Pago.objects.filter(referencia=intent_id, medio="ONLINE_STRIPE").exists():
                    pago = Pago.objects.create(
                        cuota=op.cuota,
                        monto=D(str(op.amount)),
                        medio="ONLINE_STRIPE",
                        referencia=intent_id,
                        valido=True,
                        creado_por=op.created_by,
                    )
                    pago.aplicar()
        return HttpResponse(status=200)