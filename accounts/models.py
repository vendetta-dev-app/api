import uuid
from django.utils import timezone

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models

from accounts.choices import USER_ROLES_CHOICES
from accounts.constants import roles
from accounts.managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(verbose_name="Email address", unique=True)
    full_name = models.CharField(max_length=100)
    phone_number_1 = models.CharField(max_length=10)
    phone_number_2 = models.CharField(max_length=10, blank=True, null=True)
    role = models.CharField(
        max_length=9,
        choices=USER_ROLES_CHOICES,
        default=roles.CLIENT,
    )

    date_joined = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    USERNAME_FIELD = "email"

    objects = UserManager()

    def __str__(self):
        return self.email

    @property
    def is_client(self):
        """
        Returns True if the user has an associated ClientProfile.
        """
        return hasattr(self, 'client_profile')

    @property
    def is_admin(self):
        """
        Returns True if the user has an associated AdminProfile.
        """
        return hasattr(self, 'admin_profile')

    @property
    def is_collector(self):
        """
        Returns True if the user has an associated CollectorProfile.
        """
        return hasattr(self, 'collector_profile')


class ProfileBase(models.Model):
    """
    Base class for all user profiles in the application
    """
    user = models.OneToOneField(
        get_user_model(),
        on_delete=models.PROTECT
    )

    class Meta:
        abstract = True


class ClientProfile(ProfileBase):
    alias = models.CharField(max_length=100, blank=True, null=True)
    identity_document = models.CharField(max_length=30, unique=True)
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True, null=True)
    neighborhood = models.CharField(max_length=100)

    collector = models.ForeignKey(
        'CollectorProfile',
        on_delete=models.PROTECT,
        related_name='clients'
    )

    is_active = models.BooleanField(default=False)

    class Meta:
        default_related_name = "client_profile"


class CollectorProfile(ProfileBase):
    admin = models.ForeignKey(
        'AdminProfile',
        on_delete=models.PROTECT,
        related_name='collectors'
    )
    is_active = models.BooleanField(default=False)

    class Meta:
        default_related_name = "collector_profile"


class ManagerProfile(ProfileBase):
    admin = models.ForeignKey(
        'AdminProfile',
        on_delete=models.PROTECT,
        related_name='managers'
    )

    is_active = models.BooleanField(default=False)

    class Meta:
        default_related_name = "manager_profile"

    def __str__(self):
        return f"{self.user.full_name} - {self.id}"


class AdminProfile(ProfileBase):
    class Meta:
        default_related_name = "admin_profile"

    def __str__(self):
        return f"{self.user.full_name} - {self.id}"


class InvitationCode(models.Model):
    code = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    is_active = models.BooleanField(default=True)
    used_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='used_invitation_code'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)

    def mark_as_used(self, user):
        self.used_by = user
        self.used_at = timezone.now()
        self.is_active = False
        self.save()

    def __str__(self):
        return f"{self.code} ({'Used' if not self.is_active else 'Active'})"
