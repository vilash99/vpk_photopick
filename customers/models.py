import uuid
from datetime import timedelta
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from subscriptions.models import PLAN_UPLOAD_LIMITS, Plan
from common.models import TimeStampedUUIDModel


User = settings.AUTH_USER_MODEL


class Customer(TimeStampedUUIDModel):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customers')
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        unique_together = [('owner', 'name')] # No duplicate customer name for current owner
        indexes = [
            models.Index(fields=['owner', 'name']),
        ]

    def __str__(self):
        return f'{self.name} ({self.owner})'


class Event(TimeStampedUUIDModel):
    """
    One event/function for a customer.
    UI counters are denormalized for snappy lists; authoritative enforcement
    of per-user upload limits happens in customers.services.create_photo_atomic().
    """
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='events')
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, blank=True)
    date = models.DateField(blank=True, null=True)

    # read-only counters (denormalized for quick UI)
    photos_count = models.PositiveIntegerField(default=0)
    selected_count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [('customer', 'name')]
        indexes = [
            models.Index(fields=['customer', 'name']),
        ]
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or 'event'
            self.slug = f'{base}-{uuid.uuid4().hex[:8]}'
        super().save(*args, **kwargs)

    @property
    def upload_limit(self) -> int:
        """
        Returns the owner's plan limit. Used for display; hard enforcement happens
        inside the service layer with row locks.
        """
        sub = getattr(self.customer.owner, 'subscription', None)
        if not sub:
            return PLAN_UPLOAD_LIMITS[Plan.FREE]
        return sub.upload_limit


class Photo(TimeStampedUUIDModel):
    """
    Single uploaded photo for an event.
    Authoritative quota enforcement is done in customers.services.create_photo_atomic()
    (inside a transaction with select_for_update + F() increments).
    """
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='photos')

    # Store Wasabi object KEYS
    image_key = models.CharField(max_length=512)
    thumbnail_key = models.CharField(max_length=512, blank=True, null=True)

    original_name = models.CharField(max_length=255, blank=True, null=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    thumb_size_bytes = models.PositiveBigIntegerField(default=0)

    # Client selection flag
    is_selected = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event', 'created_at']),
            models.Index(fields=['event', 'is_selected']),
        ]

    # Helper to build a public URL if you keep bucket public; else serve signed URLs in a view/serializer.
    def public_url(self) -> str:
        base = getattr(settings, 'WASABI_PUBLIC_BASE', '').rstrip('/')  # e.g., https://s3.us-east-1.wasabisys.com/<bucket>
        return f'{base}/{self.image_key}' if base else self.image_key

    def thumb_public_url(self) -> str:
        base = getattr(settings, 'WASABI_PUBLIC_BASE', '').rstrip('/')
        return f'{base}/{self.thumbnail_key}' if (base and self.thumbnail_key) else (self.thumbnail_key or '')

    def __str__(self):
        return f'Photo {self.pk} for {self.event_id}'


def generate_token() -> str:
    # 32-char lowercase hex string
    return uuid.uuid4().hex

class ShareLink(TimeStampedUUIDModel):
    """
    Public link a photographer sends to the customer to view/select photos.
    """
    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name='share_link')
    token = models.CharField(max_length=32, unique=True, default=generate_token, db_index=True)
    can_select = models.BooleanField(default=True)
    expiry = models.DateTimeField(blank=True, null=True)

    def is_active(self) -> bool:
        if self.expiry and timezone.now() > self.expiry:
            return False
        return True

    def refresh(self, hours=24):
        self.token = uuid.uuid4().hex
        self.expiry = timezone.now() + timedelta(hours=hours)
        self.save(update_fields=['token', 'expiry'])
