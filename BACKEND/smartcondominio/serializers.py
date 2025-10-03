# serializers.py
from decimal import Decimal
import re

from django.contrib.auth import get_user_model, authenticate, password_validation
from django.contrib.auth.models import Permission
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from rest_framework import serializers

from .models import (
    Profile, Rol, Unidad, Cuota, Pago, Infraccion,
    StaffKind, Visitor, Visit,
    AreaComun,
    Tarea, TareaComentario,
    Vehiculo, SolicitudVehiculo,
    Aviso,
    MockReceipt, OnlinePaymentIntent, AccessEvent
)

User = get_user_model()
PERIODO_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


# ------------------------------ utils ------------------------------
def value_gt(a, b) -> bool:
    try:
        return Decimal(a) > Decimal(b)
    except Exception:
        return False


def _resolve_role(role_id=None, role_code=None, default_code="RESIDENT"):
    try:
        if role_id is not None:
            return Rol.objects.get(id=role_id)
        if role_code:
            code = str(role_code).strip().upper()
            return Rol.objects.get(code=code)
        return Rol.objects.get(code=default_code)
    except Rol.DoesNotExist:
        raise serializers.ValidationError({"role": "Rol no encontrado (id/code inválido)."})


# ------------------------------ Me ------------------------------
class MeSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    role_base = serializers.SerializerMethodField()
    staff_kind = serializers.SerializerMethodField()
    staff_kind_id = serializers.SerializerMethodField()
    staff_kind_text = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "role", "role_base", "staff_kind", "staff_kind_id", "staff_kind_text",
        ]

    def get_role(self, obj):
        try:
            return getattr(obj.profile.role, "code", "RESIDENT")
        except ObjectDoesNotExist:
            return "RESIDENT"

    def get_role_base(self, obj):
        try:
            return getattr(obj.profile.role, "base", None)
        except ObjectDoesNotExist:
            return None

    def get_staff_kind(self, obj):
        try:
            sk = getattr(obj.profile, "staff_kind", None)
            if sk:
                return sk.name
            txt = getattr(obj.profile, "staff_kind_text", "") or ""
            return txt or None
        except ObjectDoesNotExist:
            return None

    def get_staff_kind_id(self, obj):
        try:
            return getattr(getattr(obj.profile, "staff_kind", None), "id", None)
        except ObjectDoesNotExist:
            return None

    def get_staff_kind_text(self, obj):
        try:
            return getattr(obj.profile, "staff_kind_text", "") or ""
        except ObjectDoesNotExist:
            return ""


# ------------------------------ Registro / Login / Perfil ------------------------------
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    role_id = serializers.IntegerField(required=False, write_only=True)
    role_code = serializers.CharField(required=False, write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "password", "role_id", "role_code"]

    @transaction.atomic
    def create(self, validated_data):
        role_id = validated_data.pop("role_id", None)
        role_code = validated_data.pop("role_code", None)
        user = User.objects.create_user(**validated_data)
        role = _resolve_role(role_id, role_code, default_code="RESIDENT")
        Profile.objects.update_or_create(user=user, defaults={"role": role})
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data["username"], password=data["password"])
        if not user:
            raise serializers.ValidationError("Credenciales inválidas")
        if not user.is_active:
            raise serializers.ValidationError("Usuario inactivo")
        data["user"] = user
        return data


class LoginResponseSerializer(serializers.Serializer):
    token = serializers.CharField()
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    role = serializers.CharField()


ROLE_EDITABLE_FIELDS = {
    "ADMIN": {"first_name", "last_name", "email", "username"},
    "STAFF": {"first_name", "last_name", "email"},
    "RESIDENT": {"first_name", "last_name", "email"},
}


class MeUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    email = serializers.EmailField(required=False)
    username = serializers.CharField(required=False, allow_blank=False, max_length=150)

    def validate(self, attrs):
        user = self.context["request"].user
        code = getattr(getattr(getattr(user, "profile", None), "role", None), "code", "RESIDENT")
        allowed = ROLE_EDITABLE_FIELDS.get(code, set())

        not_allowed = set(attrs.keys()) - allowed
        for k in list(not_allowed):
            attrs.pop(k, None)

        UserModel = get_user_model()
        if "username" in attrs and UserModel.objects.exclude(pk=user.pk).filter(username=attrs["username"]).exists():
            raise serializers.ValidationError({"username": "Ya está en uso."})
        if "email" in attrs and UserModel.objects.exclude(pk=user.pk).filter(email=attrs["email"]).exists():
            raise serializers.ValidationError({"email": "Ya está en uso."})
        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        for k, v in self.validated_data.items():
            setattr(user, k, v)
        user.save()
        return user


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=6)

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["current_password"]):
            raise serializers.ValidationError({"current_password": "No coincide."})
        password_validation.validate_password(attrs["new_password"], user=user)
        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user


# ------------------------------ Admin users ------------------------------
class AdminUserSerializer(serializers.ModelSerializer):
    # lectura
    role = serializers.SerializerMethodField(read_only=True)
    role_base = serializers.SerializerMethodField(read_only=True)
    staff_kind = serializers.SerializerMethodField(read_only=True)
    # escritura
    role_id = serializers.IntegerField(required=False, write_only=True)
    role_code = serializers.CharField(required=False, write_only=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, min_length=6)
    staff_kind_id = serializers.IntegerField(required=False, write_only=True, allow_null=True)
    staff_kind_text = serializers.CharField(required=False, write_only=True, allow_blank=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name", "is_active",
            "role", "role_base", "role_id", "role_code",
            "staff_kind", "staff_kind_id", "staff_kind_text",
            "password",
        ]

    # lectura
    def get_role(self, instance):
        try:
            return getattr(instance.profile.role, "code", "RESIDENT")
        except ObjectDoesNotExist:
            return "RESIDENT"

    def get_role_base(self, instance):
        try:
            return getattr(instance.profile.role, "base", None)
        except ObjectDoesNotExist:
            return None

    def get_staff_kind(self, instance):
        try:
            p = instance.profile
            if p.staff_kind:
                return p.staff_kind.name
            return p.staff_kind_text or None
        except ObjectDoesNotExist:
            return None

    # unicidad
    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        UserModel = get_user_model()

        if instance:
            if "username" in attrs and UserModel.objects.exclude(pk=instance.pk).filter(username=attrs["username"]).exists():
                raise serializers.ValidationError({"username": "Ya está en uso."})
            if "email" in attrs and attrs.get("email") and UserModel.objects.exclude(pk=instance.pk).filter(email=attrs["email"]).exists():
                raise serializers.ValidationError({"email": "Ya está en uso."})
        else:
            if "username" in attrs and UserModel.objects.filter(username=attrs["username"]).exists():
                raise serializers.ValidationError({"username": "Ya está en uso."})
            if "email" in attrs and attrs.get("email") and UserModel.objects.filter(email=attrs["email"]).exists():
                raise serializers.ValidationError({"email": "Ya está en uso."})
        return attrs

    # helpers
    def _apply_role_and_staff_kind(self, user, role_id, role_code, staff_kind_id, staff_kind_text):
        role = _resolve_role(role_id, role_code, default_code="RESIDENT")
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.role = role

        if getattr(role, "base", None) == "STAFF":
            sk_obj = None
            if staff_kind_id is not None:
                if staff_kind_id:
                    try:
                        # Usa "active" si tu modelo StaffKind tiene ese campo,
                        # o cambia a is_active=True si corresponde.
                        sk_obj = StaffKind.objects.get(pk=staff_kind_id, active=True)
                    except StaffKind.DoesNotExist:
                        raise serializers.ValidationError({"staff_kind_id": "Tipo de personal inválido."})
            profile.staff_kind = sk_obj
            profile.staff_kind_text = (staff_kind_text or "").strip()
        else:
            profile.staff_kind = None
            profile.staff_kind_text = ""

        profile.save(update_fields=["role", "staff_kind", "staff_kind_text"])

    # create/update
    @transaction.atomic
    def create(self, validated_data):
        role_id = validated_data.pop("role_id", None)
        role_code = validated_data.pop("role_code", None)
        password = validated_data.pop("password", None)
        staff_kind_id = validated_data.pop("staff_kind_id", None)
        staff_kind_text = validated_data.pop("staff_kind_text", "")

        user = User(**validated_data)
        user.set_password(password or User.objects.make_random_password())
        user.save()

        self._apply_role_and_staff_kind(user, role_id, role_code, staff_kind_id, staff_kind_text)
        return user

    @transaction.atomic
    def update(self, instance, validated_data):
        role_id = validated_data.pop("role_id", None)
        role_code = validated_data.pop("role_code", None)
        password = validated_data.pop("password", None)
        staff_kind_id = validated_data.pop("staff_kind_id", None)
        staff_kind_text = validated_data.pop("staff_kind_text", "")

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password and password.strip():
            instance.set_password(password)
        instance.save()

        if role_id is not None or role_code is not None or staff_kind_id is not None or staff_kind_text is not None:
            self._apply_role_and_staff_kind(instance, role_id, role_code, staff_kind_id, staff_kind_text)
        return instance


# ------------------------------ Permisos / Roles ------------------------------
class PermissionBriefSerializer(serializers.ModelSerializer):
    content_type = serializers.SerializerMethodField()

    class Meta:
        model = Permission
        fields = ["id", "codename", "name", "content_type"]

    def get_content_type(self, obj):
        return f"{obj.content_type.app_label}.{obj.content_type.model}"


class RolSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = ["id", "code", "name", "description", "is_system", "base"]
        read_only_fields = ["id", "is_system"]

    def validate_code(self, value):
        v = value.strip().upper()
        if " " in v:
            raise serializers.ValidationError("El code no debe contener espacios.")
        return v


# ------------------------------ Unidades / Cuotas / Pagos ------------------------------
class UnidadSerializer(serializers.ModelSerializer):
    propietario_nombre = serializers.CharField(source="propietario.get_full_name", read_only=True)
    residente_nombre = serializers.CharField(source="residente.get_full_name", read_only=True)

    # alias compat (entrada)
    torre = serializers.CharField(write_only=True, required=False, allow_blank=True)
    bloque = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Unidad
        fields = [
            "id",
            "manzana", "lote", "numero", "piso",
            "tipo", "metraje", "coeficiente",
            "dormitorios", "parqueos", "bodegas",
            "estado", "is_active",
            "propietario", "propietario_nombre",
            "residente", "residente_nombre",
            "created_at", "updated_at",
            "torre", "bloque",
        ]
        read_only_fields = ["created_at", "updated_at", "is_active"]

    def validate(self, attrs):
        # map aliases
        if not attrs.get("manzana") and "torre" in attrs:
            attrs["manzana"] = (attrs.pop("torre") or "").strip()
        if not attrs.get("lote") and "bloque" in attrs:
            attrs["lote"] = (attrs.pop("bloque") or "").strip()

        for k in ("manzana", "lote", "numero"):
            if k in attrs and attrs[k] is not None:
                attrs[k] = str(attrs[k]).strip()

        estado = attrs.get("estado", getattr(self.instance, "estado", None))
        residente = attrs.get("residente", getattr(self.instance, "residente", None))
        if residente and estado == "DESOCUPADA":
            raise serializers.ValidationError({"estado": "Si hay residente, la unidad no puede estar 'Desocupada'."})

        manzana = attrs.get("manzana", getattr(self.instance, "manzana", None))
        lote = attrs.get("lote", getattr(self.instance, "lote", None))
        numero = attrs.get("numero", getattr(self.instance, "numero", None))

        if manzana and numero:
            qs = Unidad.objects.filter(manzana=manzana, lote=lote, numero=numero, is_active=True)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({
                    "numero": "Ya existe una unidad con esa combinación (manzana/lote/número)."
                })
        return attrs


class CuotaSerializer(serializers.ModelSerializer):
    saldo = serializers.SerializerMethodField(read_only=True)
    unidad_display = serializers.SerializerMethodField(read_only=True)
    vencimiento = serializers.DateField(input_formats=["%Y-%m-%d"], format="%Y-%m-%d")

    class Meta:
        model = Cuota
        fields = [
            "id", "unidad", "unidad_display", "periodo", "concepto",
            "monto_base", "usa_coeficiente", "coeficiente_snapshot",
            "monto_calculado", "descuento_aplicado", "mora_aplicada",
            "total_a_pagar", "pagado", "saldo",
            "vencimiento", "estado", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["monto_calculado", "total_a_pagar", "estado", "pagado", "created_at", "updated_at"]

    def get_saldo(self, obj):
        return obj.saldo

    def get_unidad_display(self, obj):
        return str(obj.unidad)

    def validate_periodo(self, v):
        if not PERIODO_RE.match(v or ""):
            raise serializers.ValidationError("El periodo debe tener formato YYYY-MM.")
        return v

    def validate(self, attrs):
        instancia = getattr(self, "instance", None)
        unidad = attrs.get("unidad") or getattr(instancia, "unidad", None)
        if unidad and not unidad.is_active:
            raise serializers.ValidationError({"unidad": "La unidad está inactiva."})

        usa_coef = attrs.get("usa_coeficiente", getattr(instancia, "usa_coeficiente", True))
        snap = attrs.get("coeficiente_snapshot", getattr(instancia, "coeficiente_snapshot", None))
        if usa_coef:
            if (snap is None or snap == ""):
                if unidad and unidad.coeficiente is not None:
                    attrs["coeficiente_snapshot"] = unidad.coeficiente
                else:
                    raise serializers.ValidationError({
                        "coeficiente_snapshot": "Requiere snapshot o coeficiente definido en la unidad."
                    })

        for k in ("monto_base", "descuento_aplicado", "mora_aplicada"):
            if k in attrs and attrs[k] is None:
                attrs[k] = Decimal("0.00")
        return attrs

    def _recalc_and_save(self, instance):
        instance.recalc_importes()
        instance.recalc_estado()
        instance.save()
        return instance

    def create(self, validated):
        instance = super().create(validated)
        return self._recalc_and_save(instance)

    def update(self, instance, validated):
        for k, v in validated.items():
            setattr(instance, k, v)
        return self._recalc_and_save(instance)


class PagoCreateSerializer(serializers.Serializer):
    cuota = serializers.PrimaryKeyRelatedField(queryset=Cuota.objects.all())
    monto = serializers.DecimalField(max_digits=10, decimal_places=2)
    medio = serializers.ChoiceField(choices=Pago.MEDIO_CHOICES, default="EFECTIVO")
    referencia = serializers.CharField(required=False, allow_blank=True)

    def validate_monto(self, value):
        if value <= 0:
            raise serializers.ValidationError("El monto debe ser > 0.")
        return value

    def validate(self, attrs):
        cuota = attrs["cuota"]
        if not cuota.is_active:
            raise serializers.ValidationError({"cuota": "No se puede pagar una cuota anulada."})
        if Decimal(cuota.saldo) <= 0:
            raise serializers.ValidationError({"cuota": "La cuota no tiene saldo pendiente."})
        if value_gt(attrs["monto"], cuota.saldo):
            raise serializers.ValidationError({"monto": "El monto excede el saldo pendiente."})
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        pago = Pago.objects.create(
            cuota=validated_data["cuota"],
            monto=validated_data["monto"],
            medio=validated_data.get("medio", "EFECTIVO"),
            referencia=validated_data.get("referencia", ""),
            creado_por=request.user if request and getattr(request, "user", None) and request.user.is_authenticated else None,
        )
        pago.aplicar()
        return pago


class PagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pago
        fields = ["id", "cuota", "fecha_pago", "monto", "medio", "referencia", "valido", "creado_por", "created_at"]
        read_only_fields = ["fecha_pago", "valido", "creado_por", "created_at"]


class GenerarCuotasSerializer(serializers.Serializer):
    periodo = serializers.RegexField(regex=r"^\d{4}-(0[1-9]|1[0-2])$", max_length=7)
    concepto = serializers.CharField(max_length=100)
    monto_base = serializers.DecimalField(max_digits=12, decimal_places=2)
    usa_coeficiente = serializers.BooleanField()
    vencimiento = serializers.DateField(input_formats=["%Y-%m-%d"])


# ------------------------------ Infracciones ------------------------------
class UserBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username"]


class UnidadMiniForInfSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unidad
        fields = ["id", "manzana", "lote", "numero"]


class InfraccionSerializer(serializers.ModelSerializer):
    # lectura
    unidad = UnidadMiniForInfSerializer(read_only=True)
    creado_por = UserBriefSerializer(read_only=True)
    # escritura
    unidad_id = serializers.PrimaryKeyRelatedField(source="unidad", queryset=Unidad.objects.all(), write_only=True)
    residente_id = serializers.PrimaryKeyRelatedField(
        source="residente", queryset=User.objects.all(), allow_null=True, required=False, write_only=True
    )
    fecha = serializers.DateField(input_formats=["%Y-%m-%d"], format="%Y-%m-%d")

    class Meta:
        model = Infraccion
        fields = [
            "id",
            "unidad", "unidad_id", "residente_id",
            "fecha", "tipo", "descripcion", "monto", "evidencia_url",
            "estado", "is_active",
            "creado_por", "created_at", "updated_at",
        ]
        read_only_fields = ["creado_por", "created_at", "updated_at"]


# ------------------------------ Estado de cuenta (salidas) ------------------------------
class UnidadBriefECSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unidad
        fields = ["id", "manzana", "lote", "numero"]


class PagoEstadoCuentaSerializer(serializers.ModelSerializer):
    cuota_periodo = serializers.SerializerMethodField()
    cuota_concepto = serializers.SerializerMethodField()
    unidad_id = serializers.SerializerMethodField()

    class Meta:
        model = Pago
        fields = ["id", "fecha_pago", "monto", "medio", "referencia", "cuota_periodo", "cuota_concepto", "unidad_id", "created_at"]

    def get_cuota_periodo(self, obj):
        try:
            return obj.cuota.periodo
        except Exception:
            return None

    def get_cuota_concepto(self, obj):
        try:
            return obj.cuota.concepto
        except Exception:
            return None

    def get_unidad_id(self, obj):
        try:
            return obj.cuota.unidad_id
        except Exception:
            return None


# ------------------------------ Avisos ------------------------------
class AvisoSerializer(serializers.ModelSerializer):
    unidades = serializers.PrimaryKeyRelatedField(queryset=Unidad.objects.all(), many=True, required=False)
    roles = serializers.PrimaryKeyRelatedField(queryset=Rol.objects.all(), many=True, required=False)
    adjuntos = serializers.ListField(child=serializers.URLField(max_length=1000), required=False, allow_empty=True)

    class Meta:
        model = Aviso
        fields = [
            "id", "titulo", "cuerpo",
            "audiencia", "torre", "unidades", "roles",
            "status", "publish_at", "expires_at",
            "notify_inapp", "notify_email", "notify_push",
            "adjuntos",
            "creado_por", "created_at", "updated_at", "is_active",
        ]
        read_only_fields = ["creado_por", "created_at", "updated_at"]

    def validate(self, data):
        aud = data.get("audiencia", getattr(self.instance, "audiencia", "ALL"))
        if aud == "TORRE":
            if not data.get("torre", getattr(self.instance, "torre", "")):
                raise serializers.ValidationError({"torre": "Requerido cuando audiencia=TORRE."})
        if aud == "UNIDAD":
            unidades = data.get("unidades") or []
            if isinstance(unidades, list) and len(unidades) == 0:
                raise serializers.ValidationError({"unidades": "Debe seleccionar al menos una unidad."})
        if aud == "ROL":
            roles = data.get("roles") or []
            if isinstance(roles, list) and len(roles) == 0:
                raise serializers.ValidationError({"roles": "Debe seleccionar al menos un rol."})

        status_ = data.get("status", getattr(self.instance, "status", "BORRADOR"))
        publish_at = data.get("publish_at", getattr(self.instance, "publish_at", None))
        if status_ == "PROGRAMADO" and not publish_at:
            raise serializers.ValidationError({"publish_at": "Requerido cuando status=PROGRAMADO."})
        return data

    def create(self, validated):
        validated["creado_por"] = self.context["request"].user
        return super().create(validated)


# ------------------------------ Tareas ------------------------------
class RolBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = ("id", "code", "name")


class UnidadBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unidad
        fields = ("id", "manzana", "lote", "numero")


class TareaComentarioSerializer(serializers.ModelSerializer):
    autor = UserBriefSerializer(read_only=True)

    class Meta:
        model = TareaComentario
        fields = ("id", "cuerpo", "autor", "created_at")


class TareaSerializer(serializers.ModelSerializer):
    # Escritura (PKs)
    unidad = serializers.PrimaryKeyRelatedField(queryset=Unidad.objects.all(), allow_null=True, required=False)
    asignado_a = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), allow_null=True, required=False)
    asignado_a_rol = serializers.PrimaryKeyRelatedField(queryset=Rol.objects.all(), allow_null=True, required=False)
    # Lectura
    unidad_info = UnidadBriefSerializer(source="unidad", read_only=True)
    asignado_a_info = UserBriefSerializer(source="asignado_a", read_only=True)
    asignado_a_rol_info = RolBriefSerializer(source="asignado_a_rol", read_only=True)
    comentarios = TareaComentarioSerializer(many=True, read_only=True)

    class Meta:
        model = Tarea
        fields = (
            "id", "titulo", "descripcion", "prioridad", "estado",
            "fecha_inicio", "fecha_limite",
            "unidad", "unidad_info",
            "asignado_a", "asignado_a_info",
            "asignado_a_rol", "asignado_a_rol_info",
            "adjuntos", "checklist",
            "is_active", "created_at", "updated_at", "creado_por",
            "comentarios",
        )
        read_only_fields = ("is_active", "created_at", "updated_at", "creado_por")

    # Normaliza dd/mm/yyyy
    def _norm_date(self, v):
        if not v:
            return v
        if isinstance(v, str):
            import re as _re, datetime as _dt
            m = _re.match(r"^(\d{2})/(\d{2})/(\d{4})$", v)
            if m:
                return _dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        return v

    def validate_fecha_inicio(self, v): return self._norm_date(v)
    def validate_fecha_limite(self, v): return self._norm_date(v)


class TareaWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tarea
        fields = (
            "titulo", "descripcion", "prioridad", "estado",
            "unidad", "asignado_a", "asignado_a_rol",
            "fecha_inicio", "fecha_limite", "adjuntos", "checklist",
        )


# ------------------------------ Áreas comunes ------------------------------
class AreaComunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AreaComun
        fields = [
            "id", "nombre", "descripcion", "ubicacion",
            "capacidad", "costo_por_hora", "activa", "requiere_aprobacion",
        ]


class AreaDisponibilidadWindowSerializer(serializers.Serializer):
    start = serializers.TimeField()
    end = serializers.TimeField()


class SlotSerializer(serializers.Serializer):
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()


class DisponibilidadResponseSerializer(serializers.Serializer):
    area_id = serializers.IntegerField()
    date = serializers.DateField()
    slot_minutes = serializers.IntegerField()
    windows = AreaDisponibilidadWindowSerializer(many=True)
    slots = SlotSerializer(many=True)


# ------------------------------ StaffKind ------------------------------
class StaffKindSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffKind
        fields = ["id", "name", "description", "active"]
        read_only_fields = ["id"]


# ========= Visitor =========
class VisitorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visitor
        fields = ["id", "full_name", "doc_type", "doc_number", "phone"]


# ========= Visit (LECTURA) =========
# Versión para listar/detallar: expone campos de aprobación en solo-lectura.
class VisitSerializer(serializers.ModelSerializer):
    visitor = VisitorSerializer(read_only=True)
    host_resident_name = serializers.SerializerMethodField(read_only=True)
    unit_name = serializers.SerializerMethodField(read_only=True)

    # --- aprobación (solo lectura aquí) ---
    approval_status = serializers.CharField(read_only=True)
    approval_expires_at = serializers.DateTimeField(read_only=True)
    approved_at = serializers.DateTimeField(read_only=True)
    approved_by = serializers.PrimaryKeyRelatedField(read_only=True)
    denied_at = serializers.DateTimeField(read_only=True)
    denied_by = serializers.PrimaryKeyRelatedField(read_only=True)
    approval_token = serializers.UUIDField(read_only=True)  # útil si vas a enviar link

    class Meta:
        model = Visit
        fields = [
            "id",
            "visitor",
            "unit",
            "host_resident",
            "unit_name", "host_resident_name",
            "vehicle_plate", "purpose", "scheduled_for",
            "status", "entry_at", "exit_at", "notes",
            # --- aprobación ---
            "approval_status", "approval_expires_at",
            "approved_at", "approved_by", "denied_at", "denied_by",
            "approval_token",
            # auditoría
            "created_at", "created_by", "updated_at", "updated_by", "entry_by", "exit_by",
        ]
        read_only_fields = [
            "status", "entry_at", "exit_at",
            "created_at", "created_by", "updated_at", "updated_by", "entry_by", "exit_by",
            "approval_status", "approval_expires_at",
            "approved_at", "approved_by", "denied_at", "denied_by", "approval_token",
        ]

    def get_host_resident_name(self, obj):
        u = obj.host_resident
        return (f"{u.first_name} {u.last_name}".strip() or u.username) if u else None

    def get_unit_name(self, obj):
        u = obj.unit
        if not u:
            return None
        b = f"-{u.lote}" if u.lote else ""
        return f"Mza {u.manzana}{b}-{u.numero}"


# ========= Visit (CREAR/EDITAR) =========
# Acepta visitante anidado para crear/actualizar.
class VisitWriteSerializer(serializers.ModelSerializer):
    visitor = VisitorSerializer()

    class Meta:
        model = Visit
        fields = [
            "id",
            "visitor",
            "unit",
            "host_resident",
            "vehicle_plate",
            "purpose",
            "scheduled_for",
            "notes",
        ]

    # Validaciones pequeñas útiles
    def validate_scheduled_for(self, value):
        from django.utils import timezone
        if value and value < timezone.now() - timezone.timedelta(minutes=1):
            raise serializers.ValidationError("La fecha/hora programada no puede estar en el pasado.")
        return value

    # -------- helpers internos --------
    def _get_or_create_visitor(self, validated):
        vdata = validated.pop("visitor")
        visitor, _ = Visitor.objects.get_or_create(
            doc_type=vdata.get("doc_type", "CI"),
            doc_number=vdata["doc_number"],
            defaults={
                "full_name": vdata.get("full_name", "").strip(),
                "phone": (vdata.get("phone") or "").strip(),
            },
        )
        changed = False
        if vdata.get("full_name") and visitor.full_name != vdata["full_name"].strip():
            visitor.full_name = vdata["full_name"].strip()
            changed = True
        if "phone" in vdata and (visitor.phone or "") != (vdata.get("phone") or "").strip():
            visitor.phone = (vdata.get("phone") or "").strip()
            changed = True
        if changed:
            visitor.save()
        return visitor

    # -------- create/update --------
    def create(self, validated):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        visitor = self._get_or_create_visitor(validated)
        visit = Visit.objects.create(created_by=user, visitor=visitor, **validated)
        return visit

    def update(self, instance, validated):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if "visitor" in validated:
            instance.visitor = self._get_or_create_visitor(validated)
        for k, v in validated.items():
            if k != "visitor":
                setattr(instance, k, v)
        instance.updated_by = user
        instance.save()
        return instance


# ========= Serializers pequeños para acciones =========
# Útiles si vas a tener endpoints /approve, /deny, /checkin, /checkout
class VisitApproveSerializer(serializers.Serializer):
    hours_valid = serializers.IntegerField(required=False, min_value=1, max_value=168)  # 1h–7d

class VisitDenySerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)

class VisitCheckInSerializer(serializers.Serializer):
    force = serializers.BooleanField(required=False, default=False)

class VisitCheckOutSerializer(serializers.Serializer):
    pass

# ------------------------------ Vehículos / Solicitudes ------------------------------
class VehiculoSerializer(serializers.ModelSerializer):
    propietario_nombre = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Vehiculo
        fields = [
            "id", "unidad", "propietario", "propietario_nombre",
            "placa", "marca", "modelo", "color", "tipo",
            "foto", "activo", "autorizado_en", "autorizado_por",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "autorizado_en", "autorizado_por", "created_at", "updated_at"]

    def get_propietario_nombre(self, obj):
        u = obj.propietario
        return (f"{u.first_name} {u.last_name}".strip() or u.username)


class SolicitudVehiculoCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SolicitudVehiculo
        fields = ["id", "placa", "marca", "modelo", "color", "tipo", "foto_placa", "documento"]
        read_only_fields = ["id"]


class SolicitudVehiculoListSerializer(serializers.ModelSerializer):
    solicitante_nombre = serializers.SerializerMethodField()

    class Meta:
        model = SolicitudVehiculo
        fields = [
            "id", "solicitante", "solicitante_nombre", "unidad",
            "placa", "marca", "modelo", "color", "tipo",
            "foto_placa", "documento",
            "estado", "observaciones",
            "revisado_por", "revisado_en",
            "vehiculo",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_solicitante_nombre(self, obj):
        u = obj.solicitante
        return (f"{u.first_name} {u.last_name}".strip() or u.username)


class SolicitudVehiculoReviewSerializer(serializers.ModelSerializer):
    accion = serializers.ChoiceField(choices=["aprobar", "rechazar"])
    observaciones = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = SolicitudVehiculo
        fields = ["accion", "observaciones"]


# ------------------------------ Pagos online mock ------------------------------
class OnlinePaymentIntentSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnlinePaymentIntent
        fields = [
            "id", "cuota", "amount", "currency", "provider", "status",
            "confirmation_url", "qr_payload", "provider_id", "created_at", "paid_at",
        ]
        read_only_fields = ["status", "confirmation_url", "provider_id", "created_at", "paid_at"]

    def validate(self, attrs):
        cuota = attrs.get("cuota") or getattr(getattr(self, "instance", None), "cuota", None)
        amount = attrs.get("amount") or getattr(getattr(self, "instance", None), "amount", None)
        if not cuota:
            raise serializers.ValidationError({"cuota": "Requerida."})
        if not cuota.is_active:
            raise serializers.ValidationError({"cuota": "La cuota está inactiva/anulada."})
        if Decimal(cuota.saldo) <= 0:
            raise serializers.ValidationError({"cuota": "La cuota no tiene saldo pendiente."})
        if amount is None or Decimal(amount) <= 0:
            raise serializers.ValidationError({"amount": "Debe ser > 0."})
        if Decimal(amount) > Decimal(cuota.saldo):
            raise serializers.ValidationError({"amount": "No puede exceder el saldo pendiente."})
        return attrs


class MockReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = MockReceipt
        fields = ["id", "intent", "receipt_url", "amount", "reference", "bank_name", "uploaded_by", "created_at"]
        read_only_fields = ["uploaded_by", "created_at"]

    def validate(self, attrs):
        intent = attrs.get("intent")
        if not intent:
            raise serializers.ValidationError({"intent": "Requerido."})
        if intent.status not in ("CREATED", "PENDING"):
            raise serializers.ValidationError({"intent": "El intento no está en estado válido para adjuntar comprobante."})

        amount = attrs.get("amount")
        if amount is not None and Decimal(amount) <= 0:
            raise serializers.ValidationError({"amount": "Si se informa, debe ser > 0."})

        if not attrs.get("receipt_url") and not attrs.get("reference"):
            raise serializers.ValidationError({"receipt_url": "Debes informar receipt_url o reference."})
        return attrs


#ia
class SnapshotInSerializer(serializers.Serializer):
    gate_id = serializers.IntegerField(required=False)  # opcional si aún no tienes Gate
    camera_id = serializers.CharField(required=False, allow_blank=True)
    image = serializers.ImageField(required=True)
    
class AccessEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessEvent
        fields = [
            "id",
            "created_at",
            "camera_id",
            "plate_raw",
            "plate_norm",
            "score",
            "decision",
            "reason",
            "opened",
            "vehicle",
            "visit",
            "payload",
            "triggered_by",
        ]
        read_only_fields = ["id", "created_at"]