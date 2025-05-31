
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from rest_framework import status

from hospital.models import User, OtpUsers
from hospital.api.gen_otp import gen_otp
from hospital.sms_otp import send_otp_email






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
                str(OtpUsers.otp_code) == str(otp)
                and OtpUsers.otp_created_at
                and timezone.now() - user.otp_created_at < timezone.timedelta(minutes=5)
            ):
                user.set_password(new_password)
                OtpUsers.otp_code = None
                OtpUsers.otp_created_at = None
                user.save()
                return Response({"message": "Đặt lại mật khẩu thành công!"}, status=status.HTTP_200_OK)
            return Response({"message": "OTP không hợp lệ hoặc đã hết hạn!"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"message": f"Lỗi: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
