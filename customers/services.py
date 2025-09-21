from django.db import transaction
from django.db.models import F
from django.core.exceptions import ValidationError

from .models import Photo, Event
from subscriptions.models import Subscription

def create_photo_atomic(*, event: Event, image, original_name=None) -> Photo:
    """
    Safe photo create that
    (1) locks the user's subscription,
    (2) enforces the limit, and
    (3) bumps the counter atomically.
    """
    owner_id = event.customer.owner_id

    with transaction.atomic():
        sub = Subscription.lock_for_user(owner_id)

        # Re-check with locked, current values
        if not sub.can_upload(1):
            raise ValidationError({'image': 'Upload limit reached for your plan.'})

        # Create the photo
        photo = Photo.objects.create(
            event=event,
            image=image,
            original_name=original_name,
        )

        # Atomic bump
        Subscription.atomic_bump(sub.pk, +1)

        # Optional: refresh a lightweight field if you show it in UI frequently
        # (not required if you rely only on photos_used_cached on Subscription)
        # event.photos_count = F('photos_count') + 1
        # event.save(update_fields=['photos_count'])

        # (optional) keep your per-event counters in sync quickly for UI
        # Event.objects.filter(pk=event.pk).update(photos_count=F('photos_count') + 1)

    return photo


def delete_photo_atomic(*, photo: Photo) -> None:
    """
    Safe delete that decrements the counter. Avoid queryset.bulk_delete.
    """
    owner_id = photo.event.customer.owner_id
    event_id = photo.event_id

    with transaction.atomic():
        sub = Subscription.lock_for_user(owner_id)

        # Delete first (so we only decrement if the row exists)
        deleted, _ = Photo.objects.filter(pk=photo.pk).delete()
        if deleted:
            Subscription.atomic_bump(sub.pk, -1)
            # Event.objects.filter(pk=event_id).update(photos_count=F('photos_count') - 1)
