# urls.py
from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from .views_face_dry import FaceIdentifyAWSDryRunView
from .views_face import FaceRegisterAWSView, FaceIdentifyAndLogAWSView
from .views_api import (
    # Auth / perfil
    RegisterView, me, me_update, change_password,
    # ViewSets
    AdminUserViewSet, RolViewSet, PermissionViewSet,
    UnidadViewSet, CuotaViewSet, PagoViewSet, InfraccionViewSet,
    AvisoViewSet, TareaViewSet, AreaComunViewSet, StaffViewSet,
    VisitorViewSet, VisitViewSet, VehiculoViewSet, SolicitudVehiculoViewSet,
    # Vistas de Estado de cuenta
    EstadoCuentaView, EstadoCuentaExportCSV,
    # Mock pagos
    MockCheckoutView, MockUploadReceiptView, MockVerifyReceiptView, SnapshotCheckView, SnapshotPingView
)

router = DefaultRouter()
router.register(r'admin/users', AdminUserViewSet, basename='admin-users')
router.register(r'roles', RolViewSet, basename='roles')
router.register(r'permissions', PermissionViewSet, basename='permissions')
router.register(r'unidades', UnidadViewSet, basename='unidades')
router.register(r'cuotas', CuotaViewSet, basename='cuotas')
router.register(r'pagos', PagoViewSet, basename='pagos')
router.register(r'infracciones', InfraccionViewSet, basename='infracciones')
router.register(r'avisos', AvisoViewSet, basename='avisos')
router.register(r'tareas', TareaViewSet, basename='tareas')
router.register(r'areas-comunes', AreaComunViewSet, basename='areas-comunes')
router.register(r'staff', StaffViewSet, basename='staff')
router.register(r'visitors', VisitorViewSet, basename='visitors')
router.register(r'visits', VisitViewSet, basename='visits')
router.register(r'vehiculos', VehiculoViewSet, basename='vehiculos')
router.register(r'solicitudes-vehiculo', SolicitudVehiculoViewSet, basename='solicitudes-vehiculo')

urlpatterns = [
    # Auth / perfil
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', obtain_auth_token, name='token_login'),
    path('auth/me/', me, name='me'),
    path('auth/me/update/', me_update, name='me-update'),
    path('auth/change-password/', change_password, name='change-password'),

    # Estado de cuenta
    path('estado-cuenta/', EstadoCuentaView.as_view(), name='estado-cuenta'),
    path('estado-cuenta/export/', EstadoCuentaExportCSV.as_view(), name='estado-cuenta-export'),

    # Mock pagos
    path('pagos/mock/checkout/', MockCheckoutView.as_view(), name='mock-checkout'),
    path('pagos/mock/upload-receipt/', MockUploadReceiptView.as_view(), name='mock-upload-receipt'),
    path('pagos/mock/verify/', MockVerifyReceiptView.as_view(), name='mock-verify'),
    path("access/snapshot-check/", SnapshotCheckView.as_view(), name="snapshot-check"),
    path("access/snapshot-ping/", SnapshotPingView.as_view()),
    #IA
    path("face/register-aws/", FaceRegisterAWSView.as_view(), name="face-register-aws"),
    path("face/identify-and-log-aws/", FaceIdentifyAndLogAWSView.as_view(), name="face-identify-and-log-aws"),
     path("face/identify-aws-dry/", FaceIdentifyAWSDryRunView.as_view(), name="face-identify-aws-dry"),
]

# Rutas del router
urlpatterns += router.urls

