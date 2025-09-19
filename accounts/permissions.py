from rest_framework.permissions import BasePermission


class IsAuthenticatedAndSelfOrSuperuser(BasePermission):
    """
    - Read:
        * Superusers can read anyone (handled by queryset).
        * Non-superusers can only read themselves (handled by queryset).
    - Write (PUT/PATCH/DELETE):
        * Superusers can modify anyone.
        * A user can modify only their own object.
    """

    def has_permission(self, request, view):
        # Require auth for all actions on this ViewSet
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        return getattr(obj, 'pk', None) == getattr(request.user, 'pk', None)
