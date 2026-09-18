from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Profile, Team


class TeamStructureTests(TestCase):
    """The seeded draft board matches the structure the committee set, and
    the public pages and application form read from it."""

    def test_land_sub_teams_in_order(self):
        names = list(Team.objects.filter(division='land').values_list('name', flat=True))
        self.assertEqual(names, [
            'Data & Telemetry', 'Electrical', 'Chassis & Component',
            'Vehicle Dynamics', 'Aerodynamics', 'HFC',
        ])

    def test_uga_led_air_teams_are_listed_but_do_not_recruit_here(self):
        uga = Team.objects.filter(division='air', partner='UGA')
        self.assertEqual(
            set(uga.values_list('name', flat=True)),
            {'Aerodynamics', 'Structures', 'Avionics & Flight Operations'},
        )
        self.assertFalse(uga.filter(is_recruiting=True).exists())

        hfr = Team.objects.filter(division='air', partner='')
        self.assertEqual(
            set(hfr.values_list('name', flat=True)),
            {'Propulsion', 'Energy Management & HFC'},
        )
        self.assertTrue(all(t.is_recruiting for t in hfr))

    def test_operations_recruits_business_and_finance(self):
        recruiting = Team.objects.filter(division='operations', is_recruiting=True)
        self.assertEqual(
            set(recruiting.values_list('name', flat=True)),
            {'Business', 'Finance & Contracts'},
        )

    def test_division_pages_list_their_sub_teams(self):
        resp = self.client.get(reverse('division_air'))
        self.assertContains(resp, 'Avionics &amp; Flight Operations')
        self.assertContains(resp, 'UGA led')
        self.assertContains(resp, 'Energy Management &amp; HFC')

        resp = self.client.get(reverse('division_land'))
        self.assertContains(resp, 'Chassis &amp; Component')
        self.assertNotContains(resp, 'UGA led')

        resp = self.client.get(reverse('division_sea'))
        self.assertContains(resp, 'Hydrogen Systems')

    def test_apply_form_only_offers_recruiting_teams(self):
        user = User.objects.create_user('appl', 'appl@student.gla.ac.uk', 'pw-appl-123')
        Profile.objects.create(user=user, role=Profile.ROLE_APPLICANT)
        self.client.login(username='appl', password='pw-appl-123')

        resp = self.client.get(reverse('apply'))
        self.assertContains(resp, 'Energy Management &amp; HFC')
        self.assertNotContains(resp, 'Avionics')
        self.assertNotContains(resp, 'Creative Direction')
