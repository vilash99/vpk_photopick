from django.contrib.auth import get_user_model
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsOwnerOrStaff
from .models import Subscription
from .serializers import SubscriptionSerializer


User = get_user_model()


class SubscriptionViewSet(viewsets.ModelViewSet):
    """
    Endpoints:
    - GET /api/subscriptions/            (staff only: list all)
    - GET /api/subscriptions/{id}/       (owner or staff)
    - PATCH /api/subscriptions/{id}/     (owner or staff; validates plan/stripe rules)
    - GET /api/subscriptions/me/         (convenience: current user's subscription)
    - PATCH /api/subscriptions/me/       (update current user's subscription)
    """
    queryset = Subscription.objects.select_related("user").all()
    serializer_class = SubscriptionSerializer
    permission_classes = [IsOwnerOrStaff]
    http_method_names = ["get", "patch", "head", "options", "trace"]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return self.queryset
        return self.queryset.filter(user=user)

    def create(self, request, *args, **kwargs):
        # Subscriptions are auto-created for users. Disallow manual create via API.
        return Response({"detail": "Create not allowed."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=False, methods=["get", "patch"], url_path="me")
    def me(self, request):
        sub = Subscription.objects.select_related("user").get(user=request.user)
        if request.method.lower() == "get":
            return Response(self.get_serializer(sub).data)

        # PATCH current user's subscription
        serializer = self.get_serializer(sub, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
