import base64
from unittest.mock import MagicMock

from django.test import TestCase
from graphene import ResolveInfo
from graphql import GraphQLError

from accounts.models import CollectorProfile, AdminProfile, ManagerProfile, User
from cities_light.models import City, Country
from routes.models import Route
from routes.mutations import CreateRoute, EditRoute


def make_user(email, role='COLLECTOR'):
    return User.objects.create_user(
        email=email,
        password='pass123',
        full_name='Test User',
        phone_number_1='123456789',
        role=role,
    )


def make_admin():
    user = make_user('admin_routes@test.com', role='ADMIN')
    return AdminProfile.objects.create(user=user)


def make_collector(admin, suffix=''):
    user = make_user(f'collector_r{suffix}@test.com')
    return CollectorProfile.objects.create(user=user, admin=admin)


def make_manager(admin):
    user = make_user('manager_routes@test.com', role='MANAGER')
    return ManagerProfile.objects.create(user=user, admin=admin)


def make_route(city, name='Test Route'):
    return Route.objects.create(name=name, city=city)


def gid(type_name, pk):
    """Generate a Relay global ID (base64 TypeName:pk)."""
    return base64.b64encode(f"{type_name}:{pk}".encode()).decode()


def mock_admin_info(admin_user):
    info = MagicMock(spec=ResolveInfo)
    info.context.user = admin_user
    return info


class CreateRouteCollectorValidationTest(TestCase):
    def setUp(self):
        country, _ = Country.objects.get_or_create(name='Test Country', defaults={'continent': 'SA'})
        self.city, _ = City.objects.get_or_create(name='Test City', defaults={'country': country})
        self.admin = make_admin()
        self.manager = make_manager(self.admin)
        self.collector_busy = make_collector(self.admin, suffix='_busy')
        self.collector_free = make_collector(self.admin, suffix='_free')
        existing_route = make_route(self.city, name='Existing Route')
        existing_route.administrators.set([self.admin])
        self.collector_busy.route = existing_route
        self.collector_busy.save()
        self.info = mock_admin_info(self.admin.user)

    def test_raises_error_when_collector_already_has_route(self):
        with self.assertRaises(GraphQLError) as ctx:
            CreateRoute.mutate_and_get_payload(
                None,
                self.info,
                name='New Route',
                city_id=gid('CityNode', self.city.id),
                collector_id=gid('CollectorNode', self.collector_busy.id),
                manager_id=gid('ManagerNode', self.manager.id),
                initial_value=1000,
            )
        self.assertEqual(str(ctx.exception), 'El cobrador ya tiene una ruta asignada')

    def test_existing_route_collector_not_nullified_on_failed_create(self):
        original_route_id = self.collector_busy.route.id
        try:
            CreateRoute.mutate_and_get_payload(
                None,
                self.info,
                name='New Route',
                city_id=gid('CityNode', self.city.id),
                collector_id=gid('CollectorNode', self.collector_busy.id),
                manager_id=gid('ManagerNode', self.manager.id),
                initial_value=1000,
            )
        except GraphQLError:
            pass
        self.collector_busy.refresh_from_db()
        self.assertIsNotNone(self.collector_busy.route)
        self.assertEqual(self.collector_busy.route.id, original_route_id)

    def test_succeeds_when_collector_has_no_route(self):
        result = CreateRoute.mutate_and_get_payload(
            None,
            self.info,
            name='New Route',
            city_id=gid('CityNode', self.city.id),
            collector_id=gid('CollectorNode', self.collector_free.id),
            manager_id=gid('ManagerNode', self.manager.id),
            initial_value=1000,
        )
        self.assertIsNotNone(result.route)
        self.collector_free.refresh_from_db()
        self.assertEqual(self.collector_free.route, result.route)
