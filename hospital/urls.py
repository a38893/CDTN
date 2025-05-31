from hospital import views
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from hospital.api.register import RegisterAPI, register_page
from hospital.api.login import LoginAPI, login_page
from hospital.api.appointment_register import AppointmentAPI, appointment_page
from hospital.api.appointment_view_history import appointment_history
from hospital.api.medical_record_view_history import MedicalRecordHistoryViewAPI
from hospital.api.verify_otp import VerifyOTP
from hospital.api.resend_otp import ResendOTP
from hospital.api.change_password import ChangePasswordAPI
from hospital.api.reset_password import ResetPasswordAPI
router = DefaultRouter()
router.register(r'appointments', views.AppointmentHistoryViewAPI, basename='appointment'),
router.register(r'medical-records', MedicalRecordHistoryViewAPI, basename='medical-record')
urlpatterns = [
    
    path('api/register/', RegisterAPI.as_view(), name='register_api'),
    path('api/login/', LoginAPI.as_view(), name='login_api'),
    path('api/appointmentregister/', AppointmentAPI.as_view(), name='appointment_api'),
    path('login/', login_page, name='login-page'),
    path('register/', register_page, name='register-page'),
    path('appointment/', appointment_page, name='appointment-page'),
    path('appointment-history/', appointment_history, name='appointment-history'),
    path('api/verify-otp/', VerifyOTP.as_view(), name='verify_otp'),
    path('api/resend-otp/', ResendOTP.as_view(), name='resend_otp'),
    path('api/change-password/', ChangePasswordAPI.as_view(), name='change_password'),
    path('api/', include(router.urls)),
    # path('', home, name='home'),
    path('api/reset-password/', ResetPasswordAPI.as_view(), name='reset_password'),

    path('pay', views.index, name='index'),
    path('payment', views.payment, name='payment'),
    path('payment_ipn', views.payment_ipn, name='payment_ipn'),
    path('payment_return',views.payment_return, name='payment_return'),
    path('query',views.query, name='query'),
    path('refund',views.refund, name='refund')

]