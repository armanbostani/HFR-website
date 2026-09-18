import secrets

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone

# CVs are personal data: kept outside MEDIA_ROOT with no public URL,
# reachable only through the lead-checked download view.
private_storage = FileSystemStorage(location=settings.PRIVATE_MEDIA_ROOT)


class RecruitmentSettings(models.Model):
    """Singleton toggle for the recruitment season."""
    is_open = models.BooleanField(default=True)
    close_date = models.DateTimeField(
        null=True, blank=True,
        help_text="Informational only. Shown on the register and signup pages; does not close signups on its own.",
    )
    closed_message = models.TextField(
        default="Recruitment season is over and will begin next academic semester. "
                "Follow us on Instagram to hear when applications reopen."
    )

    class Meta:
        verbose_name = "Recruitment settings"
        verbose_name_plural = "Recruitment settings"

    def __str__(self):
        return "Recruitment: open" if self.is_open else "Recruitment: closed"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Team(models.Model):
    """A sub-team on the draft board, grouped under one of the four divisions."""
    DIVISION_CHOICES = [
        ('land', 'Land'),
        ('sea', 'Sea'),
        ('air', 'Air'),
        ('operations', 'Operations'),
    ]

    division = models.CharField(max_length=20, choices=DIVISION_CHOICES, default='land')
    name = models.CharField(max_length=80)
    sort_order = models.PositiveSmallIntegerField(default=0)
    tagline = models.CharField(max_length=160, blank=True)
    partner = models.CharField(
        max_length=40, blank=True,
        help_text='Partner society that runs this sub-team, e.g. "UGA". '
                  'Leave blank for HFR-run teams.',
    )
    leads = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name='led_teams'
    )
    is_recruiting = models.BooleanField(default=True)

    class Meta:
        ordering = ['division', 'sort_order', 'name']
        constraints = [
            models.UniqueConstraint(fields=['division', 'name'], name='unique_team_per_division'),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_division_display()})"


class Profile(models.Model):
    ROLE_APPLICANT = 'applicant'
    ROLE_ONBOARDING = 'onboarding'
    ROLE_MEMBER = 'member'
    ROLE_CHOICES = [
        (ROLE_APPLICANT, 'Applicant'),
        (ROLE_ONBOARDING, 'Onboarding HFR member'),
        (ROLE_MEMBER, 'Onboarded HFR member'),
    ]

    AVATAR_PRESETS = [
        ('h2-orange', 'H2 Orange'),
        ('h2-gold', 'H2 Gold'),
        ('h2-teal', 'H2 Teal'),
        ('h2-slate', 'H2 Slate'),
    ]
    CONTACT_METHODS = [('email', 'Email'), ('whatsapp', 'WhatsApp')]
    CONTACT_TIMES = [('morning', 'Morning'), ('evening', 'Evening'), ('anytime', 'Anytime')]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_APPLICANT)

    # Onboarding details (wireframe 24), all mandatory during onboarding
    display_name = models.CharField(
        max_length=40, unique=True, null=True, blank=True,
        help_text='You can also log in with this.',
    )
    avatar = models.ImageField(upload_to='avatars/', blank=True)
    avatar_preset = models.CharField(max_length=20, choices=AVATAR_PRESETS, blank=True)
    contact_method = models.CharField(max_length=10, choices=CONTACT_METHODS, blank=True)
    contact_time = models.CharField(max_length=10, choices=CONTACT_TIMES, blank=True)
    phone = models.CharField(max_length=30, blank=True)  # needed when WhatsApp is chosen
    onboarded_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def is_onboarded(self):
        return self.role == self.ROLE_MEMBER

    @property
    def needs_onboarding(self):
        return self.role == self.ROLE_ONBOARDING

    def complete_onboarding(self):
        self.role = self.ROLE_MEMBER
        self.onboarded_at = timezone.now()
        self.save()


class Application(models.Model):
    STATUS_SUBMITTED = 'submitted'
    STATUS_UNDER_REVIEW = 'under_review'
    STATUS_INTERVIEW = 'interview'
    STATUS_DECISION_PENDING = 'decision_pending'
    STATUS_ACCEPTED = 'accepted'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_SUBMITTED, 'Application sent'),
        (STATUS_UNDER_REVIEW, 'Application under review'),
        (STATUS_INTERVIEW, 'Interview stage'),
        (STATUS_DECISION_PENDING, 'Decision pending'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    # The five stages on the applicant's progress bar. Accepted and rejected
    # share the last one.
    STAGE_LABELS = [
        'Application sent',
        'Under review',
        'Interview',
        'Decision pending',
        'Decision',
    ]

    YEAR_CHOICES = [
        ('1', 'Year 1'), ('2', 'Year 2'), ('3', 'Year 3'),
        ('4', 'Year 4'), ('5', 'Year 5'), ('pg', 'Postgraduate'),
    ]

    applicant = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='application'
    )

    # Step 1: about you
    year_of_study = models.CharField(max_length=2, choices=YEAR_CHOICES)
    major = models.CharField(max_length=120)

    # Step 2: draft board picks
    first_pick = models.ForeignKey(
        Team, on_delete=models.PROTECT, related_name='first_pick_applications'
    )
    alternative = models.ForeignKey(
        Team, on_delete=models.PROTECT, related_name='alternative_applications'
    )
    wildcard = models.ForeignKey(
        Team, on_delete=models.PROTECT, related_name='wildcard_applications'
    )
    # Which of the three picks is currently reviewing this application (1-3)
    current_choice = models.PositiveSmallIntegerField(default=1)

    # Step 3: application form (questions from wireframe p12)
    cv = models.FileField(
        upload_to='cvs/%Y/', storage=private_storage,
        validators=[FileExtensionValidator(['pdf'], 'Your CV must be a PDF.')],
    )
    why_society = models.TextField("Why this society?")
    why_division = models.TextField("Why this division?")
    what_makes_you = models.TextField("What makes you you?")
    what_to_learn = models.TextField("What do you want to learn?")

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_SUBMITTED
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['submitted_at']

    def __str__(self):
        return f"{self.applicant.username} → {self.first_pick} ({self.get_status_display()})"

    @property
    def picks(self):
        return [self.first_pick, self.alternative, self.wildcard]

    @property
    def current_team(self):
        """The team whose draft board this application currently sits on."""
        return self.picks[self.current_choice - 1]

    def pass_to_next_choice(self):
        """Current team rejected the applicant: move to the next pick,
        or reject outright after the wildcard."""
        if self.current_choice < 3:
            self.current_choice += 1
            self.status = self.STATUS_SUBMITTED
        else:
            self.status = self.STATUS_REJECTED
        self.save()

    @property
    def is_final(self):
        return self.status in (self.STATUS_ACCEPTED, self.STATUS_REJECTED)

    @property
    def stage_number(self):
        """Which of the five progress bar stages they are currently on."""
        return {
            self.STATUS_SUBMITTED: 1,
            self.STATUS_UNDER_REVIEW: 2,
            self.STATUS_INTERVIEW: 3,
            self.STATUS_DECISION_PENDING: 4,
            self.STATUS_ACCEPTED: 5,
            self.STATUS_REJECTED: 5,
        }[self.status]

    @property
    def stages(self):
        """The progress bar, one entry per stage."""
        reached = self.stage_number
        out = []
        for i, label in enumerate(self.STAGE_LABELS, start=1):
            if i == 5 and self.is_final:
                label = 'Accepted' if self.status == self.STATUS_ACCEPTED else 'Rejected'
            out.append({
                'number': i,
                'label': label,
                'done': i < reached or (i == reached and self.is_final),
                'active': i == reached and not self.is_final,
                'rejected': i == 5 and self.status == self.STATUS_REJECTED,
            })
        return out


class PromotionCode(models.Model):
    """Code a team lead hands to an accepted applicant (once they confirm SRC
    membership) to promote their account to an onboarding HFR member."""
    code = models.CharField(max_length=12, unique=True)
    application = models.OneToOneField(
        Application, on_delete=models.CASCADE, related_name='promotion_code'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='codes_issued'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.code} → {self.application.applicant.username}"

    @property
    def is_used(self):
        return self.used_at is not None

    @classmethod
    def issue(cls, application, created_by):
        code, _ = cls.objects.get_or_create(
            application=application,
            defaults={
                'code': secrets.token_hex(4).upper(),
                'created_by': created_by,
            },
        )
        return code

    def redeem(self):
        self.used_at = timezone.now()
        self.save()
