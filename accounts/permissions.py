from rest_framework.permissions import BasePermission

class IsOwnerOrStaff(BasePermission):
    """
    - Requires authentication.
    - Staff can access any object.
    - For User objects: only the user themself or superuser can access.
    - For other models with a `user` FK: only the owner or staff can access.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.is_staff:
            return True

        # Case 1: object IS a User
        if hasattr(obj, 'pk') and obj.__class__.__name__.lower() == 'user':
            return obj.pk == user.pk

        # Case 2: object has a `user` field (e.g., Subscription, Profile, etc.)
        if hasattr(obj, 'user_id'):
            return obj.user_id == user.id

        # Default deny if no clear ownership link
        return False
