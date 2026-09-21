#!/usr/bin/env bash
# First-time install of the HFR website on a fresh Ubuntu 22.04/24.04 server.
# Run as root:  bash install.sh <domain> <git-url> [branch]
# Safe to re-run: every step is idempotent.
#
# Before running you need:
#   1. DNS A records for <domain> and www.<domain> pointing at this server
#   2. /etc/hfr-website.env filled in (copy deploy/hfr-website.env.example)
#      -- the script creates it from the example if missing and stops so you can edit it.
set -euo pipefail

DOMAIN=${1:?usage: install.sh <domain> <git-url> [branch]}
REPO=${2:?usage: install.sh <domain> <git-url> [branch]}
BRANCH=${3:-main}
ROOT=/srv/hfr-website
APP=$ROOT/app

echo "== packages"
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip git nginx certbot python3-certbot-nginx sqlite3 ufw

echo "== firewall"
ufw allow OpenSSH >/dev/null
ufw allow 'Nginx Full' >/dev/null
ufw --force enable >/dev/null

echo "== service user and folders"
id -u hfr >/dev/null 2>&1 || useradd --system --create-home --home-dir $ROOT --shell /usr/sbin/nologin hfr
mkdir -p $ROOT/media $ROOT/private_media $ROOT/backups
chown -R hfr:www-data $ROOT
chmod 750 $ROOT/private_media

echo "== code"
if [ -d $APP/.git ]; then
    sudo -u hfr git -C $APP fetch -q origin
    sudo -u hfr git -C $APP checkout -q $BRANCH
    sudo -u hfr git -C $APP pull -q --ff-only origin $BRANCH
else
    sudo -u hfr git clone -q --branch $BRANCH $REPO $APP
fi
# uploads live outside the checkout so a redeploy never touches them
sudo -u hfr ln -sfn $ROOT/media $APP/media
sudo -u hfr ln -sfn $ROOT/private_media $APP/private_media

echo "== python"
[ -d $APP/venv ] || sudo -u hfr python3 -m venv $APP/venv
sudo -u hfr $APP/venv/bin/pip install -q --upgrade pip
sudo -u hfr $APP/venv/bin/pip install -q -r $APP/requirements.txt

echo "== environment file"
if [ ! -f /etc/hfr-website.env ]; then
    cp $APP/deploy/hfr-website.env.example /etc/hfr-website.env
    chmod 600 /etc/hfr-website.env
    KEY=$($APP/venv/bin/python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
    sed -i "s|^DJANGO_SECRET_KEY=.*|DJANGO_SECRET_KEY=$KEY|" /etc/hfr-website.env
    sed -i "s|example\.org|$DOMAIN|g" /etc/hfr-website.env
    echo
    echo "Created /etc/hfr-website.env with a fresh secret key and $DOMAIN filled in."
    echo "Edit it now (contact email, SMTP user/password), then re-run this script."
    exit 0
fi

echo "== django"
set -a; . /etc/hfr-website.env; set +a
sudo -u hfr --preserve-env=DJANGO_SECRET_KEY,DJANGO_DEBUG,DJANGO_ALLOWED_HOSTS,DJANGO_CSRF_TRUSTED_ORIGINS \
    $APP/venv/bin/python $APP/manage.py migrate --noinput
sudo -u hfr --preserve-env=DJANGO_SECRET_KEY,DJANGO_DEBUG,DJANGO_ALLOWED_HOSTS,DJANGO_CSRF_TRUSTED_ORIGINS \
    $APP/venv/bin/python $APP/manage.py collectstatic --noinput -v 0
sudo -u hfr --preserve-env=DJANGO_SECRET_KEY,DJANGO_DEBUG,DJANGO_ALLOWED_HOSTS,DJANGO_CSRF_TRUSTED_ORIGINS \
    $APP/venv/bin/python $APP/manage.py check --deploy

echo "== systemd"
cp $APP/deploy/systemd/hfr-website.service /etc/systemd/system/
cp $APP/deploy/systemd/hfr-backup.service /etc/systemd/system/
cp $APP/deploy/systemd/hfr-backup.timer /etc/systemd/system/
chmod +x $APP/deploy/backup.sh $APP/deploy/update.sh
systemctl daemon-reload
systemctl enable --now hfr-website hfr-backup.timer
systemctl restart hfr-website

echo "== nginx"
sed "s/__DOMAIN__/$DOMAIN/g" $APP/deploy/nginx/hfr-website.conf > /etc/nginx/sites-available/hfr-website
ln -sfn /etc/nginx/sites-available/hfr-website /etc/nginx/sites-enabled/hfr-website
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo "== https"
if [ ! -d /etc/letsencrypt/live/$DOMAIN ]; then
    certbot --nginx --non-interactive --agree-tos --redirect \
        -m "${HFR_CONTACT_EMAIL:-admin@$DOMAIN}" -d "$DOMAIN" -d "www.$DOMAIN"
fi

echo
echo "Done. Site: https://$DOMAIN"
echo "Next: create the admin account:"
echo "  sudo -u hfr bash -c 'set -a; . /etc/hfr-website.env; $APP/venv/bin/python $APP/manage.py createsuperuser'"
