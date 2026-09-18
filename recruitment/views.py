import base64
import hashlib
import hmac
from functools import wraps
from urllib.parse import parse_qs, urlencode, urlsplit

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.http import FileResponse, Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import (
    COMMON_DEGREES, ApplicationForm, EditProfileForm, OnboardingForm,
    RedeemCodeForm, SignUpForm,
)
from .models import Application, Profile, PromotionCode, RecruitmentSettings, Team


def get_profile(user):
    profile, _ = Profile.objects.get_or_create(user=user)
    return profile


def is_team_lead(user):
    return user.is_authenticated and (user.led_teams.exists() or user.is_staff)


# ── Accounts ────────────────────────────────────────────────────────────────

def signup(request):
    """Account creation, only available while recruitment is open."""
    if request.user.is_authenticated:
        return redirect('account_router')

    season = RecruitmentSettings.load()
    if not season.is_open:
        return render(request, 'recruitment/signup_closed.html', {'season': season})

    created_name = None
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            # The welcome overlay shows over this page, then an invisible timer
            # carries them to their dashboard.
            created_name = user.first_name or user.username
    else:
        form = SignUpForm()

    return render(request, 'recruitment/signup.html', {
        'form': form,
        'season': season,
        'created': created_name is not None,
        'created_name': created_name,
    })


@login_required
def account_router(request):
    """Single entry point behind the top-right nav button: send each role
    where they belong."""
    profile = get_profile(request.user)
    if profile.needs_onboarding:
        return redirect('onboarding')
    if profile.is_onboarded or is_team_lead(request.user):
        return redirect('member_home')
    return redirect('applicant_dashboard')


# ── Applicant ───────────────────────────────────────────────────────────────

@login_required
def applicant_dashboard(request):
    profile = get_profile(request.user)
    if profile.needs_onboarding:
        return redirect('onboarding')
    # Onboarded members and leads have moved past applying
    if profile.is_onboarded or is_team_lead(request.user):
        return redirect('member_home')

    application = Application.objects.filter(applicant=request.user).first()
    accepted = application and application.status == Application.STATUS_ACCEPTED

    return render(request, 'recruitment/dashboard.html', {
        'profile': profile,
        'application': application,
        'redeem_form': RedeemCodeForm() if accepted else None,
        # Join HFR on the accepted state opens the code entry screen
        'joining': accepted and request.GET.get('join') == '1',
    })


@login_required
def apply(request):
    profile = get_profile(request.user)
    if profile.role != Profile.ROLE_APPLICANT:
        return redirect('account_router')
    if Application.objects.filter(applicant=request.user).exists():
        messages.info(request, 'You have already submitted an application.')
        return redirect('applicant_dashboard')

    season = RecruitmentSettings.load()
    if not season.is_open:
        return render(request, 'recruitment/signup_closed.html', {'season': season})

    if request.method == 'POST':
        form = ApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            application = form.save(commit=False)
            application.applicant = request.user
            application.save()
            messages.success(request, 'Application submitted. Track its progress here.')
            return redirect('applicant_dashboard')
    else:
        form = ApplicationForm()

    recruiting = Team.objects.filter(is_recruiting=True)
    divisions = [
        {'key': key, 'label': label,
         'teams': [t for t in recruiting if t.division == key]}
        for key, label in Team.DIVISION_CHOICES
    ]
    return render(request, 'recruitment/apply.html', {
        'form': form,
        'divisions': [d for d in divisions if d['teams']],
        'degree_suggestions': COMMON_DEGREES,
    })


@login_required
@require_POST
def redeem_code(request):
    """Accepted applicant enters the code their team lead gave them after
    confirming SRC membership → promoted to onboarding member, logged out."""
    application = Application.objects.filter(
        applicant=request.user, status=Application.STATUS_ACCEPTED
    ).first()
    if application is None:
        messages.error(request, 'You need an accepted application to redeem a code.')
        return redirect('applicant_dashboard')

    form = RedeemCodeForm(request.POST)
    if form.is_valid():
        code = PromotionCode.objects.filter(
            application=application, code=form.cleaned_data['code'], used_at__isnull=True
        ).first()
        if code:
            code.redeem()
            profile = get_profile(request.user)
            profile.role = Profile.ROLE_ONBOARDING
            profile.save()
            logout(request)
            return render(request, 'recruitment/promoted.html')
        messages.error(request, "That code doesn't match. Please check it with your team lead.")
    else:
        messages.error(request, 'Enter the code your team lead gave you.')
    return redirect('applicant_dashboard')


# ── Onboarding ──────────────────────────────────────────────────────────────

@login_required
def onboarding(request):
    profile = get_profile(request.user)
    if profile.is_onboarded:
        return redirect('member_home')
    if not profile.needs_onboarding:
        return redirect('applicant_dashboard')

    if request.method == 'POST':
        form = OnboardingForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            profile.complete_onboarding()
            # Completion screen explains what they can now do,
            # then sends them back to the home page (wireframe 24).
            return render(request, 'recruitment/onboarding_complete.html', {
                'profile': profile,
                'is_lead': is_team_lead(request.user),
            })
    else:
        form = OnboardingForm(instance=profile)

    return render(request, 'recruitment/onboarding.html', {'form': form})


def member_only(view):
    """Members only. Applicants get sent back to their own dashboard and
    anyone mid onboarding is pushed to finish it."""
    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        profile = get_profile(request.user)
        if profile.needs_onboarding:
            return redirect('onboarding')
        if not (profile.is_onboarded or is_team_lead(request.user)):
            return redirect('applicant_dashboard')
        return view(request, *args, **kwargs)
    return wrapper


@member_only
def member_home(request):
    """Account navigation now lives in the avatar overlay, so send members on."""
    return redirect('member_dashboard')


@member_only
def member_dashboard(request):
    """Where they landed and who runs it."""
    application = Application.objects.filter(
        applicant=request.user, status=Application.STATUS_ACCEPTED
    ).select_related('first_pick', 'alternative', 'wildcard').first()

    team = application.current_team if application else None

    teammates = []
    if team:
        # Everyone else accepted onto the same sub team
        for other in Application.objects.filter(
            status=Application.STATUS_ACCEPTED
        ).exclude(applicant=request.user).select_related(
            'applicant', 'first_pick', 'alternative', 'wildcard'
        ):
            if other.current_team.pk == team.pk:
                teammates.append(other.applicant)

    return render(request, 'recruitment/member_dashboard.html', {
        'profile': get_profile(request.user),
        'team': team,
        'leads': team.leads.all() if team else [],
        'teammates': teammates,
        'application': application,
        'led_teams': request.user.led_teams.all(),
        'is_lead': is_team_lead(request.user),
    })


@member_only
def edit_profile(request):
    profile = get_profile(request.user)
    if request.method == 'POST':
        form = EditProfileForm(request.POST, request.FILES, instance=profile)
        password_form = PasswordChangeForm(request.user, request.POST)

        changing_password = any(
            request.POST.get(f) for f in
            ('old_password', 'new_password1', 'new_password2')
        )
        profile_ok = form.is_valid()
        password_ok = password_form.is_valid() if changing_password else True

        if profile_ok and password_ok:
            form.save()
            if changing_password:
                user = password_form.save()
                # Changing a password normally signs you out
                update_session_auth_hash(request, user)
                messages.success(request, 'Profile and password updated.')
            else:
                messages.success(request, 'Profile updated.')
            return redirect('edit_profile')
    else:
        form = EditProfileForm(instance=profile)
        password_form = PasswordChangeForm(request.user)

    return render(request, 'recruitment/edit_profile.html', {
        'form': form,
        'password_form': password_form,
        'profile': profile,
    })


# ── Team lead dashboard ─────────────────────────────────────────────────────

def lead_teams_for(user):
    if user.is_staff:
        return Team.objects.all()
    return user.led_teams.all()


@login_required
def lead_dashboard(request):
    if not is_team_lead(request.user):
        messages.error(request, 'The recruitment dashboard is for team leads.')
        return redirect('account_router')

    teams = lead_teams_for(request.user)
    boards = []
    for team in teams:
        # Applications currently sitting on this team's draft board
        apps = [
            a for a in Application.objects.select_related(
                'applicant', 'first_pick', 'alternative', 'wildcard'
            ).exclude(status=Application.STATUS_REJECTED)
            if a.current_team.pk == team.pk
        ]
        boards.append({'team': team, 'applications': apps})

    return render(request, 'recruitment/lead_dashboard.html', {'boards': boards})


@login_required
def application_cv(request, app_id):
    """CVs are stored outside the public media tree, so this is the only
    way to fetch one: team leads for the applicant's current pick only."""
    if not is_team_lead(request.user):
        return redirect('account_router')

    application = get_object_or_404(
        Application.objects.select_related('first_pick', 'alternative', 'wildcard'),
        pk=app_id,
    )
    if not request.user.is_staff and application.current_team not in request.user.led_teams.all():
        messages.error(request, "That application isn't on your draft board.")
        return redirect('lead_dashboard')

    name = application.applicant.get_full_name() or application.applicant.username
    return FileResponse(
        application.cv.open('rb'), as_attachment=True,
        filename=f"{name.replace(' ', '_')}_CV.pdf",
    )


@login_required
@require_POST
def lead_action(request, app_id, action):
    if not is_team_lead(request.user):
        return redirect('account_router')

    application = get_object_or_404(
        Application.objects.select_related('first_pick', 'alternative', 'wildcard'),
        pk=app_id,
    )
    if not request.user.is_staff and application.current_team not in request.user.led_teams.all():
        messages.error(request, "That application isn't on your draft board.")
        return redirect('lead_dashboard')
    if application.is_final and action != 'code':
        messages.error(request, 'That application has already been decided.')
        return redirect('lead_dashboard')

    name = application.applicant.get_full_name() or application.applicant.username
    if action == 'interview':
        application.status = Application.STATUS_INTERVIEW
        application.save()
        messages.success(request, f'{name} moved to interview stage.')
    elif action == 'accept':
        application.status = Application.STATUS_ACCEPTED
        application.save()
        code = PromotionCode.issue(application, request.user)
        messages.success(
            request,
            f'{name} accepted. Once they confirm SRC membership, give them code {code.code}.',
        )
    elif action == 'reject':
        was_last = application.current_choice >= 3
        application.pass_to_next_choice()
        if was_last:
            messages.info(request, f'{name} was on their final pick and has been rejected.')
        else:
            messages.info(
                request,
                f'{name} passed to their next pick: {application.current_team}.',
            )
    else:
        messages.error(request, 'Unknown action.')
    return redirect('lead_dashboard')


# ── Forum (Discourse) ───────────────────────────────────────────────────────

@member_only
def forum(request):
    """The members' way into the forum. Until HFR_FORUM_URL is set there is
    nothing here, and nothing on the site links to it."""
    if not settings.FORUM_URL:
        raise Http404
    return redirect(settings.FORUM_URL)


def forum_groups(user):
    """Discourse groups a member is added to on sign-in: their division, plus
    a leads group for team leads. Names the forum doesn't know are ignored."""
    groups = set()
    application = Application.objects.filter(
        applicant=user, status=Application.STATUS_ACCEPTED
    ).select_related('first_pick', 'alternative', 'wildcard').first()
    if application:
        groups.add(application.current_team.division)
    for team in user.led_teams.all():
        groups.add(team.division)
        groups.add('team-leads')
    if user.is_staff:
        groups.add('exec')
    return sorted(groups)


@member_only
def discourse_connect(request):
    """DiscourseConnect provider. The forum sends people here to log in and we
    send them back with who they are, signed with the shared secret, so the
    website account is the only forum account anyone needs. Only onboarded
    members and team leads get past member_only, so only they can reach the
    forum at all."""
    secret = settings.DISCOURSE_CONNECT_SECRET
    if not (secret and settings.FORUM_URL):
        raise Http404

    payload = request.GET.get('sso', '')
    signature = request.GET.get('sig', '')
    expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not (payload and signature and hmac.compare_digest(expected, signature)):
        return HttpResponseBadRequest('Bad forum sign-in request.')

    try:
        inbound = parse_qs(base64.b64decode(payload).decode())
        nonce = inbound['nonce'][0]
        return_url = inbound['return_sso_url'][0]
    except (ValueError, KeyError, UnicodeDecodeError):
        return HttpResponseBadRequest('Bad forum sign-in request.')
    if not url_has_allowed_host_and_scheme(
        return_url,
        allowed_hosts={urlsplit(settings.FORUM_URL).netloc},
        require_https=settings.FORUM_URL.startswith('https://'),
    ):
        return HttpResponseBadRequest('Bad forum sign-in request.')

    user = request.user
    profile = get_profile(user)
    fields = {
        'nonce': nonce,
        'external_id': user.pk,
        'email': user.email,
        'username': profile.display_name or user.username,
        'name': user.get_full_name() or profile.display_name or user.username,
        'require_activation': 'false',
        'add_groups': ','.join(forum_groups(user)),
    }
    if profile.avatar:
        fields['avatar_url'] = request.build_absolute_uri(profile.avatar.url)

    outbound = base64.b64encode(urlencode(fields).encode()).decode()
    outbound_sig = hmac.new(secret.encode(), outbound.encode(), hashlib.sha256).hexdigest()
    return redirect(f"{return_url}?{urlencode({'sso': outbound, 'sig': outbound_sig})}")
