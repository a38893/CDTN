

from rest_framework.response import Response

from rest_framework import status

from hospital.models import MedicalRecord
from hospital.serializers import AppointmentHistoryViewSerializer
from rest_framework import  viewsets, permissions




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
