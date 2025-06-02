# import datetime, random
# from django.utils import timezone

# from django.contrib import messages
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status, viewsets, permissions, filters
# from django.shortcuts import redirect, render
# from .serializers import AppointmentSerializer
# from rest_framework.permissions import IsAuthenticated
# from .serializers import RegisterSerializer, LoginSerializer, UserSerializer, AppointmentSerializer, AppointmentHistoryViewSerializer
# from .models import  MedicalRecord, Payment, User, Appointment
# from rest_framework_simplejwt.tokens import RefreshToken
# from django.contrib.auth.hashers import check_password
# from django.contrib.auth.decorators import login_required
# from django.contrib.auth import authenticate, login
# from django_filters.rest_framework import DjangoFilterBackend
# from rest_framework import renderers
# from rest_framework.decorators import action
# from django.db.models import Q
# from .sms_otp import send_otp_email



# def home(request):
#     return render(request, '/home.html')

from hospital.api.verify_otp import *
from hospital.api.resend_otp import  *
from hospital.api.register import *
from hospital.api.login import *
from hospital.api.appointment_register import *
from hospital.api.appointment_view_history import *
from hospital.api.medical_record_view_history import *
from hospital.api.reset_password import *
from hospital.api.change_password import *
import random




    






# Đặt lịch hẹn

# Xem lịch sử đặt lịch






# payment 
import hashlib
import hmac
import json
import urllib
import urllib.parse
import urllib.request
import random
import requests
from datetime import datetime, timedelta
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from urllib.parse import quote
from hospital.forms import PaymentForm
from hospital.vnpay import vnpay


def index(request):
    return render(request, "payment/index.html", {"title": "Danh sách demo"})


def hmacsha512(key, data):
    byteKey = key.encode('utf-8')
    byteData = data.encode('utf-8')
    return hmac.new(byteKey, byteData, hashlib.sha512).hexdigest()
def payment(request):
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            order_type = form.cleaned_data['order_type']
            order_id = form.cleaned_data['order_id']
            amount = form.cleaned_data['amount']
            # Xử lý vnp_OrderInfo: thay khoảng trắng bằng +, loại bỏ ký tự đặc biệt
            order_desc = form.cleaned_data['order_desc'].replace(' ', '+').encode('ascii', 'ignore').decode('ascii')
            bank_code = form.cleaned_data['bank_code']
            language = form.cleaned_data['language']
            ipaddr = get_client_ip(request)

            vnp = vnpay()
            vnp.requestData['vnp_Version'] = '2.1.0'
            vnp.requestData['vnp_Command'] = 'pay'
            vnp.requestData['vnp_TmnCode'] = settings.VNPAY_TMN_CODE
            vnp.requestData['vnp_Amount'] = int(amount * 100)  # Nhân 100 theo yêu cầu VNPAY
            vnp.requestData['vnp_CurrCode'] = 'VND'
            vnp.requestData['vnp_TxnRef'] = order_id
            vnp.requestData['vnp_OrderInfo'] = order_desc
            vnp.requestData['vnp_OrderType'] = order_type
            vnp.requestData['vnp_Locale'] = language if language else 'vn'
            if bank_code:
                vnp.requestData['vnp_BankCode'] = bank_code
            vnp.requestData['vnp_CreateDate'] = datetime.now().strftime('%Y%m%d%H%M%S')
            vnp.requestData['vnp_IpAddr'] = ipaddr
            vnp.requestData['vnp_ReturnUrl'] = settings.VNPAY_RETURN_URL
            vnp.requestData['vnp_ExpireDate'] = (datetime.now() + timedelta(minutes=15)).strftime('%Y%m%d%H%M%S')

            # Gọi get_payment_url với đúng tham số
            vnpay_payment_url = vnp.get_payment_url(settings.VNPAY_PAYMENT_URL, settings.VNPAY_HASH_SECRET_KEY)
            print(vnpay_payment_url)
            return redirect(vnpay_payment_url)
        else:
            print("Form input not validate")
    else:
        return render(request, "payment/payment.html", {"title": "Thanh toán"})

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

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

    vnp_RequestId = str(random.randint(10**11, 10**12 - 1))
    vnp_Command = 'querydr'
    vnp_TxnRef = request.POST['order_id']
    vnp_OrderInfo = 'Kiem tra giao dich'  # Không dấu, không ký tự đặc biệt
    vnp_TransactionDate = request.POST['trans_date']
    vnp_CreateDate = datetime.now().strftime('%Y%m%d%H%M%S')
    vnp_IpAddr = get_client_ip(request)
    vnp_CreateBy = 'user01'
    vnp_TransactionType = request.POST.get('TransactionType', '')  # Cần giá trị hợp lệ
    vnp_Amount = request.POST.get('amount', '')  # Cần giá trị thực tế
    vnp_TransactionNo = request.POST.get('transaction_no', '0')  # Cần lấy từ giao dịch gốc

    data = {
        "vnp_Amount": vnp_Amount,
        "vnp_Command": vnp_Command,
        "vnp_CreateBy": vnp_CreateBy,
        "vnp_CreateDate": vnp_CreateDate,
        "vnp_IpAddr": vnp_IpAddr,
        "vnp_OrderInfo": vnp_OrderInfo,
        "vnp_RequestId": vnp_RequestId,
        "vnp_TmnCode": vnp_TmnCode,
        "vnp_TransactionDate": vnp_TransactionDate,
        "vnp_TransactionNo": vnp_TransactionNo,
        "vnp_TransactionType": vnp_TransactionType,
        "vnp_TxnRef": vnp_TxnRef,
        "vnp_Version": vnp_Version
    }

    # Sắp xếp và tạo chuỗi hash
    sorted_data = sorted((k, v) for k, v in data.items() if k != 'vnp_SecureHash')
    hash_data = "&".join(str(val) if val else '' for key, val in sorted_data)
    secure_hash = hmac.new(secret_key.encode('utf-8'), hash_data.encode('utf-8'), hashlib.sha512).hexdigest()
    print(f"Hash data: {hash_data}")
    print(f"Secure hash: {secure_hash}")

    data["vnp_SecureHash"] = secure_hash

    headers = {"Content-Type": "application/json"}
    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        response_json = json.loads(response.text)
        print(f"Response: {response_json}")
    else:
        response_json = {"error": f"Request failed назначать status code: {response.status_code}"}

    return render(request, "payment/query.html", {"title": "Kiểm tra kết quả giao dịch", "response_json": response_json})


def refund(request):
    if request.method == 'GET':
        return render(request, "payment/refund.html", {"title": "Hoàn tiền giao dịch"})

    url = settings.VNPAY_API_URL
    secret_key = settings.VNPAY_HASH_SECRET_KEY
    vnp_TmnCode = settings.VNPAY_TMN_CODE
    vnp_Version = '2.1.0'

    vnp_RequestId = str(random.randint(10**11, 10**12 - 1))
    vnp_Command = 'refund'
    vnp_TransactionType = request.POST.get('TransactionType', '02')  # 02: Hoàn tiền toàn phần
    vnp_TxnRef = request.POST['order_id']
    vnp_Amount = request.POST['amount']
    vnp_OrderInfo = request.POST['order_desc'].replace(' ', '+')  # Không dấu, thay khoảng trắng bằng +
    vnp_TransactionNo = request.POST.get('transaction_no', '0')  # Cần lấy từ giao dịch gốc
    vnp_TransactionDate = request.POST['trans_date']
    vnp_CreateDate = datetime.now().strftime('%Y%m%d%H%M%S')
    vnp_CreateBy = 'user01'
    vnp_IpAddr = get_client_ip(request)

    data = {
        "vnp_Amount": vnp_Amount,
        "vnp_Command": vnp_Command,
        "vnp_CreateBy": vnp_CreateBy,
        "vnp_CreateDate": vnp_CreateDate,
        "vnp_IpAddr": vnp_IpAddr,
        "vnp_OrderInfo": vnp_OrderInfo,
        "vnp_RequestId": vnp_RequestId,
        "vnp_TmnCode": vnp_TmnCode,
        "vnp_TransactionDate": vnp_TransactionDate,
        "vnp_TransactionNo": vnp_TransactionNo,
        "vnp_TransactionType": vnp_TransactionType,
        "vnp_TxnRef": vnp_TxnRef,
        "vnp_Version": vnp_Version
    }

    sorted_data = sorted((k, v) for k, v in data.items() if k != 'vnp_SecureHash')
    hash_data = "&".join(str(val) if val else '' for key, val in sorted_data)
    secure_hash = hmac.new(secret_key.encode('utf-8'), hash_data.encode('utf-8'), hashlib.sha512).hexdigest()
    print(f"Hash data: {hash_data}")
    print(f"Secure hash: {secure_hash}")

    data["vnp_SecureHash"] = secure_hash

    headers = {"Content-Type": "application/json"}
    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        response_json = json.loads(response.text)
        print(f"Response: {response_json}")
    else:
        response_json = {"error": f"Request failed with status code: {response.status_code}"}

    return render(request, "payment/refund.html", {"title": "Kết quả hoàn tiền giao dịch", "response_json": response_json})