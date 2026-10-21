#!/usr/bin/env bash
# Create the private repository on Gitea (if it does not exist yet) and push the current branch to it as main.
#
# Usage:  GITEA_TOKEN=... bash scripts/publish_to_gitea.sh
# Options (environment variables): GITEA_URL (default https://gitea.nessar.fr), REPO_NAME (default AWS-CERTIF),
#                                  BRANCH (default main)
# The token is read from the environment, never printed, and never written to the git configuration.
set -euo pipefail

GITEA_URL="${GITEA_URL:-https://gitea.nessar.fr}"
REPO_NAME="${REPO_NAME:-AWS-CERTIF}"
BRANCH="${BRANCH:-main}"
: "${GITEA_TOKEN:?set GITEA_TOKEN to a Gitea access token with repository write access}"

api() {
  curl -sS --fail -H "Authorization: token ${GITEA_TOKEN}" -H "Content-Type: application/json" "$@"
}

owner=$(api "${GITEA_URL}/api/v1/user" | python3 -c 'import json, sys; print(json.load(sys.stdin)["login"])')
echo "Gitea user: ${owner}"

if api -o /dev/null "${GITEA_URL}/api/v1/repos/${owner}/${REPO_NAME}" 2>/dev/null; then
  echo "Repository ${owner}/${REPO_NAME} already exists."
else
  payload=$(python3 -c 'import json, sys; print(json.dumps({"name": sys.argv[1], "private": True,
    "description": "AWS DVA-C02 study repository: book, awslings exercises, question bank, labs, tutor"}))' "${REPO_NAME}")
  api -X POST "${GITEA_URL}/api/v1/user/repos" -d "${payload}" -o /dev/null
  echo "Created private repository ${owner}/${REPO_NAME}."
fi

# Pass the credentials as an HTTP header through environment variables (git >= 2.31), so they appear
# neither in the remote URL, nor in .git/config, nor in the process list.
auth=$(printf '%s:%s' "${owner}" "${GITEA_TOKEN}" | base64 | tr -d '\n')
GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=http.extraHeader GIT_CONFIG_VALUE_0="Authorization: Basic ${auth}" \
  git push "${GITEA_URL}/${owner}/${REPO_NAME}.git" "HEAD:refs/heads/${BRANCH}"
echo "Pushed to ${GITEA_URL}/${owner}/${REPO_NAME} (branch ${BRANCH})."
