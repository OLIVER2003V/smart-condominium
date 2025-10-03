from decimal import Decimal
from datetime import date
import uuid
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission, User  # User para FKs directas en algunos modelos
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q, F
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


# =========================
# Roles / Perfiles
# =========================

BASE_CHOICES = [
    ("ADMIN", "Admin"),
    ("STAFF", "Staff"),
    ("RESIDENT", "Resident"),
]


class Rol(models.Model):
    code = models.CharField(max_length=30, unique=True)   # Ej: ADMIN
    name = models.CharField(max_length=50)                # Ej: Administrador
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=False)        # protege roles base
    base = models.CharField(max_length=10, choices=BASE_CHOICES, default="STAFF")
    permissions = models.ManyToManyField(Permission, blank=True, related_name="roles")

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def save(self, *args, **kwargs):
        # Normaliza el code: sin espacios y en mayúsculas
        if self.code:
            self.code = self.code.strip().upper().replace(" ", "_")
        super().save(*args, **kwargs)


class StaffKind(models.Model):
    """
    Catálogo opcional de tipos de personal (Guardia, Limpieza, Jardinería...).
    Puedes crear/editar/eliminar libremente.
    """
    name = models.CharField(max_length=60, unique=True)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.ForeignKey(Rol, null=True, blank=True, on_delete=models.SET_NULL)

    # Tipo de personal (opcional)
    staff_kind = models.ForeignKey(
        "smartcondominio.StaffKind",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="profiles",
    )
    staff_kind_text = models.CharField(max_length=80, blank=True, default="")

    def __str__(self):
        role_code = self.role.code if self.role else "Sin rol"
        kind = self.staff_kind.name if self.staff_kind else (self.staff_kind_text or "")
        return f"{self.user.username} ({role_code}{' · ' + kind if kind else ''})"


@receiver(post_save, sender=User)
def ensure_profile(sender, instance, created, **kwargs):
    Profile.objects.get_or_create(user=instance)


# =========================
# Unidades / Cuotas / Pagos
# =========================

class Unidad(models.Model):
    TIPO_CHOICES = [
        ("DEP", "Departamento"),
        ("CASA", "Casa"),
        ("LOCAL", "Local"),
    ]
    ESTADO_CHOICES = [
        ("OCUPADA", "Ocupada"),
        ("DESOCUPADA", "Desocupada"),
        ("MANTENIMIENTO", "Mantenimiento"),
        ("INACTIVA", "Inactiva"),
    ]

    # Identificación “cruceña”
    manzana = models.CharField(max_length=100)                 # antes torre
    lote    = models.CharField(max_length=100, blank=True)     # antes bloque
    numero  = models.CharField(max_length=20)                  # Nº casa/dpto/local
    piso    = models.IntegerField(null=True, blank=True)       # relevante en DEP/LOCAL

    # Características
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="CASA")
    metraje = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)]
    )
    coeficiente = models.DecimalField(
        max_digits=6, decimal_places=4, null=True, blank=True,  # precisión fina (%)
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    dormitorios = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    parqueos    = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    bodegas     = models.IntegerField(default=0, validators=[MinValueValidator(0)])

    # Estado y asignaciones
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="DESOCUPADA")
    propietario = models.ForeignKey(
        User, related_name="propiedades", on_delete=models.SET_NULL, null=True, blank=True
    )
    residente = models.ForeignKey(
        User, related_name="residencias", on_delete=models.SET_NULL, null=True, blank=True
    )
    is_active = models.BooleanField(default=True)  # “soft delete”

    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            # Única solo entre activas, para permitir reuso al desactivar
            models.UniqueConstraint(
                fields=["manzana", "lote", "numero"],
                condition=Q(is_active=True),
                name="uniq_unidad_manzana_lote_numero_active",
            )
        ]
        ordering = ["manzana", "lote", "numero"]

    def __str__(self):
        b = f"-{self.lote}" if self.lote else ""
        return f"Mza {self.manzana}{b}-{self.numero}"


class Cuota(models.Model):
    ESTADO_CHOICES = [
        ("PENDIENTE", "Pendiente"),
        ("PARCIAL", "Parcial"),
        ("PAGADA", "Pagada"),
        ("VENCIDA", "Vencida"),
        ("ANULADA", "Anulada"),
    ]

    unidad = models.ForeignKey("smartcondominio.Unidad", on_delete=models.PROTECT, related_name="cuotas")
    periodo = models.CharField(max_length=7)  # "YYYY-MM"
    concepto = models.CharField(max_length=50, default="GASTO_COMUN")

    # Montos
    monto_base = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    usa_coeficiente = models.BooleanField(default=True)
    # snapshot de % de la unidad en el momento
    coeficiente_snapshot = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal("0.0000"))
    monto_calculado = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    descuento_aplicado = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    mora_aplicada = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total_a_pagar = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    pagado = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    vencimiento = models.DateField()
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default="PENDIENTE")
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["unidad", "periodo", "concepto"],
                condition=Q(is_active=True),
                name="uniq_cuota_unidad_periodo_concepto_activa",
            )
        ]
        indexes = [models.Index(fields=["periodo", "concepto"])]
        ordering = ["-periodo", "unidad_id"]

    def __str__(self):
        return f"{self.unidad} · {self.periodo} · {self.concepto}"

    @property
    def saldo(self) -> Decimal:
        s = Decimal(self.total_a_pagar) - Decimal(self.pagado)
        return s if s > 0 else Decimal("0.00")

    def recalc_importes(self):
        """
        Recalcula monto_calculado/total según base + coeficiente + descuentos/moras (simples)
        """
        base = Decimal(self.monto_base or 0)
        coef = Decimal(self.coeficiente_snapshot or 0)
        calculado = base * (coef / Decimal("100")) if self.usa_coeficiente else base
        self.monto_calculado = (calculado.quantize(Decimal("0.01")))
        total = self.monto_calculado - Decimal(self.descuento_aplicado or 0) + Decimal(self.mora_aplicada or 0)
        self.total_a_pagar = (total if total > 0 else Decimal("0.00")).quantize(Decimal("0.01"))

    def recalc_estado(self, today=None):
        today = today or date.today()
        if not self.is_active:
            self.estado = "ANULADA"
            return
        if self.pagado >= self.total_a_pagar and self.total_a_pagar > 0:
            self.estado = "PAGADA"
        elif self.pagado > 0 and self.pagado < self.total_a_pagar:
            self.estado = "PARCIAL"
        else:
            # sin pagos
            if today > self.vencimiento and self.total_a_pagar > 0:
                self.estado = "VENCIDA"
            else:
                self.estado = "PENDIENTE"

    def apply_simple_mora(self, mora_fija=Decimal("0.00")):
        """Ejemplo simple de mora fija si está vencida y tiene saldo."""
        if date.today() > self.vencimiento and self.saldo > 0 and mora_fija > 0:
            self.mora_aplicada = (Decimal(self.mora_aplicada) + Decimal(mora_fija)).quantize(Decimal("0.01"))
            self.recalc_importes()
            self.recalc_estado()


class Pago(models.Model):
    MEDIO_CHOICES = [
        ("EFECTIVO", "Efectivo"),
        ("TRANSFERENCIA", "Transferencia"),
        ("TARJETA", "Tarjeta"),
        ("OTRO", "Otro"),
    ]
    cuota = models.ForeignKey(Cuota, on_delete=models.PROTECT, related_name="pagos")
    fecha_pago = models.DateField(auto_now_add=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    medio = models.CharField(max_length=20, choices=MEDIO_CHOICES, default="EFECTIVO")
    referencia = models.CharField(max_length=100, blank=True)
    valido = models.BooleanField(default=True)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="pagos_cargados")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Pago {self.id} · Cuota {self.cuota_id} · {self.monto}"

    def aplicar(self):
        if not self.valido:
            return
        self.cuota.pagado = (Decimal(self.cuota.pagado) + Decimal(self.monto)).quantize(Decimal("0.01"))
        self.cuota.recalc_estado()
        self.cuota.save(update_fields=["pagado", "estado", "updated_at"])

    def revertir(self):
        if not self.valido:
            return
        self.valido = False
        self.save(update_fields=["valido"])
        self.cuota.pagado = (Decimal(self.cuota.pagado) - Decimal(self.monto))
        if self.cuota.pagado < 0:
            self.cuota.pagado = Decimal("0.00")
        self.cuota.recalc_estado()
        self.cuota.save(update_fields=["pagado", "estado", "updated_at"])


# =========================
# Infracciones
# =========================

class Infraccion(models.Model):
    TIPO_CHOICES = [
        ("RUIDO", "Ruido"),
        ("MASCOTA", "Mascota"),
        ("ESTACIONAMIENTO", "Estacionamiento indebido"),
        ("DANOS", "Daños"),
        ("OTRA", "Otra"),
    ]
    ESTADO_CHOICES = [
        ("PENDIENTE", "Pendiente"),
        ("RESUELTA", "Resuelta"),
        ("ANULADA", "Anulada"),
    ]

    unidad = models.ForeignKey("smartcondominio.Unidad", on_delete=models.PROTECT, related_name="infracciones")
    residente = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="infracciones")

    fecha = models.DateField(default=timezone.now)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    descripcion = models.TextField(blank=True)
    monto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    evidencia_url = models.URLField(blank=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default="PENDIENTE")

    is_active = models.BooleanField(default=True)
    creado_por = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="infracciones_creadas")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.unidad_id} • {self.tipo} • {self.estado}"


# =========================
# Avisos / Comunicados
# =========================

class Aviso(models.Model):
    AUDIENCE_CHOICES = [
        ("ALL", "Todos"),
        ("TORRE", "Por torre"),
        ("UNIDAD", "Por unidad"),
        ("ROL", "Por rol"),
    ]
    STATUS_CHOICES = [
        ("BORRADOR", "Borrador"),
        ("PROGRAMADO", "Programado"),
        ("PUBLICADO", "Publicado"),
        ("ARCHIVADO", "Archivado"),
    ]

    titulo = models.CharField(max_length=200)
    cuerpo = models.TextField()

    # audiencia
    audiencia = models.CharField(max_length=10, choices=AUDIENCE_CHOICES, default="ALL")
    torre = models.CharField(max_length=100, blank=True)  # cuando audiencia=TORRE
    unidades = models.ManyToManyField("smartcondominio.Unidad", blank=True)
    roles = models.ManyToManyField("smartcondominio.Rol", blank=True)

    # publicación
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="BORRADOR")
    publish_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    # notificación (placeholders)
    notify_inapp = models.BooleanField(default=True)
    notify_email = models.BooleanField(default=False)
    notify_push = models.BooleanField(default=False)

    # adjuntos como URLs (Drive/S3/lo que uses)
    adjuntos = models.JSONField(default=list, blank=True)

    # auditoría
    creado_por = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="avisos_creados")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-publish_at", "-created_at"]
        indexes = [
            models.Index(fields=["audiencia", "status"]),
            models.Index(fields=["publish_at"]),
        ]

    def __str__(self):
        return f"[{self.status}] {self.titulo}"

    def es_visible(self, now=None):
        now = now or timezone.now()
        if not self.is_active:
            return False
        if self.status != "PUBLICADO":
            return False
        if self.publish_at and self.publish_at > now:
            return False
        if self.expires_at and self.expires_at < now:
            return False
        return True

    def publicar_ahora(self):
        self.status = "PUBLICADO"
        if not self.publish_at:
            self.publish_at = timezone.now()


# =========================
# Tareas (CU15/CU24)
# =========================

class Tarea(models.Model):
    PRIORIDAD_CHOICES = [
        ("BAJA", "Baja"),
        ("MEDIA", "Media"),
        ("ALTA", "Alta"),
        ("URGENTE", "Urgente"),
    ]
    ESTADO_CHOICES = [
        ("NUEVA", "Nueva"),
        ("ASIGNADA", "Asignada"),
        ("EN_PROGRESO", "En progreso"),
        ("BLOQUEADA", "Bloqueada"),
        ("COMPLETADA", "Completada"),
        ("CANCELADA", "Cancelada"),
    ]

    # Básico
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)

    # Contexto
    unidad = models.ForeignKey("smartcondominio.Unidad", null=True, blank=True, on_delete=models.SET_NULL, related_name="tareas")

    # Asignación
    asignado_a = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="tareas_asignadas")
    asignado_a_rol = models.ForeignKey("smartcondominio.Rol", null=True, blank=True, on_delete=models.SET_NULL, related_name="tareas_de_rol")
    watchers = models.ManyToManyField(User, blank=True, related_name="tareas_watch")

    # Gestión
    prioridad = models.CharField(max_length=10, choices=PRIORIDAD_CHOICES, default="MEDIA")
    estado = models.CharField(max_length=12, choices=ESTADO_CHOICES, default="NUEVA")
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_limite = models.DateField(null=True, blank=True)

    # Adjuntos/Checklist (como URLs/ítems)
    adjuntos = models.JSONField(default=list, blank=True)
    checklist = models.JSONField(default=list, blank=True)  # [{text: str, done: bool}]

    # Auditoría
    creado_por = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="tareas_creadas")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-created_at"]
        permissions = [
            ("manage_tasks", "Puede gestionar y asignar tareas"),
        ]

    def __str__(self):
        return f"[{self.id}] {self.titulo}"

    @property
    def atrasada(self) -> bool:
        return bool(self.fecha_limite and timezone.localdate() > self.fecha_limite and self.estado not in {"COMPLETADA", "CANCELADA"})


class TareaComentario(models.Model):
    tarea = models.ForeignKey(Tarea, on_delete=models.CASCADE, related_name="comentarios")
    autor = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="tarea_comentarios")
    cuerpo = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Coment {self.id} · Tarea {self.tarea_id}"


# =========================
# Áreas Comunes (CU16)
# =========================

class AreaComun(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    descripcion = models.TextField(blank=True)
    ubicacion = models.CharField(max_length=120, blank=True)
    capacidad = models.PositiveIntegerField(default=1)
    costo_por_hora = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    activa = models.BooleanField(default=True)
    requiere_aprobacion = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Área Común"
        verbose_name_plural = "Áreas Comunes"

    def __str__(self):
        return self.nombre


class AreaDisponibilidad(models.Model):
    """
    Ventanas de disponibilidad por día de la semana (0=Lunes ... 6=Domingo).
    """
    DIA_CHOICES = [
        (0, "Lunes"), (1, "Martes"), (2, "Miércoles"),
        (3, "Jueves"), (4, "Viernes"), (5, "Sábado"), (6, "Domingo"),
    ]
    area = models.ForeignKey(AreaComun, on_delete=models.CASCADE, related_name="reglas")
    dia_semana = models.SmallIntegerField(choices=DIA_CHOICES)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    max_horas_por_reserva = models.PositiveIntegerField(default=4)

    class Meta:
        ordering = ["area", "dia_semana", "hora_inicio"]
        constraints = [
            models.CheckConstraint(
                check=Q(hora_fin__gt=F("hora_inicio")),
                name="area_disp_hora_fin_gt_inicio"
            ),
            models.UniqueConstraint(
                fields=["area", "dia_semana", "hora_inicio", "hora_fin"],
                name="area_disp_uniq_window"
            ),
        ]

    def __str__(self):
        return f"{self.area} - {self.get_dia_semana_display()} {self.hora_inicio}-{self.hora_fin}"


class ReservaArea(models.Model):
    """
    Usada para calcular disponibilidad (evitar solapamientos).
    CU17/CU18 la usarán para crear/confirmar/cobrar.
    """
    ESTADOS = [
        ("PENDIENTE", "Pendiente"),
        ("CONFIRMADA", "Confirmada"),
        ("PAGADA", "Pagada"),
        ("CANCELADA", "Cancelada"),
        ("RECHAZADA", "Rechazada"),
    ]

    area = models.ForeignKey(AreaComun, on_delete=models.CASCADE, related_name="reservas")
    unidad = models.ForeignKey("smartcondominio.Unidad", on_delete=models.SET_NULL, null=True, blank=True, related_name="reservas_area")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reservas_area")

    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField()
    estado = models.CharField(max_length=12, choices=ESTADOS, default="PENDIENTE")

    monto_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    nota = models.TextField(blank=True)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["area", "fecha_inicio", "fecha_fin"]),
            models.Index(fields=["estado"]),
        ]
        ordering = ["-fecha_inicio"]

    def __str__(self):
        return f"{self.area} {self.fecha_inicio} - {self.fecha_fin} ({self.estado})"


# =========================
# Visitantes / Visitas
# =========================

class Visitor(models.Model):
    DOC_TYPES = [
        ("CI", "Cédula"),
        ("PASS", "Pasaporte"),
        ("OTRO", "Otro"),
    ]
    full_name  = models.CharField(max_length=120)
    doc_type   = models.CharField(max_length=10, choices=DOC_TYPES, default="CI")
    doc_number = models.CharField(max_length=40, db_index=True)
    phone      = models.CharField(max_length=30, blank=True)
    # photo = models.ImageField(upload_to="visitors/", blank=True, null=True)

    class Meta:
        unique_together = [("doc_type", "doc_number")]

    def save(self, *args, **kwargs):
        # Normalización SOLO de campos de Visitor
        if self.doc_number:
            self.doc_number = self.doc_number.strip().upper()
        if self.full_name:
            self.full_name = " ".join(self.full_name.split())
        if self.phone:
            self.phone = self.phone.strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} ({self.doc_type}-{self.doc_number})"


class Visit(models.Model):
    STATUS = [
        ("REGISTRADO", "Registrado"),
        ("INGRESADO",  "Ingresado"),
        ("SALIDO",     "Salido"),
        ("CANCELADO",  "Cancelado"),
        ("DENEGADO",   "Denegado"),
    ]
    APPROVAL = [
        ("PEND", "Pendiente"),
        ("APR",  "Aprobada"),
        ("DEN",  "Denegada"),
        ("EXP",  "Expirada"),
    ]

    visitor = models.ForeignKey(Visitor, on_delete=models.PROTECT, related_name="visits")
    unit = models.ForeignKey("smartcondominio.Unidad", on_delete=models.PROTECT, related_name="visits")
    host_resident = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="hosted_visits",
        help_text="Residente/anfitrión de la unidad",
    )

    vehicle_plate = models.CharField(max_length=15, blank=True, db_index=True)
    purpose = models.CharField(max_length=140, blank=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=12, choices=STATUS, default="REGISTRADO", db_index=True)
    entry_at = models.DateTimeField(null=True, blank=True)
    exit_at = models.DateTimeField(null=True, blank=True)

    # --- aprobación del residente ---
    approval_status     = models.CharField(max_length=4, choices=APPROVAL, default="PEND", db_index=True)
    # para evitar líos con SQLite, sin unique por ahora (solo index):
    approval_token      = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    approval_expires_at = models.DateTimeField(null=True, blank=True)
    approved_at         = models.DateTimeField(null=True, blank=True)
    approved_by         = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="visits_approved"
    )
    denied_at           = models.DateTimeField(null=True, blank=True)
    denied_by           = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="visits_denied"
    )
    # -------------------------------

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="visits_created")
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="visits_updated", null=True, blank=True)
    entry_by   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="visits_entry_by", null=True, blank=True)
    exit_by    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="visits_exit_by",  null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["approval_status"]),
            models.Index(fields=["vehicle_plate"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["-created_at"]

    # helpers (opcionales)
    def is_approval_valid(self):
        if self.approval_status != "APR":
            return False
        if self.approval_expires_at and timezone.now() > self.approval_expires_at:
            return False
        return True

    def approve(self, by_user, hours_valid=24):
        self.approval_status = "APR"
        self.approved_at = timezone.now()
        self.approved_by = by_user
        if not self.approval_expires_at:
            self.approval_expires_at = timezone.now() + timezone.timedelta(hours=hours_valid)

    def deny(self, by_user):
        self.approval_status = "DEN"
        self.denied_at = timezone.now()
        self.denied_by = by_user

    def save(self, *args, **kwargs):
        if self.vehicle_plate:
            self.vehicle_plate = self.vehicle_plate.strip().upper().replace(" ", "")
        super().save(*args, **kwargs)

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.exit_at and not self.entry_at:
            raise ValidationError("No puede haber salida sin una entrada registrada.")
        if self.exit_at and self.entry_at and self.exit_at < self.entry_at:
            raise ValidationError("La hora de salida no puede ser anterior a la hora de entrada.")

    def mark_entry(self, user, *, force: bool = False):
        if not force and not self.is_approval_valid():
            raise ValueError("La visita no está aprobada o la aprobación venció.")
        self.entry_at = timezone.now()
        self.entry_by = user
        self.status = "INGRESADO"

    def mark_exit(self, user):
        self.exit_at = timezone.now()
        self.exit_by = user
        self.status = "SALIDO"


# =========================
# Vehículos / Solicitudes
# =========================

VEHICULO_TIPO_CHOICES = [
    ("AUTO", "Auto"),
    ("MOTO", "Moto"),
    ("CAMIONETA", "Camioneta"),
    ("OTRO", "Otro"),
]

SOLICITUD_ESTADO_CHOICES = [
    ("PENDIENTE", "Pendiente"),
    ("APROBADA", "Aprobada"),
    ("RECHAZADA", "Rechazada"),
    ("CANCELADA", "Cancelada"),
]


class Vehiculo(models.Model):
    unidad = models.ForeignKey(
        "smartcondominio.Unidad",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="vehiculos",
    )
    propietario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="vehiculos",
    )
    placa = models.CharField(max_length=15, unique=True, db_index=True)
    marca = models.CharField(max_length=40, blank=True, default="")
    modelo = models.CharField(max_length=40, blank=True, default="")
    color = models.CharField(max_length=30, blank=True, default="")
    tipo = models.CharField(max_length=12, choices=VEHICULO_TIPO_CHOICES, default="AUTO")

    foto = models.ImageField(upload_to="vehiculos/fotos/", null=True, blank=True)

    activo = models.BooleanField(default=True)
    autorizado_en = models.DateTimeField(null=True, blank=True)
    autorizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="vehiculos_autorizados"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["placa"]

    def __str__(self):
        return f"{self.placa} ({self.marca} {self.modelo})"


class SolicitudVehiculo(models.Model):
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="solicitudes_vehiculo",
    )
    unidad = models.ForeignKey(
        "smartcondominio.Unidad",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="solicitudes_vehiculo",
    )

    # datos del vehículo solicitado
    placa = models.CharField(max_length=15)
    marca = models.CharField(max_length=40, blank=True, default="")
    modelo = models.CharField(max_length=40, blank=True, default="")
    color = models.CharField(max_length=30, blank=True, default="")
    tipo = models.CharField(max_length=12, choices=VEHICULO_TIPO_CHOICES, default="AUTO")

    # adjuntos
    foto_placa = models.ImageField(upload_to="vehiculos/placas/", null=True, blank=True)
    documento = models.FileField(upload_to="vehiculos/docs/", null=True, blank=True)

    estado = models.CharField(max_length=12, choices=SOLICITUD_ESTADO_CHOICES, default="PENDIENTE", db_index=True)
    observaciones = models.TextField(blank=True, default="")
    revisado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="solicitudes_vehiculo_revisadas",
    )
    revisado_en = models.DateTimeField(null=True, blank=True)

    # vínculo con el vehículo generado al aprobar
    vehiculo = models.ForeignKey(Vehiculo, null=True, blank=True, on_delete=models.SET_NULL, related_name="solicitudes")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["placa", "estado"])]
        ordering = ["-created_at"]

    def __str__(self):
        return f"Solicitud {self.placa} ({self.estado})"

    def aprobar(self, aprobado_por, unidad=None, observ=""):
        # Verifica que no exista otra placa autorizada
        existe = Vehiculo.objects.filter(placa__iexact=self.placa).exclude(activo=False).first()
        if existe and existe.propietario_id != self.solicitante_id:
            raise ValueError("La placa ya está registrada por otro usuario.")

        vehiculo = existe or Vehiculo.objects.create(
            propietario=self.solicitante,
            placa=self.placa.upper(),
            marca=self.marca, modelo=self.modelo, color=self.color, tipo=self.tipo,
            unidad=unidad or self.unidad,
        )
        vehiculo.autorizado_en = timezone.now()
        vehiculo.autorizado_por = aprobado_por
        vehiculo.activo = True
        vehiculo.save()

        self.estado = "APROBADA"
        self.revisado_por = aprobado_por
        self.revisado_en = timezone.now()
        self.observaciones = observ or self.observaciones
        self.vehiculo = vehiculo
        self.save()
        return vehiculo

    def rechazar(self, rechazado_por, observ=""):
        self.estado = "RECHAZADA"
        self.revisado_por = rechazado_por
        self.revisado_en = timezone.now()
        self.observaciones = observ or self.observaciones
        self.save()

    def cancelar(self, cancelado_por, observ=""):
        if self.solicitante_id != cancelado_por.id:
            raise ValueError("Solo el solicitante puede cancelar su solicitud.")
        self.estado = "CANCELADA"
        self.observaciones = observ or self.observaciones
        self.save()


# =========================
# Pagos Online (Mock)
# =========================

class OnlinePaymentIntent(models.Model):
    PROVIDERS = [("MOCK", "Mock")]
    ESTADOS = [("CREATED","Creada"),("PENDING","Pendiente"),("PAID","Pagada"),
               ("FAILED","Fallida"),("CANCELLED","Cancelada")]

    cuota = models.ForeignKey(Cuota, on_delete=models.PROTECT, related_name="intentos_online")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="BOB")
    provider = models.CharField(max_length=10, choices=PROVIDERS, default="MOCK")
    provider_id = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=12, choices=ESTADOS, default="CREATED")
    confirmation_url = models.URLField(blank=True)
    qr_payload = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["provider_id"]),
        ]

    def __str__(self):
        return f"Intent #{self.id} · Cuota {self.cuota_id} · {self.status}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.amount is None or self.amount <= Decimal("0"):
            raise ValidationError({"amount": "El monto debe ser mayor a 0."})
        if not self.currency:
            raise ValidationError({"currency": "Moneda requerida."})

    @property
    def is_paid(self) -> bool:
        return self.status == "PAID"

    def mark_paid(self):
        self.status = "PAID"
        self.paid_at = timezone.now()


class MockReceipt(models.Model):
    intent = models.ForeignKey(OnlinePaymentIntent, on_delete=models.CASCADE, related_name="receipts")
    receipt_url = models.URLField(blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    reference = models.CharField(max_length=120, blank=True)
    bank_name = models.CharField(max_length=80, blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"Receipt #{self.id} · Intent {self.intent_id} · {self.reference or 's/ref'}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.amount is not None and self.amount <= Decimal("0"):
            raise ValidationError({"amount": "El monto (si se informa) debe ser > 0."})
#IA BITACORA DE INGRESO
# --- Accesos vehiculares (bitácora) ---
class AccessEvent(models.Model):
    created_at   = models.DateTimeField(auto_now_add=True)
    camera_id    = models.CharField(max_length=60, blank=True)
    plate_raw    = models.CharField(max_length=30, blank=True)
    plate_norm   = models.CharField(max_length=30, db_index=True, blank=True)
    score        = models.FloatField(null=True, blank=True)
    decision     = models.CharField(max_length=32)   # ALLOW_RESIDENT | ALLOW_VISIT | DENY_UNKNOWN | ERROR_OCR
    reason       = models.CharField(max_length=200, blank=True)
    opened       = models.BooleanField(default=False)

    vehicle      = models.ForeignKey("smartcondominio.Vehiculo", null=True, blank=True, on_delete=models.SET_NULL)
    visit        = models.ForeignKey("smartcondominio.Visit",    null=True, blank=True, on_delete=models.SET_NULL)

    payload      = models.JSONField(default=dict, blank=True)   # respuesta completa de Plate Recognizer (opcional)
    triggered_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["-created_at"]
