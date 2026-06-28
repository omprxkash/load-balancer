#!/bin/bash
# First-time setup. Run once before `make up`.
set -e

echo "=== Checking prerequisites ==="

check_cmd() {
  if command -v "$1" &>/dev/null; then
    echo "  [OK] $1 ($(command -v $1))"
  else
    echo "  [MISSING] $1 — $2"
    MISSING=1
  fi
}

check_cmd docker    "Install Docker Desktop: https://www.docker.com/products/docker-desktop/"
check_cmd kubectl   "Comes with Docker Desktop (enable in settings)"
check_cmd git       "Install Git: https://git-scm.com/"
check_cmd python3   "Install Python 3.12: https://www.python.org/"
check_cmd kind      "Install kind: winget install Kubernetes.kind OR https://kind.sigs.k8s.io/"
check_cmd gh        "Install GitHub CLI: winget install GitHub.cli (optional, for git push)"

if [ "${MISSING}" = "1" ]; then
  echo ""
  echo "Please install missing tools and re-run this script."
  exit 1
fi

echo ""
echo "=== Configuring git hooks ==="
git config core.hooksPath .githooks && echo "  [OK] core.hooksPath set to .githooks"

echo ""
echo "=== Copying .env.example to .env ==="
cp -n .env.example .env && echo "  Created .env" || echo "  .env already exists"

echo ""
echo "=== Prerequisites OK. Run 'make up' to start the stack. ==="
