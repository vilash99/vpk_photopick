from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import Customer, Event, Photo, ShareLink
from customers.models import Event


User = get_user_model()


class CustomerSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True)
    event_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Customer
        fields = (
            'id', 'owner', 'name', 'phone',
            'event_count', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'owner', 'event_count', 'created_at', 'updated_at')

    def create(self, validated_data):
        # enforce ownership from the authenticated user
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)


class EventSerializer(serializers.ModelSerializer):
    # Customer must belong to the current user (validated in view/validate)
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all())
    slug = serializers.CharField(read_only=True)
    photos_count = serializers.IntegerField(read_only=True)
    selected_count = serializers.IntegerField(read_only=True)
    upload_limit = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = (
            'id', 'customer', 'name', 'slug', 'date',
            'photos_count', 'selected_count', 'upload_limit',
            'created_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'slug', 'photos_count', 'selected_count',
            'upload_limit', 'created_at', 'updated_at'
        )

    def get_upload_limit(self, obj) -> int:
        # surfaces the @property from the model
        return obj.upload_limit

    def validate_customer(self, customer: Customer):
        user = self.context['request'].user
        if user.is_staff:
            return customer
        if customer.owner_id != user.id:
            raise serializers.ValidationError("You do not own this customer.")
        return customer


class PhotoRegisterSerializer(serializers.Serializer):
    event_id = serializers.UUIDField()
    image_key = serializers.CharField(max_length=512)
    thumbnail_key = serializers.CharField(max_length=512, required=False, allow_blank=True, allow_null=True)
    original_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    size_bytes = serializers.IntegerField(required=False)
    thumb_size_bytes = serializers.IntegerField(required=False)

    def validate(self, attrs):
        request = self.context['request']
        user = request.user
        try:
            event = Event.objects.select_related('customer__owner').get(pk=attrs['event_id'])
        except Event.DoesNotExist:
            raise serializers.ValidationError('Event not found.')

        if event.customer.owner_id != user.id and not user.is_staff:
            raise serializers.ValidationError('You do not own this event.')

        attrs['event'] = event
        return attrs

    def create(self, validated):
        photo = Photo.objects.create(
            event=validated['event'],
            image_key=validated['image_key'],
            thumbnail_key=validated.get('thumbnail_key') or None,
            original_name=validated.get('original_name') or '',
            size_bytes=validated.get('size_bytes') or 0,
            thumb_size_bytes=validated.get('thumb_size_bytes') or 0,
        )
        return photo


class ShareLinkSerializer(serializers.ModelSerializer):
    event = serializers.PrimaryKeyRelatedField(queryset=Event.objects.all())
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = ShareLink
        fields = (
            'id', 'event', 'token', 'can_select', 'expiry',
            'is_active', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'token', 'is_active', 'created_at', 'updated_at')

    def get_is_active(self, obj) -> bool:
        return obj.is_active()

    def validate_event(self, event: Event):
        user = self.context['request'].user
        if user.is_staff:
            return event
        if event.customer.owner_id != user.id:
            raise serializers.ValidationError("You do not own this event.")
        return event
