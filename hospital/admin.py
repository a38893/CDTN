from django.utils import timezone
from django.db import models
from django.contrib import admin
from .models import Appointment, AbstractBaseUser, UserManager, LabTest, Medication, MedicalRecord, Payment, PatientTest,PaymentDetail, User, Prescription
from django import forms
# # Register your models here.
# admin.site.register(Appointment)
# admin.site.register(PrescriptionDetail)
# admin.site.register(LabTest)
# admin.site.register(Medication)
# admin.site.register(MedicalRecord)
# admin.site.register(Payment)
# admin.site.register(PatientTest)
# admin.site.register(User)
admin.site.register(Prescription)
# admin.site.register(PaymentDetail)
admin.site.site_header = "Quản lý bệnh viện LHM"



@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('appointment_id', 'patient_user_id', 'doctor_user_id', 'appointment_day', 'appointment_time', 'appointment_status')
    search_fields = ('patient_user_id__username', 'doctor_user_id__username', 'appointment_day', 'appointment_time', 'appointment_id')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.role in ['admin', 'receptionist']:
            return qs
        elif request.user.role == 'doctor':
            return qs.filter(doctor_user_id=request.user)
        return qs.none()
    
    def has_view_permission(self, request, obj = None):
        return request.user.role in ['admin', 'receptionist', 'doctor']

    def has_change_permission(self, request, obj=None):
        return request.user.role in ['admin', 'receptionist']
    
    def has_delete_permission(self, request, obj=None):
        return request.user.role in ['admin', 'receptionist']
    def has_add_permission(self, request):
        return request.user.role in ['admin', 'receptionist']

class UserAdminForm(forms.ModelForm):
    class Meta:
        model = User
        fields = '__all__'

    def clead_role(self):
        role = self.cleaned_data.get('role')
        user = self.current_user

        if user.role == 'receptionist' and role != 'patient':
            raise forms.ValidationError("Lễ tân chỉ tạo được tài khoản với vai trò lễ tân!")
        return role
    
    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)

class UsersAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'username', 'role', 'full_name', 'phone','gmail')
    search_fields= ('username','full_name', 'phone', 'gmail','user_id')
    list_filter = ('role',)
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        class CustomForm(form):
            def __new__(cls, *args, **kwargs2):
                kwargs2['current_user'] = request.user
                return form(*args, **kwargs2)
        return CustomForm
    
    def has_view_permission(self, request, obj=None):
        return request.user.role in ['admin', 'receptionist']

    def has_change_permission(self, request, obj=None):
        return request.user.role == 'admin'

    def has_delete_permission(self, request, obj=None):
        return request.user.role == 'admin'

    def has_add_permission(self, request):
        return request.user.role in ['admin', 'receptionist']
    
admin.site.register(User, UsersAdmin)

class PatientTestInline(admin.TabularInline):
    model = PatientTest
    extra = 1

class PrescriptionInline(admin.TabularInline):
    model = Prescription
    extra = 1

@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):

    list_display = ('record_id', 'appointment', 'record_status', 'diagnosis', 'treatment', 'result')
    search_fields = ('record_id', 'appointment__appointment_id', 'diagnosis')
    inlines = [PatientTestInline, PrescriptionInline]

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in instances:
            obj.save()
            obj.refresh_from_db()
            appointment = obj.record.appointment
            payment, created = Payment.objects.get_or_create(
                appointment=appointment,
                defaults={
                    'total_amount': 0,
                    'payment_status': 'unpaid',
                    'payment_method': '',
                    'payment_timestamp': timezone.now()
                }
            )
            if isinstance(obj, PatientTest):
                PaymentDetail.objects.get_or_create(
                    payment=payment,
                    service_type='test',
                    service_id=obj.pk,
                    service_name=str(obj.test),
                    amount=getattr(obj.test, 'test_price', 0)
                )
            elif isinstance(obj, Prescription):
                PaymentDetail.objects.get_or_create(
                    payment=payment,
                    service_type='prescription',
                    service_id=obj.pk,
                    service_name=f"Thuốc: {obj.medication.medication_name}",
                    amount=getattr(obj.medication, 'medication_price', 0) * getattr(obj, 'quantity', 1)
                )
        formset.save_m2m()
        if instances:
            payment = Payment.objects.get(appointment=instances[0].record.appointment)
            total = payment.details.aggregate(total=models.Sum('amount'))['total'] or 0
            payment.total_amount = total
            payment.save()

    def has_view_permission(self, request, obj=None):
        # Admin và lễ tân đều xem được, bác sĩ cũng xem được nếu là bác sĩ của record
        return request.user.role in ['admin', 'receptionist', 'doctor']


    def has_change_permission(self, request, obj=None):
        # Admin toàn quyền, bác sĩ chỉ được sửa record của mình
        if request.user.role == 'admin':
            return True
        if request.user.role == 'doctor':
            if obj is None:
                return True  # Cho phép truy cập trang danh sách
            return obj.appointment.doctor_user_id == request.user
        return False

    def has_add_permission(self, request):
        # Admin và bác sĩ được thêm
        return request.user.role in ['admin', 'doctor']

    def has_delete_permission(self, request, obj=None):
        # Chỉ admin được xóa
        return request.user.role == 'admin'
    


@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = ('medication_id', 'medication_name', 'medication_unit', 'medication_price', 'stock_quantity')
    search_fields = ('medication_name', 'medication_category')

    def has_view_permission(self, request, obj=None):
        # Admin, lễ tân, bác sĩ đều xem được
        return request.user.role in ['admin', 'receptionist', 'doctor']

    def has_change_permission(self, request, obj=None):
        # Admin và lễ tân được sửa
        return request.user.role in ['admin', 'receptionist']

    def has_add_permission(self, request):
        # Admin và lễ tân được thêm
        return request.user.role in ['admin', 'receptionist']

    def has_delete_permission(self, request, obj=None):
        # Admin và lễ tân được xóa
        return request.user.role in ['admin', 'receptionist']
    
@admin.register(LabTest)
class LabTestAdmin(admin.ModelAdmin):
    list_display = ('test_id', 'test_name', 'test_category', 'test_price')
    search_fields = ('test_name', 'test_category')

    def has_view_permission(self, request, obj=None):
        # Admin, lễ tân, bác sĩ đều xem được
        return request.user.role in ['admin', 'receptionist', 'doctor']

    def has_change_permission(self, request, obj=None):
        # Admin và lễ tân được sửa
        return request.user.role in ['admin', 'receptionist']

    def has_add_permission(self, request):
        # Admin và lễ tân được thêm
        return request.user.role in ['admin', 'receptionist']

    def has_delete_permission(self, request, obj=None):
        # Admin và lễ tân được xóa
        return request.user.role in ['admin', 'receptionist']
    
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('payment_id', 'appointment', 'total_amount', 'payment_status', 'payment_method', 'payment_timestamp')
    search_fields = ('appointment__appointment_id', 'payment_status', 'payment_method')
    list_filter = ('payment_status', 'payment_method')
    def has_view_permission(self, request, obj=None):
        # Admin, lễ tân, bác sĩ đều xem được
        return request.user.role in ['admin', 'receptionist']

    def has_change_permission(self, request, obj=None):
        # Admin và lễ tân được sửa
        return request.user.role in ['admin', 'receptionist']

    def has_add_permission(self, request):
        # Admin và lễ tân được thêm
        return request.user.role in ['admin', 'receptionist']

    def has_delete_permission(self, request, obj=None):
        # Admin và lễ tân được xóa
        return request.user.role in ['admin']
    
@admin.register(PaymentDetail)
class PaymentDetailAdmin(admin.ModelAdmin):
    list_display = ('detail_id', 'payment', 'service_type', 'service_id', 'service_name', 'amount')
    search_fields = ('payment__appointment__appointment_id', 'service_type', 'service_name')
    list_filter = ('service_type',)
    def has_view_permission(self, request, obj=None):
        # Admin, lễ tân, bác sĩ đều xem được
        return request.user.role in ['admin', 'receptionist']

    def has_change_permission(self, request, obj=None):
        # Admin và lễ tân được sửa
        return request.user.role in ['admin', 'receptionist']

    def has_add_permission(self, request):
        # Admin và lễ tân được thêm
        return request.user.role in ['admin', 'receptionist']

    def has_delete_permission(self, request, obj=None):
        # Admin và lễ tân được xóa
        return request.user.role in ['admin']
    
@admin.register(PatientTest)
class PatientTestAdmin(admin.ModelAdmin):
    list_display = ('patient_test_id', 'record','result', 'test', 'test_date', 'status', 'performed_by_doctor')
    search_fields = ('record__appointment__appointment_id', 'test__test_name', 'performed_by_doctor__username')
    list_filter = ('status', 'test__test_category')
    def has_view_permission(self, request, obj=None):
        # Admin, lễ tân, bác sĩ đều xem được
        return request.user.role in ['admin', 'receptionist', 'doctor']

    def has_change_permission(self, request, obj=None):
        # Admin và lễ tân được sửa
        return request.user.role in ['admin', 'receptionist', 'doctor']

    def has_add_permission(self, request):
        # Admin và lễ tân được thêm
        return request.user.role in ['admin', 'receptionist', 'doctor']

    def has_delete_permission(self, request, obj=None):
        # Admin và lễ tân được xóa
        return request.user.role in ['admin', 'receptionist', 'doctor']