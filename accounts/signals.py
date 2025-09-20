from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from subscriptions.models import Subscription

User = get_user_model()

@receiver(post_save, sender=User)
def ensure_free_subscription(sender, instance, created, **kwargs):
    if created:
        Subscription.objects.get_or_create(user=instance)
