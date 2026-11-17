from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .permissions import is_librarian_user

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    available_credits = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "name", "role", "available_credits", "is_active"]
        read_only_fields = ["id", "available_credits"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "name", "role", "password", "password_confirm"]
        extra_kwargs = {"email": {"required": True}}

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        if not (request and is_librarian_user(request.user)):
            validated_data["role"] = User.Role.MEMBER
        return User.objects.create_user(**validated_data)