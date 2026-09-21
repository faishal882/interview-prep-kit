#!/usr/bin/env bash
# Roll back to the SHA recorded by the previous deploy.sh run.
# Usage: EC2_HOST=… SSH_KEY=… ./infra/deploy/rollback.sh
set -euo pipefail

HOST="${EC2_HOST:?set EC2_HOST to the instance Elastic IP or DNS}"
KEY="${SSH_KEY:-$HOME/.ssh/id_ed25519}"
REMOTE_DIR="${REMOTE_DIR:-/home/ubuntu/trao}"
SSH=(ssh -i "$KEY" -o StrictHostKeyChecking=accept-new "ubuntu@$HOST")

PREV="$("${SSH[@]}" "cat '$REMOTE_DIR/.previous-release")"
if [ -z "$PREV" ] || [ "$PREV" = "none" ]; then
  echo "no previous release recorded" >&2
  exit 1
fi

echo "==> rolling back to $PREV"
"${SSH[@]}" "cd '$REMOTE_DIR' && git checkout --force '$PREV'"
"${SSH[@]}" "cd '$REMOTE_DIR' && docker compose -f infra/deploy/docker-compose.prod.yml --project-directory '$REMOTE_DIR' up -d --build"

echo "==> waiting for readiness"
for i in $(seq 1 30); do
  if curl -fsS "http://$HOST/api/health/ready" >/dev/null 2>&1; then
    echo "rollback ready at $PREV"
    exit 0
  fi
  sleep 2
done
echo "rollback finished but readiness not yet green" >&2
exit 1
