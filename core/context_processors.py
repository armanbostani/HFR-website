from django.conf import settings


def site(request):
    """Society-wide values every template can use."""
    return {
        'contact_email': settings.CONTACT_EMAIL,
        'forum_url': settings.FORUM_URL,
    }
