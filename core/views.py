from django.shortcuts import render

from recruitment.models import RecruitmentSettings, Team

# Division pages list their sub-teams straight from the draft board, so an
# edit in the admin shows up on the public site too.
DIVISION_PAGES = {
    'core/division_land.html': 'land',
    'core/division_sea.html': 'sea',
    'core/division_air.html': 'air',
}


def home(request):
    return render(request, 'core/index.html')


def page(request, template_name):
    context = {}
    if template_name == 'core/register.html':
        context['season'] = RecruitmentSettings.load()
    division = DIVISION_PAGES.get(template_name)
    if division:
        context['teams'] = Team.objects.filter(division=division)
    return render(request, template_name, context)
