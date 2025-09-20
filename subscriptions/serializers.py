from django.utils import timezone
from rest_framework import serializers
from .models import Subscription, Plan, SubscriptionStatus


class SubscriptionSerializer(serializers.ModelSerializer):
    # Computed, read-only helpers
    is_free = serializers.ReadOnlyField()
    is_paid = serializers.ReadOnlyField()
    is_current = serializers.ReadOnlyField()
    upload_limit = serializers.IntegerField(read_only=True)

    class Meta:
        model = Subscription
        # user is read-only; we never let clients move a subscription to a different user
        fields = (
            'id', 'user', 'plan', 'status',
            'stripe_customer_id', 'stripe_subscription_id',
            'current_period_end',
            'is_free', 'is_paid', 'is_current', 'upload_limit',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')

    def validate(self, attrs):
        """
        Mirror model.clean() with friendlier messages and also catch transitions:
        - Paid plans require both stripe IDs.
        - FREE plan must not carry stripe IDs.
        """
        plan = attrs.get('plan', getattr(self.instance, 'plan', Plan.FREE))
        stripe_cust = attrs.get('stripe_customer_id', getattr(self.instance, 'stripe_customer_id', None))
        stripe_sub = attrs.get('stripe_subscription_id', getattr(self.instance, 'stripe_subscription_id', None))

        if plan in {Plan.BASIC, Plan.PRO}:
            if not stripe_cust or not stripe_sub:
                raise serializers.ValidationError(
                    'Paid plans (Basic/Pro) require Stripe customer & subscription IDs.'
                )
        else:
            # Force FREE plans to drop stripe IDs
            if stripe_cust or stripe_sub:
                raise serializers.ValidationError(
                    'Free plan must not include Stripe IDs.'
                )

        # Optional: ensure current_period_end is in the future for paid ACTIVE status
        status = attrs.get('status', getattr(self.instance, 'status', SubscriptionStatus.ACTIVE))
        cpe = attrs.get('current_period_end', getattr(self.instance, 'current_period_end', None))
        if plan in {Plan.BASIC, Plan.PRO} and status == SubscriptionStatus.ACTIVE:
            if not cpe or cpe < timezone.now():
                raise serializers.ValidationError(
                    'Active paid subscriptions must include a future current_period_end.'
                )

        return attrs
