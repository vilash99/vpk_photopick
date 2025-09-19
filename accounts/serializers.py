from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'name', 'email', 'phone', 'is_active', 'created_at')
        read_only_fields = ('id', 'created_at')


class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id', 'name', 'email', 'phone', 'studio_name',
            'website_link', 'whatsapp_link', 'instagram_link',
            'facebook_link', 'youtube_link', 'is_active',
            'is_staff','is_superuser', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'is_staff', 'is_superuser')


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, required=True)
    confirm_password = serializers.CharField(write_only=True, min_length=8, required=True)

    class Meta:
        model = User
        fields = ('id', 'name', 'email', 'phone', 'password', 'confirm_password')
        read_only_fields = ('id',)

    def validate_email(self, value):
        v = (value or '').lower()
        if User.objects.filter(email__iexact=v).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return v

    def validate(self, attrs):
        """Check password and confirm_password match"""
        if attrs.get('password') != attrs.get('confirm_password'):
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        return attrs

    def create(self, validated_data):
         # Delegate to manager so password hashing is handled once
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('name', 'phone', 'studio_name', 'website_link',
                  'whatsapp_link', 'instagram_link', 'facebook_link',
                  'youtube_link', 'is_active')
        extra_kwargs = {'is_active': {'required': False}}
