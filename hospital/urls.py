from hospital import views
from django.urls import include, path
from .views import AppointmentAPI, RegisterAPI, LoginAPI,  TestAuth, login_page, register_page, appointment_page, AppointmentHistoryViewAPI, appointment_history
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'appointments', views.AppointmentHistoryViewAPI, basename='appointment')
urlpatterns = [
    path('api/register/', RegisterAPI.as_view(), name='register_api'),
    path('api/login/', LoginAPI.as_view(), name='login_api'),
    path('api/appointmentregister/', AppointmentAPI.as_view(), name='appointment_api'),
    path('api/TestAuth/',TestAuth.as_view(), name = 'test_auth'),
    path('login/', login_page, name='login-page'),
    path('register/', register_page, name='register-page'),
    path('appointment/', appointment_page, name='appointment-page'),
    path('appointment-history/', appointment_history, name='appointment-history'),

    path('api/', include(router.urls)),


]