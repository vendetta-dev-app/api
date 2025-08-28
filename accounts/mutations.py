from graphene import relay, Field, String
from graphql import GraphQLError
from django.db import transaction
from graphql_jwt.decorators import login_required

from accounts.constants import roles
from accounts.models import InvitationCode, User, AdminProfile, CollectorProfile
from accounts.nodes import UserNode


class BaseUserInput:
    email = String(required=True)
    full_name = String(required=True)
    phone_number_1 = String(required=True)
    phone_number_2 = String(required=False)


class CreateAdmin(relay.ClientIDMutation):
    user = Field(UserNode)

    class Input(BaseUserInput):
        invitation_code = String(required=True)
        password = String(required=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        email = input.get('email')
        invitation_code_value = input.get('invitation_code')

        if User.objects.filter(email=email).exists():
            raise GraphQLError('Ya existe un usuario con este correo')

        try:
            invitation = InvitationCode.objects.get(code=invitation_code_value, is_active=True)
        except InvitationCode.DoesNotExist:
            raise GraphQLError('Código de invitación inválido o inactivo')

        try:
            user = User.objects.create_admin(
                email=email,
                password=input.get('password'),
                full_name=input.get('full_name'),
                phone_number_1=input.get('phone_number_1'),
                phone_number_2=input.get('phone_number_2'),
            )
            invitation.mark_as_used(user)

        except Exception as e:
            raise GraphQLError(f'Error creando admin: {str(e)}')

        return CreateAdmin(user=user)


class CreateCollector(relay.ClientIDMutation):
    user = Field(UserNode)

    class Input(BaseUserInput):
        password = String(required=True)

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        admin = info.context.user

        if not admin.is_admin:
            raise GraphQLError('Solo los administradores pueden crear cobradores')

        if not hasattr(admin, 'admin_profile'):
            raise GraphQLError('Este administrador no tiene perfil asociado')

        email = input.get('email')

        if User.objects.filter(email=email).exists():
            raise GraphQLError('Ya existe un usuario con este correo')

        try:
            user = User.objects.create_collector(
                admin_profile=admin.admin_profile,
                email=email,
                password=input.get('password'),
                full_name=input.get('full_name'),
                phone_number_1=input.get('phone_number_1'),
                phone_number_2=input.get('phone_number_2'),
            )

        except Exception as e:
            raise GraphQLError(f'Error creando cobrador: {str(e)}')

        return CreateCollector(user=user)


class CreateClient(relay.ClientIDMutation):
    user = Field(UserNode)

    class Input(BaseUserInput):
        password = String(required=True)
        alias = String(required=False)
        identity_document = String(required=True)
        address_line_1 = String(required=True)
        address_line_2 = String(required=False)
        neighborhood = String(required=True)

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        collector = info.context.user

        if not collector.is_collector:
            raise GraphQLError('Solo los cobradores pueden crear clientes')

        if not hasattr(collector, 'collector_profile'):
            raise GraphQLError('Este cobrador no tiene perfil asociado')

        email = input.get('email')

        if User.objects.filter(email=email).exists():
            raise GraphQLError('Ya existe un usuario con este correo')

        try:
            user = User.objects.create_client(
                collector_profile=collector.collector_profile,
                email=email,
                password=input.get('password'),
                full_name=input.get('full_name'),
                phone_number_1=input.get('phone_number_1'),
                phone_number_2=input.get('phone_number_2'),
                alias=input.get('alias'),
                identity_document=input.get('identity_document'),
                address_line_1=input.get('address_line_1'),
                address_line_2=input.get('address_line_2'),
                neighborhood=input.get('neighborhood'),
            )

        except Exception as e:
            raise GraphQLError(f'Error creando cliente: {str(e)}')

        return CreateClient(user=user)