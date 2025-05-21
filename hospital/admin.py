from django.contrib import admin
from .models import Appointment, AbstractBaseUser, UserManager, PrescriptionDetail, LabTest, Medication, MedicalRecord, Payment, PatientTest, PaymentDetail, User, Prescription

# Register your models here.
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
