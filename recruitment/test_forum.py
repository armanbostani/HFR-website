import base64
import hashlib
import hmac
import tempfile
from urllib.parse import parse_qs, urlencode, urlsplit

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Profile, Team

SSO_SECRET = 'a-shared-secret-for-tests'
FORUM = 'https://forum.example.org'
TEMP_MEDIA = tempfile.mkdtemp()


def discourse_login_request(nonce='abc123', return_url=FORUM + '/session/sso_login'):
    """What Discourse sends when someone clicks Log In on the forum."""
    payload = base64.b64encode(
        urlencode({'nonce': nonce, 'return_sso_url': return_url}).encode()
    ).decode()
    sig = hmac.new(SSO_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return {'sso': payload, 'sig': sig}


def sso_fields(response):
    """Decode the signed payload the site sends back to the forum."""
    sso = parse_qs(urlsplit(response['Location']).query)['sso'][0]
    return parse_qs(base64.b64decode(sso).decode())


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class ForumTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user(
            'member', 'member@student.gla.ac.uk', 'pw-member-123',
            first_name='Mem', last_name='Ber',
        )
        Profile.objects.create(user=self.member, role=Profile.ROLE_MEMBER, display_name='memb')
        self.applicant = User.objects.create_user('appl', 'appl@student.gla.ac.uk', 'pw-appl-123')
        Profile.objects.create(user=self.applicant, role=Profile.ROLE_APPLICANT)

    def login_member(self):
        self.client.login(username='member', password='pw-member-123')

    # ── Entry point ──

    def test_nothing_about_the_forum_until_it_is_configured(self):
        self.login_member()
        self.assertEqual(self.client.get(reverse('forum')).status_code, 404)
        self.assertEqual(self.client.get(reverse('discourse_connect')).status_code, 404)
        resp = self.client.get(reverse('member_dashboard'))
        self.assertNotContains(resp, 'Open the forum')
        self.assertNotContains(resp, 'data-key="forum"')

    @override_settings(FORUM_URL=FORUM)
    def test_members_get_a_link_and_a_redirect(self):
        self.login_member()
        resp = self.client.get(reverse('member_dashboard'))
        self.assertContains(resp, 'Open the forum')
        self.assertContains(resp, 'data-key="forum"')
        resp = self.client.get(reverse('forum'))
        self.assertRedirects(resp, FORUM, fetch_redirect_response=False)

    @override_settings(FORUM_URL=FORUM)
    def test_applicants_and_visitors_are_kept_out(self):
        resp = self.client.get(reverse('forum'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('login'), resp['Location'])

        self.client.login(username='appl', password='pw-appl-123')
        resp = self.client.get(reverse('forum'))
        self.assertRedirects(resp, reverse('applicant_dashboard'))

    # ── Single sign-on (DiscourseConnect) ──

    @override_settings(FORUM_URL=FORUM, DISCOURSE_CONNECT_SECRET=SSO_SECRET)
    def test_single_sign_on_round_trip(self):
        self.login_member()
        resp = self.client.get(reverse('discourse_connect'), discourse_login_request())
        self.assertEqual(resp.status_code, 302)

        target = urlsplit(resp['Location'])
        self.assertEqual(
            f'{target.scheme}://{target.netloc}{target.path}',
            FORUM + '/session/sso_login',
        )
        query = parse_qs(target.query)
        sso, sig = query['sso'][0], query['sig'][0]
        self.assertEqual(
            sig, hmac.new(SSO_SECRET.encode(), sso.encode(), hashlib.sha256).hexdigest()
        )

        fields = parse_qs(base64.b64decode(sso).decode())
        self.assertEqual(fields['nonce'], ['abc123'])
        self.assertEqual(fields['external_id'], [str(self.member.pk)])
        self.assertEqual(fields['email'], ['member@student.gla.ac.uk'])
        self.assertEqual(fields['username'], ['memb'])
        self.assertEqual(fields['name'], ['Mem Ber'])
        self.assertEqual(fields['require_activation'], ['false'])

    @override_settings(FORUM_URL=FORUM, DISCOURSE_CONNECT_SECRET=SSO_SECRET)
    def test_single_sign_on_passes_division_and_lead_groups(self):
        Team.objects.filter(division='land').first().leads.add(self.member)
        self.login_member()
        resp = self.client.get(reverse('discourse_connect'), discourse_login_request())
        self.assertEqual(sso_fields(resp)['add_groups'], ['land,team-leads'])

    @override_settings(FORUM_URL=FORUM, DISCOURSE_CONNECT_SECRET=SSO_SECRET)
    def test_single_sign_on_rejects_a_bad_signature(self):
        self.login_member()
        params = discourse_login_request()
        params['sig'] = 'f' * 64
        resp = self.client.get(reverse('discourse_connect'), params)
        self.assertEqual(resp.status_code, 400)

    @override_settings(FORUM_URL=FORUM, DISCOURSE_CONNECT_SECRET=SSO_SECRET)
    def test_single_sign_on_only_returns_to_the_forum(self):
        self.login_member()
        params = discourse_login_request(return_url='https://evil.example.org/session/sso_login')
        resp = self.client.get(reverse('discourse_connect'), params)
        self.assertEqual(resp.status_code, 400)

    @override_settings(FORUM_URL=FORUM, DISCOURSE_CONNECT_SECRET=SSO_SECRET)
    def test_single_sign_on_needs_a_member_login(self):
        resp = self.client.get(reverse('discourse_connect'), discourse_login_request())
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('login'), resp['Location'])

        self.client.login(username='appl', password='pw-appl-123')
        resp = self.client.get(reverse('discourse_connect'), discourse_login_request())
        self.assertRedirects(resp, reverse('applicant_dashboard'))
