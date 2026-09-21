# Operations runbook — Interview Prep Kit

Commands below have been exercised locally (verify, compose build, terraform
validate) or are the documented production path (deploy/rollback/snapshot).

## Local: quality gate

```bash
npm run setup
npm run web:install
npm run verify
```

`verify` runs API tests, web typecheck + tests (including the OpenAPI drift
check), and high-severity dependency audits. It fails the build on any of those.

## Local: production composition

```bash
cp .env.example .env   # fill GEMINI_API_KEY, ALLOWED_ORIGINS; set ENV=production
# For a local prod-shaped run without real AWS:
docker compose -f infra/deploy/docker-compose.prod.yml --project-directory . up -d --build
curl -fsS http://127.0.0.1/api/health/live
curl -fsS http://127.0.0.1/api/health/ready
```

Stop with `docker compose -f infra/deploy/docker-compose.prod.yml --project-directory . down`.

## Infrastructure (Terraform)

State is local and gitignored. Secrets are never in Terraform.

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars   # edit my_ip, key, repo_url, budget_email
terraform init
terraform validate
terraform plan
terraform apply
```

Outputs: `ec2_ip`, `cloudfront_url`. Point Vercel `API_ORIGIN` at `cloudfront_url`
and set `ALLOWED_ORIGINS` on the instance to the Vercel origin.

## Secrets on the instance

```bash
scp -i $SSH_KEY .env.prod ubuntu@$EC2_HOST:trao/.env
ssh -i $SSH_KEY ubuntu@$EC2_HOST 'chmod 600 ~/trao/.env'
```

Never commit `.env` / `.env.prod` / `*.tfstate` / `terraform.tfvars`.

## Deploy / rollback

```bash
EC2_HOST=<eip> SSH_KEY=~/.ssh/id_ed25519 ./infra/deploy/deploy.sh
EC2_HOST=<eip> SSH_KEY=~/.ssh/id_ed25519 ./infra/deploy/rollback.sh
```

Deploy records the previous git SHA in `.previous-release` on the instance;
rollback checks that SHA out and rebuilds the composition.

## Create a user (registration is closed by default)

```bash
# local
npm run users:create -- --email you@x.co --password '…'
# on the instance
docker compose -f infra/deploy/docker-compose.prod.yml --project-directory ~/trao \
  exec api python -m app.cli.create_user --email you@x.co --password '…'
```

## Rotate the model key

1. Create a new Gemini key; update `.env` on the instance (`GEMINI_API_KEY=…`).
2. `docker compose -f infra/deploy/docker-compose.prod.yml --project-directory ~/trao up -d api`
3. Confirm `GET /api/health/ready` is green; revoke the old key.

## Logs

```bash
ssh ubuntu@$EC2_HOST 'cd ~/trao && docker compose -f infra/deploy/docker-compose.prod.yml logs -f --tail=200 api'
```

Logs are structured JSON on stdout (`request_id`, `job_id`, `trace_id`). Match an
error response's `trace_id` to a log line.

## Backup and restore (Mongo data volume)

Daily snapshots are configured by the Terraform DLM policy on the `trao-mongo`
volume (7-day retention).

**Restore (exercised once against a throwaway volume):**

1. Create a volume from the chosen snapshot in the same AZ as the instance.
2. Stop the composition: `docker compose … stop mongo api`
3. Unmount `/var/lib/trao-mongo`, attach the restored volume, mount it.
4. Start mongo then api; confirm readiness and that a known Kit is present.

## Known topology limits

- Single EC2 instance (in-process worker).
- CloudFront → EC2 is HTTP on port 80 (HTTPS only at the front door).
- DNS-rebinding window between URL-guard check and connect remains.
- No hosted CI — `npm run verify` is the gate.
