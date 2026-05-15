# ai-infra-fund — project instructions

## Active deploy target: Azure cloud (always)

When the user says "deploy", "ship", "push it", "release", or any
synonym, the deploy target is **always the Azure cloud project**, never
local docker-compose, never a local-only smoke run.

Concretely, "deploy" in this repo means the full pipeline:

1. Commit changes locally.
2. Build Docker images for `api`, `worker`, `web`.
3. Push images to Azure Container Registry (ACR).
4. `kubectl apply` against the AKS cluster `aks-fund-rag` in resource
   group `rg-fund-rag`, namespace `ai-infra-fund`.
5. Roll the Azure App Service for the frontend
   (`ai-infra-fund-frontend.azurewebsites.net`) onto the new image.
6. Verify rollout (pods Ready, App Service Running, `/health` /
   `/ready` green).

This matches what the `deploy` skill already does — invoke that skill
unless the user explicitly asks for something else.

## Live cloud surface (canonical)

- **Frontend (canonical)**: https://ai-infra-fund-frontend.azurewebsites.net
- **Frontend (sibling, also CORS-allowed)**: https://fundrag-frontend.azurewebsites.net
- **AKS cluster**: `aks-fund-rag` (resource group `rg-fund-rag`)
- **Namespace**: `ai-infra-fund`
- **Container registry**: ACR in `rg-fund-rag`
- **Database**: PostgreSQL + pgvector StatefulSet inside the AKS namespace

CORS allowlist for the API lives at
`deploy/aks-ai-infra-fund.yaml:15`
(`AI_INFRA_FUND_CORS_ORIGINS`).

## Local stack is for development only

`docker compose up` and `scripts/compose_smoke.sh` are valid for local
testing, but they are **not** what "deploy" means. If the user wants a
local smoke run they will say "compose smoke", "local stack", or
"docker compose".

## Never leak the .env file

**Do not** read, print, summarize, paste into chat, copy into other
files, attach to PRs/commits, or send to remote tools the contents of:

- `.env`
- `.env.*` (e.g. `.env.local`, `.env.production`)
- any other untracked file containing real secrets

`.env.example` is **fine** — it's a tracked sample with no real values.
Real secrets stay in Kubernetes Secrets (`ai-infra-fund-db` and any
future secret resource) and Azure Key Vault, never in chat or git.

Specifically:

- Don't use `cat .env`, `Read /path/to/.env`, `grep` over `.env`, or
  any command that streams its contents to the conversation.
- If you need to know whether a key is set, ask the user, or check
  `kubectl get secret ... -o jsonpath='{.data | keys}'` (key names
  only, never values).
- If `.env` accidentally appears in a tool result, do not echo it
  back. Acknowledge the leak in one line and continue.
- Never `git add .env` or include it in a commit, even by accident.
  Prefer `git add <specific-files>` over `git add .` / `git add -A`.
