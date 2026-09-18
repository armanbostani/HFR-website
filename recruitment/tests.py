import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Application, Profile, PromotionCode, RecruitmentSettings, Team

TEMP_MEDIA = tempfile.mkdtemp()


def fake_cv():
    return SimpleUploadedFile('cv.pdf', b'%PDF-1.4 fake', content_type='application/pdf')


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class RecruitmentFlowTests(TestCase):
    def setUp(self):
        self.season = RecruitmentSettings.load()
        # Only recruiting teams can be drafted; partner-led ones are listed on
        # the site but recruit elsewhere
        self.teams = list(Team.objects.filter(is_recruiting=True)[:3])
        self.lead = User.objects.create_user('leader', 'lead@hfr.org', 'pw-lead-123')
        Profile.objects.create(user=self.lead, role=Profile.ROLE_MEMBER)
        self.teams[0].leads.add(self.lead)

    def signup(self, username='fresher', name='Fresh Fresher'):
        # The GUID is the username, so the local part of the email becomes it
        return self.client.post(reverse('signup'), {
            'name': name,
            'email': f'{username}@student.gla.ac.uk',
            'password': 'sup3r-secret-pw',
            'password_confirm': 'sup3r-secret-pw',
        })

    def submit_application(self):
        return self.client.post(reverse('apply'), {
            'year_of_study': '2',
            'major': 'Aerospace Systems',
            'first_pick': self.teams[0].pk,
            'alternative': self.teams[1].pk,
            'wildcard': self.teams[2].pk,
            'cv': fake_cv(),
            'why_society': 'I want to build hydrogen boats.',
            'why_division': 'The Vital Spark looks incredible.',
            'what_makes_you': 'I show up and I ask questions.',
            'what_to_learn': 'Fuel cells, CAD, teamwork.',
        })

    # ── Accounts ──

    def test_signup_creates_applicant_and_shows_welcome(self):
        resp = self.signup()
        self.assertEqual(resp.status_code, 200)
        # The welcome overlay appears over the form, then a timer moves them on
        self.assertContains(resp, 'Welcome')
        self.assertContains(resp, 'start your application')
        user = User.objects.get(username='fresher')
        self.assertEqual(user.profile.role, Profile.ROLE_APPLICANT)
        self.assertEqual(user.first_name, 'Fresh')
        self.assertIn('_auth_user_id', self.client.session)

    def test_signup_rejects_non_glasgow_email(self):
        resp = self.client.post(reverse('signup'), {
            'name': 'Outside Person',
            'email': 'someone@gmail.com',
            'password': 'sup3r-secret-pw',
            'password_confirm': 'sup3r-secret-pw',
        })
        self.assertContains(resp, 'not a University of Glasgow address')
        self.assertFalse(User.objects.filter(email='someone@gmail.com').exists())

    def test_signup_accepts_the_staff_domain_too(self):
        resp = self.client.post(reverse('signup'), {
            'name': 'Post Grad',
            'email': 'p.grad@glasgow.ac.uk',
            'password': 'sup3r-secret-pw',
            'password_confirm': 'sup3r-secret-pw',
        })
        self.assertContains(resp, 'Welcome')
        self.assertTrue(User.objects.filter(email='p.grad@glasgow.ac.uk').exists())

    def test_signup_rejects_mismatched_passwords(self):
        resp = self.client.post(reverse('signup'), {
            'name': 'Typo Person',
            'email': 'typo@student.gla.ac.uk',
            'password': 'sup3r-secret-pw',
            'password_confirm': 'different-password',
        })
        self.assertContains(resp, 'do not match')
        self.assertFalse(User.objects.filter(username='typo').exists())

    def test_circle_logs_out_and_returns_home(self):
        self.signup()
        self.assertIn('_auth_user_id', self.client.session)
        resp = self.client.post(reverse('logout'))
        self.assertRedirects(resp, reverse('home'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_signup_closed_when_recruitment_over(self):
        self.season.is_open = False
        self.season.save()
        resp = self.client.get(reverse('signup'))
        self.assertTemplateUsed(resp, 'recruitment/signup_closed.html')
        self.assertContains(resp, 'next academic semester')

    def test_dashboard_requires_login(self):
        resp = self.client.get(reverse('applicant_dashboard'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('login'), resp.url)

    # ── Application ──

    def test_submit_application(self):
        self.signup()
        resp = self.submit_application()
        self.assertRedirects(resp, reverse('applicant_dashboard'))
        app = Application.objects.get(applicant__username='fresher')
        self.assertEqual(app.status, Application.STATUS_SUBMITTED)
        self.assertEqual(app.current_team, self.teams[0])
        # The dashboard shows the five stage progress bar
        resp = self.client.get(reverse('applicant_dashboard'))
        for label in ('Application sent', 'Under review', 'Interview',
                      'Decision pending', 'Decision'):
            self.assertContains(resp, label)
        self.assertContains(resp, app.submitted_at.strftime('%d/%m/%Y'))

    def test_progress_bar_advances_with_status(self):
        self.signup()
        self.submit_application()
        app = Application.objects.get()

        for status, stage in [
            (Application.STATUS_SUBMITTED, 1),
            (Application.STATUS_UNDER_REVIEW, 2),
            (Application.STATUS_INTERVIEW, 3),
            (Application.STATUS_DECISION_PENDING, 4),
            (Application.STATUS_ACCEPTED, 5),
        ]:
            app.status = status
            app.save()
            self.assertEqual(app.stage_number, stage)
            done = [s for s in app.stages if s['done']]
            self.assertEqual(len(done), stage if app.is_final else stage - 1)

    def test_empty_dashboard_prompts_an_application(self):
        self.signup()
        resp = self.client.get(reverse('applicant_dashboard'))
        self.assertContains(resp, 'Looks quite empty')
        self.assertContains(resp, 'Apply Now')

    def test_accepted_shows_join_then_code_screen(self):
        self.signup()
        self.submit_application()
        app = Application.objects.get()
        app.status = Application.STATUS_ACCEPTED
        app.save()

        resp = self.client.get(reverse('applicant_dashboard'))
        self.assertContains(resp, 'Join HFR')
        resp = self.client.get(reverse('applicant_dashboard') + '?join=1')
        self.assertContains(resp, 'Congratulations for completing')

    def test_duplicate_picks_rejected(self):
        self.signup()
        resp = self.client.post(reverse('apply'), {
            'year_of_study': '1',
            'major': 'Economics',
            'first_pick': self.teams[0].pk,
            'alternative': self.teams[0].pk,
            'wildcard': self.teams[2].pk,
            'cv': fake_cv(),
            'why_society': 'x', 'why_division': 'x',
            'what_makes_you': 'x', 'what_to_learn': 'x',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Application.objects.exists())

    def test_cannot_apply_twice(self):
        self.signup()
        self.submit_application()
        resp = self.client.get(reverse('apply'))
        self.assertRedirects(resp, reverse('applicant_dashboard'))

    # ── Team lead flow ──

    def lead_client_with_application(self):
        self.signup()
        self.submit_application()
        app = Application.objects.get()
        self.client.logout()
        self.client.login(username='leader', password='pw-lead-123')
        return app

    def test_lead_sees_applicant_on_board(self):
        self.lead_client_with_application()
        resp = self.client.get(reverse('lead_dashboard'))
        self.assertContains(resp, 'fresher')
        self.assertContains(resp, self.teams[0].name)

    def test_lead_interview_then_accept_issues_code(self):
        app = self.lead_client_with_application()
        self.client.post(reverse('lead_action', args=[app.pk, 'interview']))
        app.refresh_from_db()
        self.assertEqual(app.status, Application.STATUS_INTERVIEW)

        self.client.post(reverse('lead_action', args=[app.pk, 'accept']))
        app.refresh_from_db()
        self.assertEqual(app.status, Application.STATUS_ACCEPTED)
        self.assertTrue(PromotionCode.objects.filter(application=app).exists())

    def test_reject_passes_to_next_pick_then_final(self):
        app = self.lead_client_with_application()
        self.client.post(reverse('lead_action', args=[app.pk, 'reject']))
        app.refresh_from_db()
        self.assertEqual(app.current_choice, 2)
        self.assertEqual(app.current_team, self.teams[1])
        self.assertEqual(app.status, Application.STATUS_SUBMITTED)

        # Not on teams[0]'s board any more → lead of teams[0] can't act on it
        resp = self.client.post(reverse('lead_action', args=[app.pk, 'reject']))
        app.refresh_from_db()
        self.assertEqual(app.current_choice, 2)

        # Reject from picks 2 and 3 (as staff, who sees all boards)
        self.lead.is_staff = True
        self.lead.save()
        self.client.post(reverse('lead_action', args=[app.pk, 'reject']))
        app.refresh_from_db()
        self.assertEqual(app.current_choice, 3)
        self.client.post(reverse('lead_action', args=[app.pk, 'reject']))
        app.refresh_from_db()
        self.assertEqual(app.status, Application.STATUS_REJECTED)

    # ── Promotion + onboarding ──

    def accepted_applicant_with_code(self):
        self.signup()
        self.submit_application()
        app = Application.objects.get()
        app.status = Application.STATUS_ACCEPTED
        app.save()
        return app, PromotionCode.issue(app, self.lead)

    def test_wrong_code_rejected(self):
        self.accepted_applicant_with_code()
        resp = self.client.post(reverse('redeem_code'), {'code': 'NOPE1234'}, follow=True)
        self.assertContains(resp, "check it with your team lead")
        user = User.objects.get(username='fresher')
        self.assertEqual(user.profile.role, Profile.ROLE_APPLICANT)

    def test_full_promotion_and_onboarding_flow(self):
        app, code = self.accepted_applicant_with_code()

        # Redeem → promoted to onboarding, logged out
        resp = self.client.post(reverse('redeem_code'), {'code': code.code.lower()})
        self.assertTemplateUsed(resp, 'recruitment/promoted.html')
        user = User.objects.get(username='fresher')
        self.assertEqual(user.profile.role, Profile.ROLE_ONBOARDING)
        code.refresh_from_db()
        self.assertTrue(code.is_used)
        # Actually logged out
        self.assertNotIn('_auth_user_id', self.client.session)

        # Log back in → routed to onboarding
        self.client.login(username='fresher', password='sup3r-secret-pw')
        resp = self.client.get(reverse('account_router'))
        self.assertRedirects(resp, reverse('onboarding'))
        # Applicant dashboard also pushes to onboarding
        resp = self.client.get(reverse('applicant_dashboard'))
        self.assertRedirects(resp, reverse('onboarding'))

        # Complete onboarding (wireframe 24 fields) → full member + completion page
        resp = self.client.post(reverse('onboarding'), {
            'display_name': 'Fresh',
            'avatar_preset': 'h2-orange',
            'contact_method': 'whatsapp',
            'contact_time': 'evening',
            'phone': '+44 7000 000000',
        })
        self.assertTemplateUsed(resp, 'recruitment/onboarding_complete.html')
        self.assertContains(resp, "You're all set")
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.role, Profile.ROLE_MEMBER)
        self.assertIsNotNone(user.profile.onboarded_at)

        # Account navigation rides in the avatar overlay on every member page
        resp = self.client.get(reverse('member_home'))
        self.assertRedirects(resp, reverse('member_dashboard'))
        resp = self.client.get(reverse('member_dashboard'))
        self.assertContains(resp, 'hfr-account-rail')
        self.assertContains(resp, 'Log Out')

    def test_onboarding_requires_avatar_and_whatsapp_phone(self):
        self.accepted_applicant_with_code()
        profile = Profile.objects.get(user__username='fresher')
        profile.role = Profile.ROLE_ONBOARDING
        profile.save()
        # No avatar, whatsapp without phone → stays on the form
        resp = self.client.post(reverse('onboarding'), {
            'display_name': 'Fresh',
            'contact_method': 'whatsapp',
            'contact_time': 'anytime',
            'phone': '',
        })
        self.assertTemplateUsed(resp, 'recruitment/onboarding.html')
        self.assertContains(resp, 'Upload a photo or pick a premade one')
        self.assertContains(resp, 'reach you on WhatsApp')
        profile.refresh_from_db()
        self.assertEqual(profile.role, Profile.ROLE_ONBOARDING)

    # ── Flexible login (username / email / display name) ──

    def test_login_with_email_and_display_name(self):
        self.signup()
        profile = Profile.objects.get(user__username='fresher')
        profile.display_name = 'Speedster'
        profile.save()
        self.client.logout()

        self.assertTrue(self.client.login(
            username='fresher@student.gla.ac.uk', password='sup3r-secret-pw'))
        self.client.logout()
        self.assertTrue(self.client.login(
            username='speedster', password='sup3r-secret-pw'))
        self.client.logout()
        self.assertFalse(self.client.login(
            username='speedster', password='wrong-pw'))

    # ── Member area ──

    def make_member(self, team=None):
        """An accepted, onboarded member, optionally placed on a team."""
        self.signup()
        self.submit_application()
        app = Application.objects.get()
        app.status = Application.STATUS_ACCEPTED
        app.save()
        profile = Profile.objects.get(user__username='fresher')
        profile.role = Profile.ROLE_MEMBER
        profile.display_name = 'Fresh'
        profile.contact_method = 'email'
        profile.contact_time = 'anytime'
        profile.avatar_preset = 'h2-orange'
        profile.save()
        return app, profile

    def test_member_home_redirects_to_dashboard(self):
        self.make_member()
        resp = self.client.get(reverse('member_home'))
        self.assertRedirects(resp, reverse('member_dashboard'))

    def test_member_dashboard_shows_their_team_and_lead(self):
        app, _ = self.make_member()
        resp = self.client.get(reverse('member_dashboard'))
        self.assertContains(resp, app.current_team.name)
        # The lead of that team is named on the page
        self.assertContains(resp, 'leader')

    def test_applicant_cannot_reach_member_pages(self):
        self.signup()
        for name in ('member_home', 'member_dashboard', 'edit_profile'):
            resp = self.client.get(reverse(name))
            self.assertRedirects(resp, reverse('applicant_dashboard'))

    def test_edit_profile_saves_changes(self):
        self.make_member()
        resp = self.client.post(reverse('edit_profile'), {
            'display_name': 'Speedster',
            'full_name': 'Fresh Renamed',
            'email': 'fresher@student.gla.ac.uk',
            'avatar_preset': 'h2-gold',
        })
        self.assertRedirects(resp, reverse('edit_profile'))
        profile = Profile.objects.get(user__username='fresher')
        self.assertEqual(profile.display_name, 'Speedster')
        self.assertEqual(profile.avatar_preset, 'h2-gold')
        self.assertEqual(profile.user.last_name, 'Renamed')

    def test_member_can_change_password(self):
        self.make_member()
        resp = self.client.post(reverse('edit_profile'), {
            'display_name': 'Fresh',
            'full_name': 'Fresh Fresher',
            'email': 'fresher@student.gla.ac.uk',
            'avatar_preset': 'h2-orange',
            'old_password': 'sup3r-secret-pw',
            'new_password1': 'a-brand-new-pw-42',
            'new_password2': 'a-brand-new-pw-42',
        })
        self.assertRedirects(resp, reverse('edit_profile'))
        # Still signed in afterwards, and the new password works
        self.assertIn('_auth_user_id', self.client.session)
        self.client.logout()
        self.assertTrue(self.client.login(username='fresher', password='a-brand-new-pw-42'))

    def test_non_lead_cannot_open_lead_dashboard(self):
        self.signup()
        resp = self.client.get(reverse('lead_dashboard'))
        self.assertRedirects(resp, reverse('account_router'), target_status_code=302)
