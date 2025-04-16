from django.urls import path
from .views import AppointmentAPI, RegisterAPI, LoginAPI,  TestAuth

urlpatterns = [
    path('api/register/', RegisterAPI.as_view(), name='register_api'),
    path('api/login/', LoginAPI.as_view(), name='login_api'),
    path('api/appointment/', AppointmentAPI.as_view(), name='appointment_api'),
    path('api/TestAuth/',TestAuth.as_view(), name = 'test_auth')
]