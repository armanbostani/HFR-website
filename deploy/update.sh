#!/usr/bin/env bash
# Redeploy after a push: pull, install, migrate, collect static, restart.
# Run as root:  /srv/hfr-website/app/deploy/update.sh [branch]
set -euo pipefail

APP=/srv/hfr-website/app
# git must run as hfr: the checkout is hfr-owned and git refuses root ("dubious ownership")
BRANCH=${1:-$(sudo -u hfr git -C $APP rev-parse --abbrev-ref HEAD)}
set -a; . /etc/hfr-website.env; set +a
RUN="sudo -u hfr --preserve-env=DJANGO_SECRET_KEY,DJANGO_DEBUG,DJANGO_ALLOWED_HOSTS,DJANGO_CSRF_TRUSTED_ORIGINS"

sudo -u hfr $APP/deploy/backup.sh >/dev/null && echo "backup taken"
sudo -u hfr git -C $APP fetch -q origin
sudo -u hfr git -C $APP checkout -q $BRANCH
sudo -u hfr git -C $APP pull -q --ff-only origin $BRANCH
$RUN $APP/venv/bin/pip install -q -r $APP/requirements.txt
$RUN $APP/venv/bin/python $APP/manage.py migrate --noinput
$RUN $APP/venv/bin/python $APP/manage.py collectstatic --noinput -v 0
systemctl restart hfr-website
systemctl --no-pager --lines=5 status hfr-website
echo "deployed $(sudo -u hfr git -C $APP log -1 --format='%h %s')"
