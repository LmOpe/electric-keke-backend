from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from .models import Profile
from .serializers import ProfileSerializer

# Create your views here.
class ValidateDriverLicense(APIView):
    """Driver License Validation"""
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        data = {'detail': 'message_type value is required'}
        # return Response(serializer.data, status=status.HTTP_201_CREATED)
        if request.data.get("user_id") is None:
            return Response({'detail': 'user_id value is required'},\
                            status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        if request.data.get("avatar") is None or len(request.data.get("avatar")) < 1:
            return Response({'detail': 'Avatar value is required'},\
                            status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        if request.data.get("driver_license") is None or len(request.data.get("driver_license")) < 1:
            return Response({'detail': 'driver license value is required'},\
                            status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        serializer = ProfileSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
