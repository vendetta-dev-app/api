from graphene import relay, Field, String, Boolean
from graphql import GraphQLError
from graphql_jwt.decorators import login_required
from graphql_relay import from_global_id

from accounts.models import InvitationCode, User, CollectorProfile
from accounts.nodes import UserNode, CollectorNode, ManagerNode


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


class CreateManager(relay.ClientIDMutation):
    manager = Field(ManagerNode)

    class Input(BaseUserInput):
        password = String(required=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        admin = info.context.user

        if not admin.is_admin:
            raise GraphQLError('Solo los administradores pueden crear cobradores')

        email = input.get('email')

        if User.objects.filter(email=email).exists():
            raise GraphQLError('Ya existe un usuario con este correo')

        try:
            user = User.objects.create_manager(
                admin_profile=admin.admin_profile,
                email=email,
                password=input.get('password'),
                full_name=input.get('full_name'),
                phone_number_1=input.get('phone_number_1'),
                phone_number_2=input.get('phone_number_2'),
            )
        except Exception as e:
            raise GraphQLError(f'Error creando manager: {str(e)}')

        return CreateManager(manager=user.manager_profile)



class CreateCollector(relay.ClientIDMutation):
    collector = Field(CollectorNode)

    class Input(BaseUserInput):
        password = String(required=True)

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        admin = info.context.user

        if not admin.is_admin:
            raise GraphQLError('Solo los administradores pueden crear cobradores')

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

        return CreateCollector(collector=user.collector_profile)


class EditCollector(relay.ClientIDMutation):
    user = Field(UserNode)

    class Input(BaseUserInput):
        user_id = String(required=True)
        is_active = Boolean(required=True)

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user_id = input.pop("user_id")
        print(input)
        try:
            user_id = from_global_id(user_id)[1]
        except Exception as e:
            raise GraphQLError(f"Error editar cobrador: {str(e)}")

        try:
            user = User.objects.get(id=user_id)
        except CollectorProfile.DoesNotExist:
            raise GraphQLError("No existe un usuario con este id")

        if not user.is_collector:
            raise GraphQLError("No existe un perfil de cobrador para este usuario")

        for field, value in input.items():
            if field == 'is_active':
                setattr(user.collector_profile, field, value)
            if hasattr(user, field):
                setattr(user, field, value)

        user.save()
        user.collector_profile.save()

        return EditCollector(user=user)


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


class UpdateClient(relay.ClientIDMutation):
    user = Field(UserNode)

    class Input(BaseUserInput):
        id = String(required=True)
        alias = String(required=False)
        phone_number_1 = String(required=False)
        phone_number_2 = String(required=False)
        address_line_1 = String(required=False)
        address_line_2 = String(required=False)
        neighborhood = String(required=False)
        full_name = String(required=False)

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        collector = info.context.user

        if not collector.is_collector:
            raise GraphQLError("Solo los cobradores pueden actualizar clientes")

        if not hasattr(collector, "collector_profile"):
            raise GraphQLError("Este cobrador no tiene perfil asociado")

        # Decode Relay global ID to get the database ID
        try:
            client_id = from_global_id(input.get("id"))[1]
            client = User.objects.get(id=client_id, collector_profile=collector.collector_profile)
        except User.DoesNotExist:
            raise GraphQLError("Cliente no encontrado o no pertenece a este cobrador")

        # Update allowed fields
        updatable_fields = [
            "alias",
            "phone_number_1",
            "phone_number_2",
            "address_line_1",
            "address_line_2",
            "neighborhood",
            "full_name",
        ]

        for field in updatable_fields:
            value = input.get(field)
            if value is not None:
                setattr(client, field, value)

        try:
            client.save()
        except Exception as e:
            raise GraphQLError(f"Error actualizando cliente: {str(e)}")

        return UpdateClient(user=client.user)