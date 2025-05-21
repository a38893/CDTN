import datetime
from django.utils import timezone

from django.contrib import messages
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, permissions, filters
from django.shortcuts import redirect, render
from .serializers import AppointmentSerializer
from rest_framework.permissions import IsAuthenticated
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer, AppointmentSerializer, AppointmentHistoryViewSerializer
from .models import User, Appointment
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import check_password
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import renderers
from rest_framework.decorators import action
from django.db.models import Q



class RegisterAPI(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Đăng ký thành công!"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

def register_page(request):
    return render(request, 'register.html')

class LoginAPI(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                # Tạo JWT token
                refresh = RefreshToken.for_user(user)
                user_serializer = UserSerializer(user)
                return Response({
                    "message": "Đăng nhập thành công!",
                    "user": user_serializer.data,
                    "access_token": str(refresh.access_token),
                    "refresh_token": str(refresh)
                }, status=status.HTTP_200_OK)
            return Response({"message": "Sai thông tin!"}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
def login_page(request):
    return render(request, 'login.html')

    
class TestAuth(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "user": str(request.user),
            "is_authenticated": request.user.is_authenticated
        })


# Đặt lịch hẹn
class AppointmentAPI(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Lấy danh sách bác sĩ cho dropdown chọn"""
        # Lấy tất cả bác sĩ có trạng thái active
        doctors = User.objects.filter(role='doctor', status='active')
        
        # Tạo danh sách bác sĩ với thông tin cần thiết
        doctor_list = []
        for doctor in doctors:
            doctor_info = {
                'user_id': doctor.user_id,
                'full_name': doctor.full_name,
                'specialty': doctor.specialty,
                'degree': doctor.degree
            }
            doctor_list.append(doctor_info)
        
        return Response({
            "doctors": doctor_list
        }, status=status.HTTP_200_OK)
    
    def post(self, request):
        serializer = AppointmentSerializer(data=request.data)
        if serializer.is_valid():
            date = serializer.validated_data['date']
            time = serializer.validated_data['time']
            doctor_user_id = serializer.validated_data['doctor_user_id']
            description = serializer.validated_data.get('description', '')
            
            try:
                # Kiểm tra bác sĩ tồn tại và có trạng thái active
                doctor = User.objects.get(user_id=doctor_user_id, role='doctor', status='active')
                
                # Kiểm tra xem bác sĩ có lịch trùng không
                existing_appointment = Appointment.objects.filter(
                    doctor_user_id=doctor,
                    appointment_day=date,
                    appointment_time=time,
                    appointment_status__in=['scheduled', 'confirmed']
                ).exists()
                
                if existing_appointment:
                    return Response({
                        "message": "Bác sĩ đã có lịch hẹn vào thời gian này. Vui lòng chọn thời gian khác!"
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Tạo lịch hẹn mới
                appointment = Appointment.objects.create(
                    patient_user_id=request.user,
                    doctor_user_id=doctor,
                    appointment_day=date,
                    appointment_time=time,
                    appointment_status='scheduled',
                    description=description
                )
                
                return Response({
                    "message": "Đăng ký lịch hẹn thành công!",
                    "appointment_id": appointment.id
                }, status=status.HTTP_201_CREATED)
                
            except User.DoesNotExist:
                return Response({
                    "message": "Bác sĩ không tồn tại hoặc không hoạt động!"
                }, status=status.HTTP_400_BAD_REQUEST)
                
            except ValueError as e:
                return Response({
                    "message": f"Lỗi: {str(e)}"
                }, status=status.HTTP_400_BAD_REQUEST)
                
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

def appointment_page(request):
    return render(request, 'appointment.html')

# Xem lịch sử đặt lịch
class AppointmentHistoryViewAPI(viewsets.ReadOnlyModelViewSet):
    serializer_class = AppointmentHistoryViewSerializer
    permission_classes = [permissions.IsAuthenticated]
    renderer_classes = [renderers.JSONRenderer]
    
    def get_queryset(self):
        # Chỉ lấy lịch hẹn của người dùng hiện tại
        return Appointment.objects.select_related('doctor_user_id').filter(
            patient_user_id=self.request.user
        ).order_by('-appointment_day', '-appointment_time')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        if not queryset.exists():
            return Response(
                {"message": "Bạn chưa có lịch hẹn nào."},
                status=status.HTTP_200_OK
            )
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
            
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "message": "Lấy danh sách lịch hẹn thành công",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            # Kiểm tra xem người dùng có quyền xem lịch hẹn này không
            if instance.patient_user_id != request.user:
                return Response(
                    {"message": "Bạn không có quyền xem lịch hẹn này."},
                    status=status.HTTP_403_FORBIDDEN
                )
                
            serializer = self.get_serializer(instance)
            return Response({
                "message": "Lấy thông tin lịch hẹn thành công",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"message": "Không tìm thấy lịch hẹn."},
                status=status.HTTP_404_NOT_FOUND
            )
            
    # Thêm action để hủy lịch hẹn
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        try:
            appointment = self.get_object()
            
            # Kiểm tra xem người dùng có quyền hủy lịch hẹn này không
            if appointment.patient_user_id != request.user:
                return Response(
                    {"message": "Bạn không có quyền hủy lịch hẹn này."},
                    status=status.HTTP_403_FORBIDDEN
                )
                
            # Chỉ cho phép hủy lịch hẹn chưa diễn ra và chưa bị hủy
            if appointment.appointment_status in ['scheduled', 'confirmed']:
                appointment.appointment_status = 'cancelled'
                appointment.save()
                return Response(
                    {"message": "Hủy lịch hẹn thành công"},
                    status=status.HTTP_200_OK
                )
            return Response(
                {"message": "Không thể hủy lịch hẹn này"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"message": "Không tìm thấy lịch hẹn."},
                status=status.HTTP_404_NOT_FOUND
            )
def appointment_history(request):
    return render(request, 'appointment_history.html')