import boto3
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.db.models import Count
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .serializers import PhotoRegisterSerializer, CustomerSerializer, EventSerializer, ShareLinkSerializer
from .models import Customer, Event, ShareLink
from accounts.permissions import IsOwnerOrStaff


MAX_BYTES = 20 * 1024 * 1024

def wasabi_client():
    return boto3.client(
        's3',
        region_name=getattr(settings, 'WASABI_REGION', 'us-east-1'),
        endpoint_url=getattr(settings, 'WASABI_ENDPOINT', 'https://s3.us-east-1.wasabisys.com'),
        aws_access_key_id=settings.WASABI_ACCESS_KEY,
        aws_secret_access_key=settings.WASABI_SECRET_KEY,
    )


class OwnerScopedMixin:
    """
    Scopes queryset to the authenticated owner unless user.is_staff.
    Set owner_path to the FK path reaching the User owner.
    """
    owner_path = None  # e.g., 'owner', 'customer__owner', 'event__customer__owner'

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_staff:
            return qs
        assert self.owner_path, "owner_path must be set on the viewset"
        return qs.filter(**{self.owner_path: user})


class CustomerViewSet(OwnerScopedMixin, viewsets.ModelViewSet):
    """
    /api/customers/
    /api/customers/{id}/
    """
    queryset = Customer.objects.all().annotate(event_count=Count('events'))
    serializer_class = CustomerSerializer
    permission_classes = [IsOwnerOrStaff]
    owner_path = 'owner'
    http_method_names = ['get', 'post', 'patch', 'put', 'delete', 'head', 'options']

    # Optional niceties if you enabled DRF filters in settings:
    search_fields = ['name', 'phone']
    ordering_fields = ['created_at', 'name']
    filterset_fields = []


class EventViewSet(OwnerScopedMixin, viewsets.ModelViewSet):
    """
    /api/events/
    /api/events/{id}/
    """
    queryset = Event.objects.select_related('customer', 'customer__owner')
    serializer_class = EventSerializer
    permission_classes = [IsOwnerOrStaff]
    owner_path = 'customer__owner'
    http_method_names = ['get', 'post', 'patch', 'put', 'delete', 'head', 'options']

    search_fields = ['name']
    ordering_fields = ['created_at', 'date', 'name']
    filterset_fields = ['customer']


class PhotoRegisterView(APIView):
    permission_classes = [IsOwnerOrStaff]

    def post(self, request):
        ser = PhotoRegisterSerializer(data=request.data, context={'request': request})
        ser.is_valid(raise_exception=True)

        data = ser.validated_data
        s3 = wasabi_client()

        # Optional server-side validation of sizes
        try:
            head = s3.head_object(Bucket=settings.WASABI_BUCKET_NAME, Key=data['image_key'])
            size = head['ContentLength']
            if size > MAX_BYTES:
                # Clean up object if you want
                s3.delete_object(Bucket=settings.WASABI_BUCKET_NAME, Key=data['image_key'])
                return Response({"detail": "Original image exceeds 20 MB after compression."}, status=400)
        except Exception as e:
            return Response({"detail": f"Image object not found or not accessible: {e}"}, status=400)

        thumb_size = 0
        if data.get('thumbnail_key'):
            try:
                h2 = s3.head_object(Bucket=settings.WASABI_BUCKET_NAME, Key=data['thumbnail_key'])
                thumb_size = h2['ContentLength']
            except Exception:
                # If thumb missing, you can proceed or treat as error; here we proceed.
                thumb_size = 0

        # Save
        photo = ser.save(size_bytes=size, thumb_size_bytes=thumb_size)

        return Response({
            "id": str(photo.id),
            "image_key": photo.image_key,
            "thumbnail_key": photo.thumbnail_key,
            "size_bytes": photo.size_bytes,
            "thumb_size_bytes": photo.thumb_size_bytes,
        }, status=status.HTTP_201_CREATED)


class ShareLinkViewSet(OwnerScopedMixin, viewsets.ModelViewSet):
    """
    /api/share-links/
    /api/share-links/{id}/
    Extra:
      POST /api/share-links/{id}/refresh/   -> rotate token & extend expiry
    """
    queryset = ShareLink.objects.select_related('event', 'event__customer', 'event__customer__owner')
    serializer_class = ShareLinkSerializer
    permission_classes = [IsOwnerOrStaff]
    owner_path = 'event__customer__owner'
    http_method_names = ['get', 'post', 'patch', 'put', 'delete', 'head', 'options']

    ordering_fields = ['created_at', 'expiry']
    filterset_fields = ['event']

    @action(detail=True, methods=['post'])
    def refresh(self, request, pk=None):
        sl = self.get_object()
        hours = int(request.data.get('hours', 24))
        sl.refresh(hours=hours)
        return Response(self.get_serializer(sl).data, status=status.HTTP_200_OK)