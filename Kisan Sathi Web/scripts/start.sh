#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
COMPOSE="$ROOT/deploy/compose.yaml"
ENV_ARGS=""
if [ -f "$ROOT/deploy/.env" ]; then
  ENV_ARGS="--env-file $ROOT/deploy/.env"
fi

python "$ROOT/scripts/health_check.py" --compose "$COMPOSE" --config-only
if [ "${1:-}" = "down" ]; then
  # shellcheck disable=SC2086
  docker compose $ENV_ARGS -f "$COMPOSE" down
  exit 0
fi
if [ "${1:-}" = "build" ]; then
  # shellcheck disable=SC2086
  docker compose $ENV_ARGS -f "$COMPOSE" build
fi
# shellcheck disable=SC2086
docker compose $ENV_ARGS -f "$COMPOSE" up -d
# shellcheck disable=SC2086
docker compose $ENV_ARGS -f "$COMPOSE" ps
