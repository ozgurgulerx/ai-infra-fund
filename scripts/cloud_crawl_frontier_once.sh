#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${AI_INFRA_FUND_K8S_NAMESPACE:-ai-infra-fund}"
CRONJOB="${AI_INFRA_FUND_CRAWL_CRONJOB:-ai-infra-fund-crawl-frontier}"
JOB_NAME="${AI_INFRA_FUND_CRAWL_JOB_NAME:-${CRONJOB}-manual-$(date +%Y%m%d%H%M%S)}"
TIMEOUT="${AI_INFRA_FUND_CRAWL_JOB_TIMEOUT:-900s}"

kubectl -n "${NAMESPACE}" create job "${JOB_NAME}" --from=cronjob/"${CRONJOB}"
kubectl -n "${NAMESPACE}" wait --for=condition=complete "job/${JOB_NAME}" --timeout="${TIMEOUT}"
kubectl -n "${NAMESPACE}" logs "job/${JOB_NAME}" --all-containers=true
