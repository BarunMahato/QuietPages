from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    CurrentUserProfileAPIView,
    LogoutAPIView,
    RegisterAPIView,
    UserDetailAPIView,
    UserListCreateAPIView,
)

app_name = "users"

urlpatterns = [
    path("login/", TokenObtainPairView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("logout/", LogoutAPIView.as_view(), name="logout"),
    path("register/", RegisterAPIView.as_view(), name="register"),
    path("me/", CurrentUserProfileAPIView.as_view(), name="me"),
    path("", UserListCreateAPIView.as_view(), name="user-list-create"),
    path("<int:pk>/", UserDetailAPIView.as_view(), name="user-detail"),
]