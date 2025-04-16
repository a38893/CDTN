import datetime
from rest_framework import serializers
from .models import User,Appointment
from django.contrib.auth.hashers import make_password


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['user_id', 'username', 'full_name', 'gender', 'phone', 'address', 'birth_day']
        read_only_fields = ['user_id']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ['username', 'password', 'full_name', 'gender', 'phone', 'address', 'birth_day']

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Tên đăng nhập đã tồn tại!")
        return value

    def validate_birth_day(self, value):
        if isinstance(value, str):
            try:
                value = datetime.strptime(value, '%Y-%m-%d').date()
            except ValueError:
                raise serializers.ValidationError("Ngày sinh phải có định dạng YYYY-MM-DD!")
        if value > datetime.datetime.now().date():
            raise serializers.ValidationError("Ngày sinh không thể là tương lai!")
        return value

    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])
        validated_data['status'] = 'active'
        return User.objects.create(**validated_data)

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})

class RegisterAppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = '__all__'


class AppointmentSerializer(serializers.Serializer):
      date = serializers.DateField()
      time = serializers.TimeField()
      doctor_user_id = serializers.IntegerField()
      description = serializers.CharField(max_length=500, required=False, allow_blank=True)