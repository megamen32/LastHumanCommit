#!/bin/sh
# Reload only the LHC certificate consumer after a successful renewal.
set -eu
[ "${RENEWED_LINEAGE:-}" = /etc/letsencrypt/live/lhc.bezrabotnyi.com ] || exit 0
/usr/sbin/nginx -t
/bin/systemctl reload nginx
