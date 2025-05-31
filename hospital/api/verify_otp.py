
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from hospital.models import User, OtpUsers
from rest_framework import status






class VerifyOTP(APIView):
    def post(self, request):
        user_id = request.data.get('user_id')
        otp = request.data.get('otp')
        try:
            user = User.objects.get(user_id=user_id)
            if (OtpUsers.otp_code == otp and
                 OtpUsers.otp_created_at and 
                 timezone.now() - OtpUsers.otp_created_at < timezone.timedelta(minutes=5)
                 ):
                user.status= True
                OtpUsers.is_phone_verified = True
                OtpUsers.otp_code = None
                OtpUsers.save()
                return Response({"message": "Xác thực thành công!"}, status=status.HTTP_200_OK)
            return Response({"message": "Mã OTP không hợp lệ hoặc đã hết hạn!"}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({"message": "Người dùng không tồn tại!"}, status=status.HTTP_404_NOT_FOUND)