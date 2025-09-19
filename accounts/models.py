from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.core.exceptions import ValidationError
from common.models import TimeStampedUUIDModel
from django.db.models import UniqueConstraint
from django.db.models.functions import Lower


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        if not password:
            raise ValueError('Superuser must have a password.')

        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

    # Make authentication case-insensitive by email
    def get_by_natural_key(self, email):
        return self.get(**{f'{self.model.USERNAME_FIELD}__iexact': email})


class User(AbstractBaseUser, PermissionsMixin, TimeStampedUUIDModel):
    # id, created_at, updated_at come from TimeStampedUUIDModel

    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True, db_index=True)
    phone = models.CharField(max_length=50, null=True, blank=True)

    studio_name = models.CharField(max_length=255, null=True, blank=True)
    website_link = models.URLField(null=True, blank=True)
    whatsapp_link = models.URLField(null=True, blank=True)
    instagram_link = models.URLField(null=True, blank=True)
    facebook_link = models.URLField(null=True, blank=True)
    youtube_link = models.URLField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    objects = UserManager()

    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'
        ordering = ['-created_at']

        constraints = [
            UniqueConstraint(Lower('email'), name='user_email_ci_unique')
        ]

    def clean(self):
        super().clean()
        if self.email:
            self.email = self.email.lower()

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower()

        # App-level guard against duplicate emails differing by case
        if self.email and User.objects.exclude(pk=self.pk).filter(email__iexact=self.email).exists():
            raise ValidationError({'email': 'A user with this email already exists.'})
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name or self.email
