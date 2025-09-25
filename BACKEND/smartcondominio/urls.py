from django.urls import path
from .views_api import (
    RegisterView, me, AdminUserViewSet, me_update, change_password,
    RolViewSet, PermissionViewSet, UnidadViewSet, CuotaViewSet, PagoViewSet,
    InfraccionViewSet, EstadoCuentaView, EstadoCuentaExportCSV, OnlinePayInitView, StripeWebhookView   # <-- ya lo importaste
)
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token

router = DefaultRouter()
router.register(r'admin/users', AdminUserViewSet, basename='admin-users')
router.register(r'roles', RolViewSet, basename='roles')
router.register(r'permissions', PermissionViewSet, basename='permissions')
router.register(r'unidades', UnidadViewSet, basename='unidades')
router.register(r'cuotas', CuotaViewSet, basename='cuotas')
router.register(r'pagos',  PagoViewSet,  basename='pagos')
router.register(r'infracciones', InfraccionViewSet, basename='infracciones')

urlpatterns = [
    # Auth / perfil
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', obtain_auth_token, name='token_login'),
    path('auth/me/', me, name='me'),
    path('auth/me/update/', me_update, name='me-update'),
    path('auth/change-password/', change_password, name='change-password'),

    # 👇👇 NUEVOS ENDPOINTS DE ESTADO DE CUENTA
    path('estado-cuenta/', EstadoCuentaView.as_view(), name='estado-cuenta'),
    path('estado-cuenta/export/', EstadoCuentaExportCSV.as_view(), name='estado-cuenta-export'),
    
    #Pagos en linea
    path('pay/online/init/', OnlinePayInitView.as_view(), name='pay_online_init'),
    path('stripe/webhook/', StripeWebhookView.as_view(), name='stripe_webhook'),
    
    
]

urlpatterns += router.urls
