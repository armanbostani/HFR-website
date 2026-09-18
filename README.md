# UG Hydrogen Fuel Racing

The website for Hydrogen Fuel Racing (HFR), the University of Glasgow's student
society building hydrogen powered vehicles for land, sea and air. The site is the
public face of the society and runs the recruitment flow: applications, team lead
draft boards, and the member area.

Live divisions: Land (Shell Eco-Marathon endurance vehicle), Sea (Energy Class
boat for the Monaco Energy Boat Challenge), Air (hydrogen plane concept with
UGA), and Operations (business, finance, creative direction).

## Team structure

Sub-teams live in the database (`recruitment.Team`) and are seeded by
migration. The division pages and the application form both read from it, so
the committee edits teams in the admin rather than in templates.

| Division | Sub-teams |
| --- | --- |
| Land | Data & Telemetry, Electrical, Chassis & Component, Vehicle Dynamics, Aerodynamics, HFC |
| Sea | Cockpit & Structures, Hydrogen Systems, Fuel Cell & Power, Propulsion & Performance, Controls & Electronics (provisional) |
| Air | Aerodynamics, Structures, Avionics & Flight Operations (all UGA-led, listed but not recruiting here); Propulsion, Energy Management & HFC (HFR) |
| Operations | Business, Finance & Contracts (Creative Direction exists but is switched off) |

A team's `partner` field marks it as run by another society; the division page
shows the badge and the application form leaves it out.

## Members' forum

The society forum (Discourse) is reachable from the site once `HFR_FORUM_URL`
is set: a Forum entry in the member account menu, a panel on the member
dashboard, and `/forum/` for members only. With `HFR_DISCOURSE_CONNECT_SECRET`
set as well, the site acts as the forum's login (DiscourseConnect at
`/forum/sso/`), so a website account is the only account a member needs.
Details in [DEPLOYMENT.md](DEPLOYMENT.md).

## Tech stack

- Django 5 (Python 3.13), single project, two apps
- SQLite in development
- Plain Django templates, no frontend framework
- WhiteNoise for static files, Pillow for image uploads, gunicorn in production

## Running it locally

```
python3 -m venv venv
venv/bin/pip install -r requirements.txt
venv/bin/python manage.py migrate
venv/bin/python manage.py runserver
```

The site is then at http://localhost:8000.

### Test accounts

Seed one account for every stage of the recruitment flow (development only,
refuses to run in production):

```
venv/bin/python manage.py seed_test_users
```

Every account uses the password `testpass123`. The useful ones:

| Username | What you see |
| --- | --- |
| `test_new` | Applicant with no application yet |
| `test_submitted` | Application submitted, waiting on review |
| `test_accepted` | Accepted, has a promotion code to redeem |
| `test_onboarding` | Mid onboarding |
| `test_member` | Fully onboarded member dashboard |
| `lead_land` / `lead_sea` / `lead_air` / `lead_ops` | Team lead draft boards |
| `test_admin` | Superuser, sees every board and /admin/ |

Remove them again with `seed_test_users --delete`.

## Project layout

```
core/           Public site: pages, templates, static files, photos
recruitment/    Accounts, applications, draft boards, onboarding, member area
hfr_site/       Settings and URL routing
docs/           Extracted wireframe spec and open design decisions
private_media/  Applicant CVs (not web served; leads download through the app)
media/          Public uploads such as profile pictures
```

## How recruitment works

1. An applicant creates an account with their GUID email and submits one
   application: three team picks (first, alternative, wildcard), answers, and a
   PDF CV.
2. Team leads review applications on their division's draft boards: invite to
   interview, accept, or pass the applicant to their next pick.
3. On acceptance the lead gives the applicant a one time promotion code (after
   SRC membership is confirmed). Redeeming it promotes them to onboarding.
4. Onboarding collects display name, profile picture and contact preferences,
   then unlocks the member area.

The recruitment season is toggled in the admin under Recruitment settings.

## Tests

```
venv/bin/python manage.py test recruitment
```

## Deploying

See [DEPLOYMENT.md](DEPLOYMENT.md) for the launch checklist: required
environment variables, email setup for password resets, and the warning about
never shipping the development database.

## Design reference

The site follows the v2 wireframes. The hero video is `core/static/core/hero-loop.mp4`
(H.264 in an MP4 container, so it plays in Firefox too; the original QuickTime
export did not).

The extracted spec, including what is still
unbuilt (member events, tasks, objectives, member store) and the decisions the
committee still owes, lives in [docs/wireframe-spec.md](docs/wireframe-spec.md).
