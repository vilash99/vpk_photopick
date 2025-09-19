from rest_framework import viewsets, status, generics, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.authentication import JWTAuthentication

from .serializers import (
    UserListSerializer,
    UserDetailSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
)
from .permissions import IsAuthenticatedAndSelfOrSuperuser

User = get_user_model()


class RegistrationView(generics.CreateAPIView):
    """
    Public signup endpoint
    POST /api/auth/register/
    """
    serializer_class = UserCreateSerializer
    permission_classes = [AllowAny]
    queryset = User.objects.all()
    authentication_classes = []


class UserViewSet(viewsets.ModelViewSet):
    """
    - Superusers can see all users.
    - Regular users can only see themselves.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticatedAndSelfOrSuperuser]

    queryset = User.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['email', 'name', 'phone']
    ordering = ['name']
    filterset_fields = ['name', 'is_active']

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return User.objects.exclude(id=user.id)
        return User.objects.filter(id=user.id)

    def get_serializer_class(self):
        if self.action == 'list':
            return UserListSerializer
        elif self.action == 'retrieve':
            return UserDetailSerializer
        elif self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserDetailSerializer

    def create(self, request, *args, **kwargs):
        # only superusers can create via this endpoint
        if not request.user.is_superuser:
            return Response({'detail': 'Only superusers can create users here. Use /api/auth/register/ for signup.'},
                            status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    def perform_update(self, serializer):
        """
        Enforce object-level permission: only self or superuser.
        (DRF already calls check_object_permissions(self.request, obj) via get_object())
        """

        instance = self.get_object()
        self.check_object_permissions(self.request, instance)
        serializer.save()

    @action(detail=False, methods=['get', 'patch'], url_path='me')
    def me(self, request, *args, **kwargs):
        """
        GET  /api/accounts/me/    -> current user's details
        PATCH /api/accounts/me/   -> update current user's details
        """
        user = request.user
        if request.method.lower() == 'get':
            serializer = UserDetailSerializer(user)
            return Response(serializer.data)

        # PATCH
        serializer = UserUpdateSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

