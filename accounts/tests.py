from django.test import TestCase
from accounts.filtersets import CollectorProfileFilterset
from accounts.models import CollectorProfile, AdminProfile, User
from routes.models import Route
from cities_light.models import City, Country


def make_user(email, role='COLLECTOR'):
    return User.objects.create_user(
        email=email,
        password='pass123',
        full_name='Test User',
        phone_number_1='123456789',
        role=role,
    )


def make_admin():
    user = make_user('admin_filter@test.com', role='ADMIN')
    return AdminProfile.objects.create(user=user)


def make_collector(admin, suffix=''):
    user = make_user(f'collector{suffix}@test.com')
    return CollectorProfile.objects.create(user=user, admin=admin)


def make_route(city):
    return Route.objects.create(name='Test Route', city=city)


class CollectorRouteIsnullFilterTest(TestCase):
    def setUp(self):
        country, _ = Country.objects.get_or_create(name='Test Country', defaults={'continent': 'SA'})
        self.city, _ = City.objects.get_or_create(name='Test City', defaults={'country': country})
        self.admin = make_admin()
        self.collector_with_route = make_collector(self.admin, suffix='_with')
        self.collector_without_route = make_collector(self.admin, suffix='_without')
        route = make_route(self.city)
        self.collector_with_route.route = route
        self.collector_with_route.save()

    def test_route_isnull_true_excludes_collectors_with_route(self):
        qs = CollectorProfile.objects.filter(admin=self.admin)
        fs = CollectorProfileFilterset(data={'route_isnull': True}, queryset=qs)
        result = list(fs.qs)
        self.assertIn(self.collector_without_route, result)
        self.assertNotIn(self.collector_with_route, result)

    def test_route_isnull_false_excludes_collectors_without_route(self):
        qs = CollectorProfile.objects.filter(admin=self.admin)
        fs = CollectorProfileFilterset(data={'route_isnull': False}, queryset=qs)
        result = list(fs.qs)
        self.assertIn(self.collector_with_route, result)
        self.assertNotIn(self.collector_without_route, result)
