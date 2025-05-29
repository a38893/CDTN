import datetime, random
from django.utils import timezone

from django.contrib import messages
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, permissions, filters
from django.shortcuts import redirect, render
from .serializers import AppointmentSerializer
from rest_framework.permissions import IsAuthenticated
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer, AppointmentSerializer, AppointmentHistoryViewSerializer
from .models import  MedicalRecord, Payment, User, Appointment
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import check_password
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import renderers
from rest_framework.decorators import action
from django.db.models import Q
from .sms_otp import send_otp_email



def home(request):
    return render(request, '/home.html')


def gen_otp():
    return str(random.randint(100000, 999999))

class VerifyOTP(APIView):
    def post(self, request):
        user_id = request.data.get('user_id')
        otp = request.data.get('otp')
        try:
            user = User.objects.get(user_id=user_id)
            if (user.otp_code == otp and
                 user.otp_created_at and 
                 timezone.now() - user.otp_created_at < timezone.timedelta(minutes=5)
                 ):
                user.status= True
                user.is_phone_verified = True
                user.otp_code = None
                user.save()
                return Response({"message": "Xác thực thành công!"}, status=status.HTTP_200_OK)
            return Response({"message": "Mã OTP không hợp lệ hoặc đã hết hạn!"}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({"message": "Người dùng không tồn tại!"}, status=status.HTTP_404_NOT_FOUND)


class ResendOTP(APIView):
    def post(self, request):
        user_id = request.data.get('user_id')
        try:
            user = User.objects.get(user_id=user_id)
            # Sinh OTP mới
            otp = gen_otp()
            user.otp_code = otp
            user.otp_created_at = timezone.now()
            user.save()
            send_otp_email(user.phone, otp)
            return Response({"message": "Đã gửi lại mã OTP!"}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"message": "Người dùng không tồn tại!"}, status=status.HTTP_404_NOT_FOUND)
class ResetPasswordAPI(APIView):
    def post(self, request):
        username = request.data.get('username')  # Lấy username từ request
        otp = request.data.get('otp')
        new_password = request.data.get('new_password')
        try:
            user = User.objects.filter(username=username).order_by('-user_id').first()
            if user is None:
                return Response({"message": "Không tìm thấy người dùng với username này!"}, status=status.HTTP_404_NOT_FOUND)
            if (
                str(user.otp_code) == str(otp)
                and user.otp_created_at
                and timezone.now() - user.otp_created_at < timezone.timedelta(minutes=5)
            ):
                user.set_password(new_password)
                user.otp_code = None
                user.otp_created_at = None
                user.save()
                return Response({"message": "Đặt lại mật khẩu thành công!"}, status=status.HTTP_200_OK)
            return Response({"message": "OTP không hợp lệ hoặc đã hết hạn!"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"message": f"Lỗi: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

class ChangePasswordAPI(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        user = request.user
        if not user.check_password(old_password):
            return Response({"message": "Mật khẩu cũ không đúng!"}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(new_password)
        user.save()
        return Response({"message": "Đổi mật khẩu thành công!"}, status=status.HTTP_200_OK)
class RegisterAPI(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            otp = gen_otp()
            #cài mặc định là chưa active
            user = serializer.save(status=False, otp_code=otp, otp_created_at=timezone.now())
            #gửi OTP qua SMS
            send_otp_email(user.gmail, otp)
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
                if not user.status:
                    return Response({"message": "Tài khoản chưa được kích hoạt! Vui lòng kiểm tra SMS để kích hoạt tài khoản."}, status=status.HTTP_403_FORBIDDEN)
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
            doctor_user = User.objects.get(user_id=doctor_user_id)
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
                    description=description
                )
                # Payment.objects.create(
                #     appointment=appointment,
                #     amount=30000,
                #     payment_status='pending',  
                #     # payment_method='bank_transfer'  # Phương thức thanh toán mặc định
                # )
                
                return Response({
                    "message": "Đăng ký lịch hẹn thành công!",
                    "appointment_id": appointment.appointment_id,
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
            if appointment.appointment_status in ['pending']:
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


class MedicalRecordHistoryViewAPI(viewsets.ReadOnlyModelViewSet):
    serializer_class = AppointmentHistoryViewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        if not queryset.exists():
            return Response(
                {"message": "Bạn chưa có lịch sử khám bệnh nào."},
                status=status.HTTP_200_OK
            )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def get_queryset(self):
        return MedicalRecord.objects.filter(
            appointment__patient_user_id=self.request.user
        ).order_by('-appointment__appointment_day')





# payment 
import hashlib
import hmac
import json
import urllib
import urllib.parse
import urllib.request
import random
import requests
from datetime import datetime
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from urllib.parse import quote
from hospital.forms import PaymentForm
from hospital.vnpay import vnpay


def index(request):
    return render(request, "payment/index.html", {"title": "Danh sách demo"})


def hmacsha256(key, data):
    byteKey = key.encode('utf-8')
    byteData = data.encode('utf-8')
    return hmac.new(byteKey, byteData, hashlib.sha256).hexdigest()


def payment(request):

    if request.method == 'POST':
        # Process input data and build url payment
        form = PaymentForm(request.POST)
        if form.is_valid():
            order_type = form.cleaned_data['order_type']
            order_id = form.cleaned_data['order_id']
            amount = form.cleaned_data['amount']
            order_desc = form.cleaned_data['order_desc']
            bank_code = form.cleaned_data['bank_code']
            language = form.cleaned_data['language']
            ipaddr = get_client_ip(request)
            # Build URL Payment
            vnp = vnpay()
            vnp.requestData['vnp_Version'] = '2.1.0'
            vnp.requestData['vnp_Command'] = 'pay'
            vnp.requestData['vnp_TmnCode'] = settings.VNPAY_TMN_CODE
            vnp.requestData['vnp_Amount'] = amount * 100
            vnp.requestData['vnp_CurrCode'] = 'VND'
            vnp.requestData['vnp_TxnRef'] = order_id
            vnp.requestData['vnp_OrderInfo'] = order_desc
            vnp.requestData['vnp_OrderType'] = order_type
            # Check language, default: vn
            if language and language != '':
                vnp.requestData['vnp_Locale'] = language
            else:
                vnp.requestData['vnp_Locale'] = 'vn'
                # Check bank_code, if bank_code is empty, customer will be selected bank on VNPAY
            if bank_code and bank_code != "":
                vnp.requestData['vnp_BankCode'] = bank_code

            vnp.requestData['vnp_CreateDate'] = datetime.now().strftime('%Y%m%d%H%M%S')  # 20150410063022
            vnp.requestData['vnp_IpAddr'] = ipaddr
            vnp.requestData['vnp_ReturnUrl'] = settings.VNPAY_RETURN_URL
            vnpay_payment_url = vnp.get_payment_url(settings.VNPAY_PAYMENT_URL, settings.VNPAY_HASH_SECRET_KEY)
            print(vnpay_payment_url)
            return redirect(vnpay_payment_url)
        else:
            print("Form input not validate")
    else:
        return render(request, "payment/payment.html", {"title": "Thanh toán"})


def payment_ipn(request):
    inputData = request.GET
    if inputData:
        vnp = vnpay()
        vnp.responseData = inputData.dict()
        order_id = inputData['vnp_TxnRef']
        amount = inputData['vnp_Amount']
        order_desc = inputData['vnp_OrderInfo']
        vnp_TransactionNo = inputData['vnp_TransactionNo']
        vnp_ResponseCode = inputData['vnp_ResponseCode']
        vnp_TmnCode = inputData['vnp_TmnCode']
        vnp_PayDate = inputData['vnp_PayDate']
        vnp_BankCode = inputData['vnp_BankCode']
        vnp_CardType = inputData['vnp_CardType']
        if vnp.validate_response(settings.VNPAY_HASH_SECRET_KEY):
            # Check & Update Order Status in your Database
            # Your code here
            firstTimeUpdate = True
            totalamount = True
            if totalamount:
                if firstTimeUpdate:
                    if vnp_ResponseCode == '00':
                        print('Payment Success. Your code implement here')
                    else:
                        print('Payment Error. Your code implement here')

                    # Return VNPAY: Merchant update success
                    result = JsonResponse({'RspCode': '00', 'Message': 'Confirm Success'})
                else:
                    # Already Update
                    result = JsonResponse({'RspCode': '02', 'Message': 'Order Already Update'})
            else:
                # invalid amount
                result = JsonResponse({'RspCode': '04', 'Message': 'invalid amount'})
        else:
            # Invalid Signature
            result = JsonResponse({'RspCode': '97', 'Message': 'Invalid Signature'})
    else:
        result = JsonResponse({'RspCode': '99', 'Message': 'Invalid request'})

    return result


def payment_return(request):
    inputData = request.GET
    if inputData:
        vnp = vnpay()
        vnp.responseData = inputData.dict()
        order_id = inputData['vnp_TxnRef']
        amount = int(inputData['vnp_Amount']) / 100
        order_desc = inputData['vnp_OrderInfo']
        vnp_TransactionNo = inputData['vnp_TransactionNo']
        vnp_ResponseCode = inputData['vnp_ResponseCode']
        vnp_TmnCode = inputData['vnp_TmnCode']
        vnp_PayDate = inputData['vnp_PayDate']
        vnp_BankCode = inputData['vnp_BankCode']
        vnp_CardType = inputData['vnp_CardType']
        if vnp.validate_response(settings.VNPAY_HASH_SECRET_KEY):
            if vnp_ResponseCode == "00":
                return render(request, "payment/payment_return.html", {"title": "Kết quả thanh toán",
                                                               "result": "Thành công", "order_id": order_id,
                                                               "amount": amount,
                                                               "order_desc": order_desc,
                                                               "vnp_TransactionNo": vnp_TransactionNo,
                                                               "vnp_ResponseCode": vnp_ResponseCode})
            else:
                return render(request, "payment/payment_return.html", {"title": "Kết quả thanh toán",
                                                               "result": "Lỗi", "order_id": order_id,
                                                               "amount": amount,
                                                               "order_desc": order_desc,
                                                               "vnp_TransactionNo": vnp_TransactionNo,
                                                               "vnp_ResponseCode": vnp_ResponseCode})
        else:
            return render(request, "payment/payment_return.html",
                          {"title": "Kết quả thanh toán", "result": "Lỗi", "order_id": order_id, "amount": amount,
                           "order_desc": order_desc, "vnp_TransactionNo": vnp_TransactionNo,
                           "vnp_ResponseCode": vnp_ResponseCode, "msg": "Sai checksum"})
    else:
        return render(request, "payment/payment_return.html", {"title": "Kết quả thanh toán", "result": ""})


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

n = random.randint(10**11, 10**12 - 1)
n_str = str(n)
while len(n_str) < 12:
    n_str = '0' + n_str


def query(request):
    if request.method == 'GET':
        return render(request, "payment/query.html", {"title": "Kiểm tra kết quả giao dịch"})

    url = settings.VNPAY_API_URL
    secret_key = settings.VNPAY_HASH_SECRET_KEY
    vnp_TmnCode = settings.VNPAY_TMN_CODE
    vnp_Version = '2.1.0'

    vnp_RequestId = n_str
    vnp_Command = 'querydr'
    vnp_TxnRef = request.POST['order_id']
    vnp_OrderInfo = 'kiem tra gd'
    vnp_TransactionDate = request.POST['trans_date']
    vnp_CreateDate = datetime.now().strftime('%Y%m%d%H%M%S')
    vnp_IpAddr = get_client_ip(request)

    hash_data = "|".join([
        vnp_RequestId, vnp_Version, vnp_Command, vnp_TmnCode,
        vnp_TxnRef, vnp_TransactionDate, vnp_CreateDate,
        vnp_IpAddr, vnp_OrderInfo
    ])

    secure_hash = hmac.new(secret_key.encode(), hash_data.encode(), hashlib.sha256).hexdigest()

    data = {
        "vnp_RequestId": vnp_RequestId,
        "vnp_TmnCode": vnp_TmnCode,
        "vnp_Command": vnp_Command,
        "vnp_TxnRef": vnp_TxnRef,
        "vnp_OrderInfo": vnp_OrderInfo,
        "vnp_TransactionDate": vnp_TransactionDate,
        "vnp_CreateDate": vnp_CreateDate,
        "vnp_IpAddr": vnp_IpAddr,
        "vnp_Version": vnp_Version,
        "vnp_SecureHash": secure_hash
    }

    headers = {"Content-Type": "application/json"}

    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        response_json = json.loads(response.text)
    else:
        response_json = {"error": f"Request failed with status code: {response.status_code}"}

    return render(request, "query.html", {"title": "Kiểm tra kết quả giao dịch", "response_json": response_json})

def refund(request):
    if request.method == 'GET':
        return render(request, "payment/refund.html", {"title": "Hoàn tiền giao dịch"})

    url = settings.VNPAY_API_URL
    secret_key = settings.VNPAY_HASH_SECRET_KEY
    vnp_TmnCode = settings.VNPAY_TMN_CODE
    vnp_RequestId = n_str
    vnp_Version = '2.1.0'
    vnp_Command = 'refund'
    vnp_TransactionType = request.POST['TransactionType']
    vnp_TxnRef = request.POST['order_id']
    vnp_Amount = request.POST['amount']
    vnp_OrderInfo = request.POST['order_desc']
    vnp_TransactionNo = '0'
    vnp_TransactionDate = request.POST['trans_date']
    vnp_CreateDate = datetime.now().strftime('%Y%m%d%H%M%S')
    vnp_CreateBy = 'user01'
    vnp_IpAddr = get_client_ip(request)

    hash_data = "|".join([
        vnp_RequestId, vnp_Version, vnp_Command, vnp_TmnCode, vnp_TransactionType, vnp_TxnRef,
        vnp_Amount, vnp_TransactionNo, vnp_TransactionDate, vnp_CreateBy, vnp_CreateDate,
        vnp_IpAddr, vnp_OrderInfo
    ])

    secure_hash = hmac.new(secret_key.encode(), hash_data.encode(), hashlib.sha256).hexdigest()

    data = {
        "vnp_RequestId": vnp_RequestId,
        "vnp_TmnCode": vnp_TmnCode,
        "vnp_Command": vnp_Command,
        "vnp_TxnRef": vnp_TxnRef,
        "vnp_Amount": vnp_Amount,
        "vnp_OrderInfo": vnp_OrderInfo,
        "vnp_TransactionDate": vnp_TransactionDate,
        "vnp_CreateDate": vnp_CreateDate,
        "vnp_IpAddr": vnp_IpAddr,
        "vnp_TransactionType": vnp_TransactionType,
        "vnp_TransactionNo": vnp_TransactionNo,
        "vnp_CreateBy": vnp_CreateBy,
        "vnp_Version": vnp_Version,
        "vnp_SecureHash": secure_hash
    }

    headers = {"Content-Type": "application/json"}

    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        response_json = json.loads(response.text)
    else:
        response_json = {"error": f"Request failed with status code: {response.status_code}"}

    return render(request, "payment/refund.html", {"title": "Kết quả hoàn tiền giao dịch", "response_json": response_json})     