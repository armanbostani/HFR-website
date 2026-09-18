# Deploying the HFR website

Everything below assumes the code is on the server (or PaaS) with Python 3.12+
and the dependencies from `requirements.txt` installed.

## 1. Environment variables (required)

| Variable | What to set |
| --- | --- |
| `DJANGO_SECRET_KEY` | A long random string. Generate one with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`. The site refuses to start in production with the dev key. |
| `DJANGO_DEBUG` | `0` |
| `DJANGO_ALLOWED_HOSTS` | The domain(s), comma separated, e.g. `hfr.gla.ac.uk,www.hfr.gla.ac.uk` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Same domains with scheme, e.g. `https://hfr.gla.ac.uk` |
| `HFR_CONTACT_EMAIL` | The society inbox the public site points people at (store orders, sponsorship, donations). Defaults to `hfr@glasgow.ac.uk`; **check that address actually exists before launch.** |

## 2. Email (required for password resets)

| Variable | What to set |
| --- | --- |
| `DJANGO_EMAIL_HOST` | SMTP server |
| `DJANGO_EMAIL_PORT` | Usually `587` (default) |
| `DJANGO_EMAIL_USER` / `DJANGO_EMAIL_PASSWORD` | SMTP credentials |
| `DJANGO_DEFAULT_FROM_EMAIL` | e.g. `HFR <hfr@glasgow.ac.uk>` (default) |

In development no setup is needed; reset emails print to the runserver console.

## 3. Members' forum (optional, Discourse)

Leave both variables unset until the forum is live and the site shows nothing
about it. Set `HFR_FORUM_URL` and members get a Forum entry in their account
menu, a panel on their dashboard and a `/forum/` link that sends them there
(applicants and visitors are turned away).

| Variable | What to set |
| --- | --- |
| `HFR_FORUM_URL` | The forum's address, e.g. `https://forum.hfr.gla.ac.uk` |
| `HFR_DISCOURSE_CONNECT_SECRET` | A long random string, the same one entered in Discourse. Turns on single sign-on. |

With the secret set, the site is the forum's identity provider
(DiscourseConnect): members log in to the forum with their website account,
nobody needs a second signup, and only onboarded members and team leads can
get in. In the Discourse admin, under Settings → Login:

- `enable discourse connect`: on
- `discourse connect url`: `https://<website domain>/forum/sso/`
- `discourse connect secret`: the same value as `HFR_DISCOURSE_CONNECT_SECRET`
- `discourse connect overrides email`, `... username`, `... name`: on (optional, keeps profiles in step)

On each sign-in the site also asks Discourse to add the member to groups
named after their division (`land`, `sea`, `air`, `operations`), `team-leads`
for leads and `exec` for staff accounts. Create those groups on the forum
(exact names) and category permissions can hang off them; group names the
forum doesn't know are ignored.

## 4. First deploy

```
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
gunicorn hfr_site.wsgi
```

## 5. Before opening the doors

- **Never reuse the development `db.sqlite3`.** It contains test accounts
  (including a superuser) with a public password. Start from a fresh database,
  or if one was ever copied across, run `python manage.py seed_test_users --delete`.
  The seed command itself refuses to run when `DEBUG` is off.
- In the admin, set **Recruitment settings**: the open/closed toggle and the
  (informational) close date shown on the register page.
- Check **Teams** in the admin. `migrate` seeds the sub-team structure
  (Land, Sea, Air, Operations) and the division pages list whatever is there,
  so rename, reorder or switch off recruiting for any team without a deploy.
  Air's UGA-led teams are listed but don't recruit through this site.
- Check the file storage locations `media/` (public: avatars) and
  `private_media/` (applicant CVs, served only to team leads through the app)
  are on a persistent disk and included in backups, along with the database.

## 6. Sanity checks

```
DJANGO_DEBUG=0 DJANGO_SECRET_KEY=<key> python manage.py check --deploy
```

Expect no errors. W004/W008 style warnings about HSTS and SSL redirect should
be gone; the hardening switches on automatically when `DJANGO_DEBUG=0`.
