from django.db import models
from django.db.models import Q, F
from django.contrib.auth.models import User, Permission
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from datetime import date
from django.utils import timezone
#CREAMOS UNA TABLA DE TIPO ROL 
class Rol(models.Model):
    code = models.CharField(max_length=30, unique=True)   # Ej: ADMIN
    name = models.CharField(max_length=50)                # Ej: Administrador
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=False)  # protege roles base
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

#TABLA DE TIPO PERFIL
# Profile: cambia role de CharField -> ForeignKey
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.ForeignKey(Rol, null=True, blank=True, on_delete=models.SET_NULL)
    def __str__(self):
        return f"{self.user.username} ({self.role.code if self.role else 'Sin rol'})"

@receiver(post_save, sender=User)
def ensure_profile(sender, instance, created, **kwargs):
    Profile.objects.get_or_create(user=instance)
    
#UNIDAD  
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

    # Identificación física
    torre = models.CharField(max_length=100)
    bloque = models.CharField(max_length=100, null=True, blank=True)
    numero = models.CharField(max_length=20)
    piso = models.IntegerField(null=True, blank=True)

    # Características
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    metraje = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    coeficiente = models.DecimalField(  # alícuota
        max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    dormitorios = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    parqueos = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    bodegas = models.IntegerField(default=0, validators=[MinValueValidator(0)])

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
        # Unicidad lógica para unidades activas (torre + bloque + numero)
        constraints = [
            models.UniqueConstraint(
                fields=["torre", "bloque", "numero"],
                name="uniq_unidad_torre_bloque_numero",
            )
        ]
        ordering = ["torre", "bloque", "numero"]

    def __str__(self):
        b = f"-{self.bloque}" if self.bloque else ""
        return f"{self.torre}{b}-{self.numero}"
    
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
    coeficiente_snapshot = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))  # % de la unidad en el momento
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
        indexes = [
            models.Index(fields=["periodo", "concepto"]),
        ]
        ordering = ["-periodo", "unidad_id"]

    def __str__(self):
        return f"{self.unidad} · {self.periodo} · {self.concepto}"

    @property
    def saldo(self) -> Decimal:
        s = Decimal(self.total_a_pagar) - Decimal(self.pagado)
        return s if s > 0 else Decimal("0.00")

    def recalc_importes(self):
        """Recalcula monto_calculado/total según base + coeficiente + descuentos/moras (simples)"""
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
        ("ONLINE_STRIPE", "Online (Stripe)"),  # ✅ necesario para CU11
        # opcionales a futuro:
        # ("ONLINE_AIRTM", "Online (Airtm)"),
        # ("ONLINE_MERU", "Online (Meru)"),
        ("OTRO", "Otro"),
    ]

    cuota = models.ForeignKey("Cuota", on_delete=models.PROTECT, related_name="pagos")
    fecha_pago = models.DateField(auto_now_add=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    medio = models.CharField(max_length=20, choices=MEDIO_CHOICES, default="EFECTIVO")

    # Sube max_length y agrega índice: la referencia del gateway (p.ej. intent_id)
    referencia = models.CharField(max_length=150, blank=True, db_index=True)

    valido = models.BooleanField(default=True)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="pagos_cargados")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        # Evita duplicar el mismo pago del mismo gateway:
        constraints = [
            models.UniqueConstraint(
                fields=["medio", "referencia"],
                name="uniq_pago_medio_referencia",
                condition=~Q(referencia=""),
            )
        ]

    def __str__(self):
        return f"Pago {self.id} · Cuota {self.cuota_id} · {self.monto}"

    def aplicar(self):
        """
        Aplica el pago a la cuota de forma segura (evita condiciones de carrera).
        """
        if not self.valido:
            return
        # Garantiza que pagado nunca sea None
        if self.cuota.pagado is None:
            self.cuota.pagado = Decimal("0.00")

        # Suma atómica en DB
        type(self.cuota).objects.filter(pk=self.cuota.pk).update(
            pagado=F("pagado") + Decimal(self.monto)
        )
        # Refresca y recalcula estado
        self.cuota.refresh_from_db(fields=["pagado"])
        self.cuota.recalc_estado()
        self.cuota.save(update_fields=["estado", "updated_at"])

    def revertir(self):
        """
        Marca el pago como inválido y resta el monto de forma segura.
        """
        if not self.valido:
            return
        self.valido = False
        self.save(update_fields=["valido"])

        type(self.cuota).objects.filter(pk=self.cuota.pk).update(
            pagado=F("pagado") - Decimal(self.monto)
        )
        self.cuota.refresh_from_db(fields=["pagado"])
        if self.cuota.pagado < 0:
            self.cuota.pagado = Decimal("0.00")
        self.cuota.recalc_estado()
        self.cuota.save(update_fields=["pagado", "estado", "updated_at"])
        
#GESTIONAR INFRACCIONES

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
    # 🔧 antes: ForeignKey("smartcondominio.Residente") -> no existe
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

#PAGOS EN LINEA
class OnlinePayment(models.Model):
    PROVIDER_CHOICES = [("STRIPE", "Stripe")]
    STATUS_CHOICES = [
        ("CREATED", "Created"),
        ("REQUIRES_ACTION", "Requires action"),
        ("SUCCEEDED", "Succeeded"),
        ("FAILED", "Failed"),
        ("CANCELED", "Canceled"),
    ]
    cuota = models.ForeignKey("smartcondominio.Cuota", on_delete=models.PROTECT, related_name="online_payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="USD")
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default="STRIPE")
    provider_intent_id = models.CharField(max_length=128, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="CREATED")
    created_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="online_payments")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self): return f"{self.provider} • {self.cuota_id} • {self.status}"