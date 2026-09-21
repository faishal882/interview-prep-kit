#!/usr/bin/env bash
# Deploy the current repository tip to the EC2 instance.
# Usage: EC2_HOST=… SSH_KEY=… ./infra/deploy/deploy.sh
set -euo pipefail

HOST="${EC2_HOST:?set EC2_HOST to the instance Elastic IP or DNS}"
KEY="${SSH_KEY:-$HOME/.ssh/id_ed25519}"
REMOTE_DIR="${REMOTE_DIR:-/home/ubuntu/trao}"
SSH=(ssh -i "$KEY" -o StrictHostKeyChecking=accept-new "ubuntu@$HOST")

echo "==> recording previous release SHA for rollback"
PREV="$("${SSH[@]}" "cd '$REMOTE_DIR' && git rev-parse HEAD 2>/dev/null || echo none")"
echo "$PREV" | "${SSH[@]}" "cat > '$REMOTE_DIR/.previous-release'"

echo "==> syncing repository"
"${SSH[@]}" "cd '$REMOTE_DIR' && git fetch --all --prune && git reset --hard origin/master || git reset --hard origin/main"

echo "==> ensuring .env exists (secrets stay on the instance)"
"${SSH[@]}" "test -f '$REMOTE_DIR/.env' || (echo 'missing .env — scp your .env.prod there first' >&2; exit 1)"
"${SSH[@]}" "chmod 600 '$REMOTE_DIR/.env'"

echo "==> building and starting production composition"
"${SSH[@]}" "cd '$REMOTE_DIR' && docker compose -f infra/deploy/docker-compose.prod.yml --project-directory '$REMOTE_DIR' up -d --build"

echo "==> waiting for readiness"
for i in $(seq 1 30); do
  if curl -fsS "http://$HOST/api/health/ready" >/dev/null 2>&1; then
    echo "ready"
    exit 0
  fi
  sleep 2
done
echo "deploy finished but readiness not yet green — check logs" >&2
exit 1
