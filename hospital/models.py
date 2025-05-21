
from django.db import models
from django.utils import timezone
from datetime import date, time
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager


class UserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('Tên đăng nhập là bắt buộc.')
        user = self.model(username=username, **extra_fields)
        user.set_password(password)  # Mã hóa mật khẩu
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('status', 'active')
        return self.create_user(username, password, **extra_fields)

class User(AbstractBaseUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('receptionist', 'Receptionist'),
        ('doctor', 'Doctor'),
        ('patient', 'Patient'),
    ]
    user_id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=128)  # Tăng độ dài cho mật khẩu mã hóa
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='patient')
    status = models.CharField(max_length=20, default='active')
    full_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10)
    address = models.TextField()
    birth_day = models.DateField()
    phone = models.CharField(max_length=10)
    specialty = models.CharField(max_length=50, blank=True, null=True)
    degree = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['full_name', 'gender', 'address', 'birth_day', 'phone']


    def __str__(self):
        return self.username

    def has_perm(self, perm, obj=None):
        return self.role == 'admin'

    def has_module_perms(self, app_label):
        return self.role == 'admin'

    @property
    def is_staff(self):
        return self.role == 'admin'

    @property
    def is_active(self):
        return self.status == 'active'

    class Meta:
        db_table = 'custom_user'  # Tránh xung đột với bảng 'user' mặc định

# Appointment model
class Appointment(models.Model):
    # appointment_id = models.IntegerField(primary_key=True, null=False, blank=False, editable=False)
    patient_user_id = models.ForeignKey(User, on_delete=models.CASCADE, related_name='patient_appointments')
    doctor_user_id = models.ForeignKey(User, on_delete=models.CASCADE, related_name='doctor_appointments')
    appointment_day = models.DateField(default=date.today)  # chỉ lấy ngày
    appointment_time = models.TimeField(default=time(12, 0))
    appointment_status = models.CharField(max_length=20, default='scheduled')
    description = models.TextField(blank=True, null=True)
    def __str__(self):
        return f"Appointment {self.id} - {self.patient.full_name} with {self.doctor.full_name}"

    class Meta:
        db_table = 'appointments'

# Medical Record model
class MedicalRecord(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='medical_records')
    record_status = models.CharField(max_length=20, default='active')
    notes = models.TextField(blank=True, null=True)
    diagnosis = models.TextField()
    treatment = models.TextField()
    result = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Medical Record {self.id} - Appointment {self.appointment.id}"

    class Meta:
        db_table = 'medical_record'

# Prescription model
class Prescription(models.Model):
    record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name='prescriptions')
    prescription_date = models.DateField()
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prescribed_by')
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Prescription {self.id} - Record {self.record.id}"

    class Meta:
        db_table = 'prescriptions'

# Medication model
class Medication(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    unit = models.CharField(max_length=20)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    recommended_dosage = models.CharField(max_length=50)
    expiration_date = models.DateField()
    stock_quantity = models.IntegerField()

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'medications'

# Prescription Detail model (junction table for Prescription and Medication)
class PrescriptionDetail(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='prescription_details')
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name='prescription_details')
    duration = models.CharField(max_length=50)
    dosage = models.CharField(max_length=50)
    quantity = models.IntegerField()
    instructions = models.TextField()
    frequency = models.CharField(max_length=50)

    def __str__(self):
        return f"Prescription Detail {self.id} - {self.medication.name}"

    class Meta:
        db_table = 'prescription_details'

# Lab Test model
class LabTest(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    test_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'lab_test'

# Patient Test model (junction table for MedicalRecord and LabTest)
class PatientTest(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='patient_tests')
    test = models.ForeignKey(LabTest, on_delete=models.CASCADE, related_name='patient_tests')
    result = models.TextField(blank=True, null=True)
    test_date = models.DateField()
    status = models.CharField(max_length=20, default='pending')
    performed_by_doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tests_performed', blank=True, null=True)
    requested_by_doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tests_requested')
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Patient Test {self.id} - {self.test.name}"

    class Meta:
        db_table = 'patient_tests'

# Payment model
class Payment(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='payments')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField()
    payment_method = models.CharField(max_length=50)
    payment_status = models.CharField(max_length=20, default='pending')

    def __str__(self):
        return f"Payment {self.id} - Appointment {self.appointment.id}"

    class Meta:
        db_table = 'payments'

# Payment Detail model
class PaymentDetail(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='payment_details')
    item_type = models.CharField(max_length=50)  # e.g., 'lab_test', 'medication', 'consultation'
    item = models.CharField(max_length=100)  # Name of the item (e.g., test name, medication name)
    description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Payment Detail {self.id} - {self.item}"

    class Meta:
        db_table = 'payment_details'