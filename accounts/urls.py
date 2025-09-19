from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet

from django.http import JsonResponse

router = DefaultRouter()

urlpatterns = [
    # /users/, /users/{id}/, /users/me/
    # path("", include(router.urls)),
]
