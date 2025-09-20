# # customers/models.py
# import uuid
# from datetime import timedelta
# from django.conf import settings
# from django.core.exceptions import ValidationError
# from django.db import models
# from django.utils import timezone
# from django.utils.text import slugify
# from subscriptions.models import PLAN_UPLOAD_LIMITS, Plan
# from common.models import TimeStampedUUIDModel


# User = settings.AUTH_USER_MODEL


# def user_upload_limit(user) -> int:
#     sub = getattr(user, "subscription", None)
#     if not sub:
#         return PLAN_UPLOAD_LIMITS[Plan.FREE]
#     return sub.upload_limit()


# def user_total_uploads(user) -> int:
#     # Count ALL photos across ALL events for this user's customers
#     return Photo.objects.filter(event__customer__owner=user).count()


# class Customer(TimeStampedUUIDModel):
#     owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customers')
#     name = models.CharField(max_length=255)
#     phone = models.CharField(max_length=50, blank=True, null=True)

#     class Meta:
#         unique_together = [('owner', 'name')]  # optional; remove if you want dup names
#         indexes = [
#             models.Index(fields=['owner', 'name']),
#         ]

#     def __str__(self):
#         return f'{self.name} ({self.owner})'


# class Event(TimeStampedUUIDModel):
#     """
#     One event/function for a customer.
#     Upload limit is enforced PER EVENT using the owner's plan.
#     """
#     customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='events')
#     name = models.CharField(max_length=255)
#     slug = models.SlugField(max_length=280, blank=True)
#     date = models.DateField(blank=True, null=True)

#     # read-only counters (denormalized for quick UI)
#     photos_count = models.PositiveIntegerField(default=0)
#     selected_count = models.PositiveIntegerField(default=0)

#     class Meta:
#         unique_together = [('customer', 'name')]
#         indexes = [
#             models.Index(fields=['customer', 'name']),
#         ]
#         ordering = ['-created_at']

#     def save(self, *args, **kwargs):
#         if not self.slug:
#             base = slugify(self.name) or 'event'
#             self.slug = f'{base}-{uuid.uuid4().hex[:8]}'
#         super().save(*args, **kwargs)

#     def upload_limit(self) -> int:
#        return user_upload_limit(self.customer.owner)


# def event_photo_upload_to(instance, filename):
#     # Organized path: user/<user_id>/customer/<cust_id>/event/<event_id>/<filename>
#     owner_id = instance.event.customer.owner_id
#     return f'u/{owner_id}/c/{instance.event.customer_id}/e/{instance.event_id}/{filename}'


# class Photo(TimeStampedUUIDModel):
#     """
#     Single uploaded photo for an event.
#     """
#     event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='photos')
#     image = models.ImageField(upload_to=event_photo_upload_to)  # consider S3 via django-storages
#     original_name = models.CharField(max_length=255, blank=True, null=True)

#     # Client selection flag
#     is_selected = models.BooleanField(default=False)

#     uploaded_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         ordering = ['-uploaded_at']
#         indexes = [
#             models.Index(fields=['event', 'uploaded_at']),
#             models.Index(fields=['event', 'is_selected']),
#         ]

#     def clean(self):
#         if not self.pk:
#             owner = self.event.customer.owner
#             limit = user_upload_limit(owner)
#             used = user_total_uploads(owner)
#             if used >= limit:
#                 raise ValidationError(
#                     {"image": f"Upload limit reached for your plan (limit={limit}, used={used})."}
#                 )

#     def __str__(self):
#         return f'Photo {self.pk} for {self.event_id}'


# class ShareLink(TimeStampedUUIDModel):
#     """
#     Public link a photographer sends to the customer to view/select photos.
#     """
#     event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name='share_link')
#     token = models.CharField(max_length=64, unique=True, default=lambda: uuid.uuid4().hex)
#     can_select = models.BooleanField(default=True)
#     expiry = models.DateTimeField(blank=True, null=True)  # optional timebox

#     def is_active(self) -> bool:
#         if self.expiry and timezone.now() > self.expiry:
#             return False
#         return True

#     def refresh(self, hours=24):
#         self.token = uuid.uuid4().hex
#         self.expiry = timezone.now() + timedelta(hours=hours)
#         self.save(update_fields=['token', 'expiry'])
