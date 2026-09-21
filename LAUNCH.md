# Launch runbook

Everything you need to take the site from this repo to a live domain, in
order. The `deploy/` folder holds the server config; `install.sh` applies it.
Assumes a fresh Ubuntu 22.04 or 24.04 VPS with root SSH. Anything else
(shared hosting, a PaaS) needs a different route; ask before improvising.

## 1. Things only a human can do

| Step | Where | Notes |
| --- | --- | --- |
| Register the domain | Cloudflare Registrar or Porkbun | Under the **society** account, 2FA on, auto-renew on |
| Point DNS at the server | Registrar's DNS panel | `A  @  <server IP>` and `A  www  <server IP>`. DNS-only, no proxy |
| Have a society email that receives mail | Google Workspace / Outlook / registrar mailbox | Goes in `HFR_CONTACT_EMAIL`; the shop and sponsor pages mail it |
| Get SMTP credentials for outgoing mail | Brevo (free tier) or the mailbox provider | Needed for password resets. Verify the sending domain there |
| Merge `launch-prep` into `main` | GitHub | The server pulls from GitHub |

## 2. Install (about 10 minutes)

SSH in as root and run:

```bash
apt-get install -y git
git clone https://github.com/22ishaq/HFR-website.git /tmp/hfr && \
bash /tmp/hfr/deploy/install.sh <domain> https://github.com/22ishaq/HFR-website.git main
```

The first run stops after writing `/etc/hfr-website.env`. Open it, fill in
the contact email and SMTP user/password, then run the same command again.
The second run migrates, collects static files, starts gunicorn under
systemd, configures nginx and gets a Let's Encrypt certificate.

Then create the admin account:

```bash
sudo -u hfr bash -c 'set -a; . /etc/hfr-website.env; /srv/hfr-website/app/venv/bin/python /srv/hfr-website/app/manage.py createsuperuser'
```

## 3. Before opening recruitment

- Log in at `https://<domain>/admin/`.
- **Recruitment settings**: open, close date set.
- **Teams**: check names, taglines, recruiting toggles, and add each team lead
  under Leads (leads must have an account first: they sign up like anyone
  else, then you set their Profile role to "Onboarded HFR member" in the admin).
- Send yourself a password reset from `/accounts/password-reset/` and confirm
  the email arrives, not in spam.
- Submit one real test application from a phone, download the CV from the
  lead dashboard, accept it, redeem the code, complete onboarding. Then
  delete that account in the admin.
- Check `https://<domain>` on a phone on mobile data: hero video plays, menu
  opens, division pages show the sub-team grids.

## 4. Day to day

- **Deploy a change:** merge to `main`, then on the server
  `/srv/hfr-website/app/deploy/update.sh`. It takes a backup first.
- **Backups:** nightly at 03:30 to `/srv/hfr-website/backups` (database,
  avatars, CVs), 30 days kept. Copy that folder off the server too;
  `rclone` to the society Drive is the simplest.
- **Logs:** `journalctl -u hfr-website -f`.
- **Restore:** stop the service, copy a `db_*.sqlite3` over
  `/srv/hfr-website/app/db.sqlite3`, untar `files_*.tar.gz` into
  `/srv/hfr-website/`, start the service.

## 5. Where things live on the server

```
/srv/hfr-website/app/            git checkout, venv, db.sqlite3
/srv/hfr-website/media/          avatars (public)
/srv/hfr-website/private_media/  applicant CVs (never web-served)
/srv/hfr-website/backups/        nightly snapshots
/etc/hfr-website.env             secrets, root-only
/etc/nginx/sites-available/hfr-website
/etc/systemd/system/hfr-website.service, hfr-backup.timer
```
