from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from datetime import date, time



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

class OtpUsers(models.Model):
    otp_id = models.AutoField(primary_key=True)
    user= models.ForeignKey('User', on_delete=models.CASCADE, related_name='otp_users')
    is_phone_verified  = models.BooleanField(default=False)
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(blank=True, null=True)


class User(AbstractBaseUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('receptionist', 'Receptionist'),
        ('doctor', 'Doctor'),
        ('patient', 'Patient'),
    ]
    user_id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=128)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='patient')
    status = models.BooleanField( default=False)
    full_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10)
    address = models.TextField()
    birth_day = models.DateField()
    phone = models.CharField(max_length=10, unique= True)
    gmail = models.EmailField(max_length=254,unique=True)    
    specialty = models.CharField(max_length=50, blank=True, null=True)
    degree = models.CharField(max_length=50, blank=True, null=True)
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
    def is_superuser(self):
        return self.role == 'admin'

    @property
    def is_staff(self):
        return self.role in ['admin', 'receptionist', 'doctor']

    @property
    def is_active(self):
        return self.status

    class Meta:
        db_table = 'users'

class Appointment(models.Model):
    appointment_id = models.AutoField(primary_key=True)
    patient_user_id = models.ForeignKey(User, on_delete=models.CASCADE, related_name='appointments_as_patient')
    doctor_user_id = models.ForeignKey(User, on_delete=models.CASCADE, related_name='appointments_as_doctor')
    appointment_day = models.DateField(default=date.today)
    appointment_status = models.CharField(max_length=20, default='pending')
    appointment_time = models.TimeField(default=time(12, 0))
    description = models.TextField(blank=True, null=True)
    appointment_created_at = models.DateTimeField(auto_now_add=True)
    appointment_updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Appointment {self.appointment_id}"

    class Meta:
        db_table = 'appointments'

class MedicalRecord(models.Model):
    record_id = models.AutoField(primary_key=True)
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='medical_records')
    record_status = models.CharField(max_length=20)
    record_note = models.TextField(blank=True, null=True)
    diagnosis = models.TextField(blank=True, null=True)
    treatment = models.TextField(blank=True, null=True)
    result = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Medical Record {self.record_id}"

    class Meta:
        db_table = 'medical_records'

class PatientTest(models.Model):
    patient_test_id = models.AutoField(primary_key=True)
    record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name='patient_tests')
    test = models.ForeignKey('LabTest', on_delete=models.CASCADE, related_name='patient_tests')
    result = models.TextField(blank=True, null=True)
    test_date = models.DateField()
    status = models.CharField(max_length=20)
    performed_by_doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='performed_tests')

    def __str__(self):
        return f"Patient Test {self.patient_test_id}"

    class Meta:
        db_table = 'patient_tests'

class LabTest(models.Model):
    test_id = models.AutoField(primary_key=True)
    test_name = models.CharField(max_length=100)
    description = models.TextField()
    test_price = models.DecimalField(max_digits=10, decimal_places=2)
    test_category = models.CharField(max_length=100)

    def __str__(self):
        return self.test_name

    class Meta:
        db_table = 'lab_test'

class Prescription(models.Model):
    prescription_id = models.AutoField(primary_key=True)
    record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name='prescriptions')
    prescription_date = models.DateField()
    doctor_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prescriptions')
    prescription_note = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Prescription {self.prescription_id}"

    class Meta:
        db_table = 'prescriptions'

class Medication(models.Model):
    medication_id = models.AutoField(primary_key=True)
    medication_name = models.CharField(max_length=100)
    medication_description = models.TextField()
    medication_unit = models.CharField(max_length=20)
    medication_price = models.DecimalField(max_digits=10, decimal_places=2)
    recommended_dosage = models.CharField(max_length=50)
    expiration_date = models.DateField()
    stock_quantity = models.IntegerField()
    medication_category = models.CharField(max_length=100)

    def __str__(self):
        return self.medication_name

    class Meta:
        db_table = 'medications'

class PrescriptionDetail(models.Model):
    detail_id = models.AutoField(primary_key=True)
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='prescription_details')
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name='prescription_details')
    duration = models.CharField(max_length=50)
    dosage = models.CharField(max_length=50)
    quantity = models.IntegerField()
    instructions = models.TextField()
    frequency = models.CharField(max_length=50)

    def __str__(self):
        return f"Prescription Detail {self.detail_id}"

    class Meta:
        db_table = 'prescription_details'

class Payment(models.Model):
    payment_id = models.AutoField(primary_key=True)
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='payments')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_timestamp = models.DateTimeField()
    payment_method = models.CharField(max_length=50)
    payment_status = models.CharField(max_length=20)

    def __str__(self):
        return f"Payment {self.payment_id}"

    class Meta:
        db_table = 'payments'

class PaymentDetail(models.Model):
    payment_detail_id = models.AutoField(primary_key=True)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='payment_details')
    item_type = models.CharField(max_length=50)
    item_id = models.IntegerField()
    description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField()
    discount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Payment Detail {self.payment_detail_id}"

    class Meta:
        db_table = 'payment_details'
