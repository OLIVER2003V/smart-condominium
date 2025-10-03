# smartcondominio/admin.py
from django.contrib import admin
from .models import (
    Profile, Unidad,
    Aviso,
    Tarea, TareaComentario,
    AreaComun, AreaDisponibilidad, ReservaArea,
    Visitor, Visit,
    Vehiculo, SolicitudVehiculo, AccessEvent
)

# --- Profile ---
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role")
    search_fields = ("user__username",)
    list_filter = ("role",)

# --- Unidades ---
@admin.register(Unidad)
class UnidadAdmin(admin.ModelAdmin):
    list_display = (
        "id", "manzana", "lote", "numero",
        "tipo", "estado", "propietario", "residente",
        "is_active", "updated_at",
    )
    list_filter = ("manzana", "lote", "estado", "tipo", "is_active")
    search_fields = (
        "manzana", "lote", "numero",
        "propietario__first_name", "propietario__last_name",
        "residente__first_name", "residente__last_name",
    )
    ordering = ("manzana", "lote", "numero")
    autocomplete_fields = ("propietario", "residente")

# --- Avisos ---
@admin.register(Aviso)
class AvisoAdmin(admin.ModelAdmin):
    list_display = ("id", "titulo", "audiencia", "status", "publish_at", "creado_por", "is_active")
    list_filter = ("audiencia", "status", "is_active")
    search_fields = ("titulo", "cuerpo", "torre")
    filter_horizontal = ("unidades", "roles")

# --- Tareas ---
@admin.register(Tarea)
class TareaAdmin(admin.ModelAdmin):
    list_display = (
        "id", "titulo", "prioridad", "estado",
        "asignado_a", "asignado_a_rol", "unidad",
        "fecha_limite", "creado_por", "is_active",
    )
    list_filter = ("prioridad", "estado", "asignado_a_rol", "is_active")
    search_fields = (
        "titulo", "descripcion",
        "asignado_a__username", "creado_por__username",
        "unidad__manzana", "unidad__lote", "unidad__numero",
    )

@admin.register(TareaComentario)
class TareaComentarioAdmin(admin.ModelAdmin):
    list_display = ("id", "tarea", "autor", "created_at")
    search_fields = ("tarea__titulo", "autor__username", "cuerpo")

# --- Áreas comunes ---
@admin.register(AreaComun)
class AreaComunAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "capacidad", "activa", "requiere_aprobacion", "costo_por_hora")
    search_fields = ("nombre", "ubicacion")
    list_filter = ("activa", "requiere_aprobacion")

@admin.register(AreaDisponibilidad)
class AreaDisponibilidadAdmin(admin.ModelAdmin):
    list_display = ("area", "dia_semana", "hora_inicio", "hora_fin", "max_horas_por_reserva")
    list_filter = ("area", "dia_semana")

@admin.register(ReservaArea)
class ReservaAreaAdmin(admin.ModelAdmin):
    list_display = ("area", "fecha_inicio", "fecha_fin", "estado", "usuario", "unidad", "monto_total")
    list_filter = ("estado", "area")
    search_fields = ("nota",)

# --- Visitantes y Visitas ---
@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    list_display = ("full_name", "doc_type", "doc_number", "phone")
    search_fields = ("full_name", "doc_number")

@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ("id", "visitor", "unit", "host_resident", "status", "entry_at", "exit_at", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("visitor__full_name", "visitor__doc_number", "vehicle_plate", "purpose")

# --- Vehículos / Solicitudes ---
@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = ("placa", "propietario", "unidad", "tipo", "activo", "autorizado_en")
    list_filter = ("activo", "tipo", "unidad")
    search_fields = ("placa", "propietario__username", "propietario__first_name", "propietario__last_name")

@admin.register(SolicitudVehiculo)
class SolicitudVehiculoAdmin(admin.ModelAdmin):
    list_display = ("placa", "solicitante", "estado", "unidad", "created_at", "revisado_en")
    list_filter = ("estado", "unidad", "tipo")
    search_fields = ("placa", "solicitante__username", "solicitante__first_name", "solicitante__last_name")
    
@admin.register(AccessEvent)
class AccessEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "camera_id", "plate_norm", "score", "decision", "opened")
    search_fields = ("plate_norm", "plate_raw", "reason")
    list_filter = ("decision", "opened", "camera_id")
