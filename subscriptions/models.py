from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.functional import cached_property
from django.core.exceptions import ValidationError
from django.conf import settings

from common.models import TimeStampedUUIDModel
# from photos.models import Photo


User = settings.AUTH_USER_MODEL

class Plan(models.TextChoices):
    FREE = 'FREE', 'Free'
    BASIC = 'BASIC', 'Basic'
    PRO = 'PRO', 'Pro'


PLAN_UPLOAD_LIMITS = {
    Plan.FREE: 100,
    Plan.BASIC: 1000,
    Plan.PRO: 3000,
}

class SubscriptionStatus(models.TextChoices):
    ACTIVE = 'active', 'Active'
    PAST_DUE = 'past_due', 'Past due'
    CANCELED = 'canceled', 'Canceled'
    INCOMPLETE = 'incomplete', 'Incomplete'


class Subscription(TimeStampedUUIDModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')

    # Stripe fields are OPTIONAL for free plans
    stripe_customer_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    stripe_subscription_id = models.CharField(max_length=100, unique=True, null=True, blank=True)

    plan = models.CharField(max_length=20, choices=Plan.choices, default=Plan.FREE)
    status = models.CharField(max_length=20, choices=SubscriptionStatus.choices, default=SubscriptionStatus.ACTIVE)

    current_period_end = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['current_period_end']),
            models.Index(fields=['plan']),
        ]

        constraints = [
            # If plan is PAID (BASIC/PRO) then stripe IDs must be present
            models.CheckConstraint(
                name='paid_plans_require_stripe_ids',
                check=(
                    Q(plan=Plan.FREE) |
                    (Q(stripe_customer_id__isnull=False) & ~Q(stripe_customer_id='')) &
                    (Q(stripe_subscription_id__isnull=False) & ~Q(stripe_subscription_id=''))
                ),
            ),
            # If plan is FREE, Stripe IDs must be NULL to avoid accidental linkage
            models.CheckConstraint(
                name='free_plan_must_not_have_stripe_ids',
                check=(
                    Q(plan__in=[Plan.BASIC, Plan.PRO]) |
                    (Q(stripe_customer_id__isnull=True) & Q(stripe_subscription_id__isnull=True))
                ),
            ),
        ]

    @property
    def is_free(self) -> bool:
        return self.plan == Plan.FREE

    @property
    def is_paid(self) -> bool:
        return self.plan in {Plan.BASIC, Plan.PRO}

    @property
    def upload_limit(self) -> int:
        return PLAN_UPLOAD_LIMITS[self.plan]

    @property
    def is_current(self) -> bool:
        """
        Is the subscription currently valid time-wise?
        For free plans (no period), treat as current if ACTIVE.
        """
        if self.is_free:
            return self.status == SubscriptionStatus.ACTIVE
        if not self.current_period_end:
            return False
        return self.current_period_end >= timezone.now()

    @cached_property
    def photos_used(self) -> int:
        """
        Total photos uploaded by this subscription's user.
        Assumes a Photo model with FK to User: Photo(user=..., ...)
        """
        # return Photo.objects.filter(user=self.user).count()
        return 0

    @property
    def photos_remaining(self) -> int:
        # return max(self.upload_limit - self.photos_used, 0)
        return self.upload_limit

    def clean(self):
        # App-level validation mirroring DB constraints, gives nicer messages
        if self.plan in {Plan.BASIC, Plan.PRO}:
            if not self.stripe_customer_id or not self.stripe_subscription_id:
                raise ValidationError('Paid plans require Stripe customer & subscription IDs.')
        else:
            if self.stripe_customer_id or self.stripe_subscription_id:
                raise ValidationError('Free plan must not have Stripe IDs.')

    def __str__(self):
        return f'{self.user} · {self.plan} · {self.status}'


class ReferralCredit(TimeStampedUUIDModel):
    referrer_org = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='referral_credits_earned'
    )
    referee_org = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='referral_credit_received'
    )
    days_awarded = models.PositiveIntegerField(default=15)
    awarded_at = models.DateTimeField(auto_now_add=True)
    reason = models.CharField(max_length=255, blank=True, default='referral_first_payment')

    class Meta:
        indexes = [
            models.Index(fields=['referrer_org']),
            models.Index(fields=['awarded_at']),
        ]
