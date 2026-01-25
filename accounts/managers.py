from django.contrib.auth.base_user import BaseUserManager
from django.db import models, transaction

from accounts.constants import roles


class UserQuerySet(models.QuerySet):
    def clients(self):
        return self.filter(role=roles.CLIENT)

    def admins(self):
        return self.filter(role=roles.ADMIN)

    def collectors(self):
        return self.filter(role=roles.COLLECTOR)

    def active(self):
        return self.filter(is_active=True)

    def staff(self):
        return self.filter(is_staff=True)


class UserManager(BaseUserManager):
    use_in_migrations = True

    def get_queryset(self):
        return UserQuerySet(self.model, using=self._db)

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)

    # Consultas directas
    def clients(self):
        return self.get_queryset().clients()

    def admins(self):
        return self.get_queryset().admins()

    def collectors(self):
        return self.get_queryset().collectors()

    # Creación de usuarios por rol con perfiles asociados
    def create_admin(self, email, password=None, **extra_fields):
        from accounts.models import AdminProfile

        with transaction.atomic():
            user = self.create_user(
                email=email,
                password=password,
                role=roles.ADMIN,
                **extra_fields
            )
            AdminProfile.objects.create(user=user)
        return user

    def create_manager(self, admin_profile, email, password=None, **extra_fields):
        from accounts.models import ManagerProfile

        if not admin_profile:
            raise ValueError("Debe proporcionar un perfil de administrador")

        with transaction.atomic():
            user = self.create_user(
                email=email,
                password=password,
                role=roles.MANAGER,
                **extra_fields
            )
            ManagerProfile.objects.create(user=user, admin=admin_profile)

        return user

    def create_collector(self, admin_profile, email, password=None, **extra_fields):
        from accounts.models import CollectorProfile

        if not admin_profile:
            raise ValueError("Debe proporcionar un perfil de administrador")

        with transaction.atomic():
            user = self.create_user(
                email=email,
                password=password,
                role=roles.COLLECTOR,
                **extra_fields
            )
            CollectorProfile.objects.create(user=user, admin=admin_profile)
        return user

    def create_client(self, collector_profile, email, password=None, **extra_fields):
        from accounts.models import ClientProfile

        if not collector_profile:
            raise ValueError("Debe proporcionar un perfil de cobrador")

        user_fields = {
            "full_name": extra_fields.pop("full_name", None),
            "phone_number_1": extra_fields.pop("phone_number_1", None),
            "phone_number_2": extra_fields.pop("phone_number_2", None),
        }

        client_fields = {
            "alias": extra_fields.pop("alias", None),
            "identity_document": extra_fields.pop("identity_document", None),
            "address_line_1": extra_fields.pop("address_line_1", None),
            "address_line_2": extra_fields.pop("address_line_2", None),
            "neighborhood": extra_fields.pop("neighborhood", None),
        }

        with transaction.atomic():
            user = self.create_user(
                email=email,
                password=password,
                role=roles.CLIENT,
                **user_fields
            )

            ClientProfile.objects.create(
                user=user,
                collector=collector_profile,
                **client_fields
            )

        return user
