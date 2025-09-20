from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

from accounts.views import UserViewSet, RegistrationView
from subscriptions.views import SubscriptionViewSet


# Show users
router = DefaultRouter()
router.register(r'accounts', UserViewSet, basename='accounts')
router.register(r'subscriptions', SubscriptionViewSet, basename='subscriptions')


def health(_request):
    return JsonResponse({'ok': True, 'service': 'VPK PhotoPick API'})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health),

    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='docs'),

    path('api/', include(router.urls)),

    # Public registration
    path('api/auth/register/', RegistrationView.as_view(), name='register'),

    # JWT
    path('api/auth/jwt/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/jwt/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/jwt/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
]
