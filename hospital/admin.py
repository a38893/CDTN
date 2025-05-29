from django.contrib import admin
from .models import Appointment, AbstractBaseUser, UserManager, PrescriptionDetail, LabTest, Medication, MedicalRecord, Payment, PatientTest, PaymentDetail, User, Prescription

# # Register your models here.
admin.site.register(Appointment)
admin.site.register(PrescriptionDetail)
admin.site.register(LabTest)
admin.site.register(Medication)
admin.site.register(MedicalRecord)
admin.site.register(Payment)
admin.site.register(PatientTest)
admin.site.register(PaymentDetail)
admin.site.register(User)
admin.site.register(Prescription)

admin.site.site_header = "Quản lý bệnh viện"

# @admin.register(Appointment)
# class AppointmentAdmin(admin.ModelAdmin):
#     list_display = ('id', 'patient', 'doctor', 'appointment_date', 'status')
#     search_fields = ('patient__username', 'doctor__username', 'status')
#     def get_queryset(self, request):
#         queryset = super().get_queryset(request)
#         return queryset.select_related('patient', 'doctor')

