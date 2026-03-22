from graphene import relay, Field, String, Boolean
import graphene
from graphql import GraphQLError
from graphql_jwt.decorators import login_required
from graphql_relay import from_global_id

from accounts.models import InvitationCode, User, CollectorProfile
from routes.models import Route
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
    @login_required
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


class UpdateManager(relay.ClientIDMutation):
    manager = Field(ManagerNode)

    class Input:
        user_id = String(required=True)
        email = String(required=False)
        full_name = String(required=False)
        phone_number_1 = String(required=False)
        phone_number_2 = String(required=False)
        is_active = Boolean(required=False)

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        admin = info.context.user

        if not admin.is_admin:
            raise GraphQLError('Solo los administradores pueden editar managers')

        user_id = input.pop("user_id")

        try:
            user_id = from_global_id(user_id)[1]
        except Exception as e:
            raise GraphQLError(f"Error editar manager: {str(e)}")

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise GraphQLError("No existe un usuario con este id")

        if not user.is_manager:
            raise GraphQLError("No existe un perfil de manager para este usuario")

        # Verify the manager belongs to this admin
        if user.manager_profile.admin != admin.admin_profile:
            raise GraphQLError("No tienes permiso para editar este manager")

        for field, value in input.items():
            if field == 'is_active':
                setattr(user.manager_profile, field, value)
            elif hasattr(user, field):
                setattr(user, field, value)

        user.save()
        user.manager_profile.save()

        return UpdateManager(manager=user.manager_profile)



class CreateCollector(relay.ClientIDMutation):
    collector = Field(CollectorNode)

    class Input(BaseUserInput):
        password = String(required=True)

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        admin = info.context.user
        print("User: ", admin.admin_profile)

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


class UpdateCollector(relay.ClientIDMutation):
    user = Field(UserNode)

    class Input(BaseUserInput):
        user_id = String(required=True)
        is_active = Boolean(required=True)

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user_id = input.pop("user_id")

        try:
            user_id = from_global_id(user_id)[1]
        except Exception as e:
            raise GraphQLError(f"Error editar cobrador: {str(e)}")

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise GraphQLError("No existe un usuario con este id")

        if not user.is_collector:
            raise GraphQLError("No existe un perfil de cobrador para este usuario")

        for field, value in input.items():
            if field == 'is_active':
                setattr(user.collector_profile, field, value)
            elif hasattr(user, field):
                setattr(user, field, value)

        user.save()
        user.collector_profile.save()

        return UpdateCollector(user=user)


class CreateClient(relay.ClientIDMutation):
    user = Field(UserNode)

    class Input:
        # Optional route_id (admin must provide, collector uses own route)
        route_id = String(required=False)
        # Optional email/password (clients don't need login)
        email = String(required=False)
        password = String(required=False)
        # Required fields
        full_name = String(required=True)
        phone_number_1 = String(required=True)
        phone_number_2 = String(required=False)
        alias = String(required=False)
        identity_document = String(required=True)
        address_line_1 = String(required=True)
        address_line_2 = String(required=False)
        neighborhood = String(required=True, verbose_name="Comuna/Barrio")
        # New location fields
        city = String(required=False, verbose_name="Ciudad")
        address_reference = String(required=False, verbose_name="Referencia")
        latitude = graphene.Float(required=False)
        longitude = graphene.Float(required=False)

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user

        if not (user.is_collector or user.is_admin):
            raise GraphQLError('No tienes permiso para ejecutar esta accion')

        route = None
        route_id_input = input.get("route_id")

        # Admin: debe proporcionar route_id
        if user.is_admin:
            if not route_id_input:
                raise GraphQLError('El admin debe proporcionar una ruta')
            try:
                route_id = from_global_id(route_id_input)[1]
            except Exception:
                raise GraphQLError("Error al obtener el route id")
            try:
                route = Route.objects.get(id=route_id)
            except Route.DoesNotExist:
                raise GraphQLError("No existe una ruta con el id dado")

        # Collector: usa su ruta si no se proporciona route_id
        elif user.is_collector:
            if route_id_input:
                # Si envía route_id, validar que le pertenezca
                try:
                    route_id = from_global_id(route_id_input)[1]
                except Exception:
                    raise GraphQLError("Error al obtener el route id")
                try:
                    route = Route.objects.get(id=route_id)
                    if route.collector_profile != user.collector_profile:
                        raise GraphQLError("No existe una ruta con ese id o no te pertenece")
                except Route.DoesNotExist:
                    raise GraphQLError("No existe una ruta con ese id o no te pertenece")
            else:
                # Usar la ruta del collector (OneToOne)
                if not user.collector_profile.route:
                    raise GraphQLError('No tienes una ruta asignada. Contacta al administrador.')
                route = user.collector_profile.route

        # Check if identity_document already exists
        identity_document = input.get('identity_document')
        if User.objects.filter(client_profile__identity_document=identity_document).exists():
            raise GraphQLError('Ya existe un cliente con este RUT')

        # Check email uniqueness only if provided (and not auto-generated)
        email = input.get('email')
        if email and not email.endswith('@no-login.local'):
            if User.objects.filter(email=email).exists():
                raise GraphQLError('Ya existe un usuario con este correo')

        try:
            user_obj = User.objects.create_client(
                route=route,
                email=email,
                password=input.get('password'),
                full_name=input.get('full_name'),
                phone_number_1=input.get('phone_number_1'),
                phone_number_2=input.get('phone_number_2'),
                alias=input.get('alias'),
                identity_document=identity_document,
                address_line_1=input.get('address_line_1'),
                address_line_2=input.get('address_line_2'),
                neighborhood=input.get('neighborhood'),
                city=input.get('city'),
                address_reference=input.get('address_reference'),
                latitude=input.get('latitude'),
                longitude=input.get('longitude'),
            )

        except Exception as e:
            raise GraphQLError(f'Error creando cliente: {str(e)}')

        return CreateClient(user=user_obj)


class UpdateClient(relay.ClientIDMutation):
    user = Field(UserNode)

    class Input:
        id = String(required=True)
        alias = String(required=False)
        phone_number_1 = String(required=False)
        phone_number_2 = String(required=False)
        address_line_1 = String(required=False)
        address_line_2 = String(required=False)
        neighborhood = String(required=False)
        full_name = String(required=False)
        # New location fields
        city = String(required=False)
        address_reference = String(required=False)
        latitude = graphene.Float(required=False)
        longitude = graphene.Float(required=False)

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
            client_user = User.objects.select_related('client_profile').get(
                id=client_id,
                client_profile__route__collector_profile=collector.collector_profile
            )
        except User.DoesNotExist:
            raise GraphQLError("Cliente no encontrado o no pertenece a este cobrador")

        # Fields that belong to User model
        user_fields = ["phone_number_1", "phone_number_2", "full_name"]

        # Fields that belong to ClientProfile model
        profile_fields = ["alias", "address_line_1", "address_line_2", "neighborhood",
                         "city", "address_reference"]

        # Special numeric fields
        numeric_fields = ["latitude", "longitude"]

        for field in user_fields:
            value = input.get(field)
            if value is not None:
                setattr(client_user, field, value)

        for field in profile_fields:
            value = input.get(field)
            if value is not None:
                setattr(client_user.client_profile, field, value)

        for field in numeric_fields:
            value = input.get(field)
            if value is not None:
                setattr(client_user.client_profile, field, value)

        try:
            client_user.save()
            client_user.client_profile.save()
        except Exception as e:
            raise GraphQLError(f"Error actualizando cliente: {str(e)}")

        return UpdateClient(user=client_user)