#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
BASE_COMPOSE="$ROOT/deploy/compose.yaml"
PROTOTYPE_COMPOSE="$ROOT/deploy/compose.prototype.yaml"
ENV_ARGS=""
if [ -f "$ROOT/deploy/.env" ]; then
  ENV_ARGS="--env-file $ROOT/deploy/.env"
fi

python "$ROOT/scripts/validate_prototype_models.py"
python "$ROOT/scripts/validate_prototype_models.py" \
  --registry "$ROOT/models/crop_disease/registry.prototype.json" \
  --root "$ROOT/models/candidates"
python "$ROOT/scripts/health_check.py" --compose "$BASE_COMPOSE" --config-only

if [ "${1:-}" = "down" ]; then
  # shellcheck disable=SC2086
  docker compose $ENV_ARGS -f "$BASE_COMPOSE" -f "$PROTOTYPE_COMPOSE" down
  exit 0
fi
if [ "${1:-}" = "build" ]; then
  # shellcheck disable=SC2086
  docker compose $ENV_ARGS -f "$BASE_COMPOSE" -f "$PROTOTYPE_COMPOSE" build
fi
# shellcheck disable=SC2086
docker compose $ENV_ARGS -f "$BASE_COMPOSE" -f "$PROTOTYPE_COMPOSE" up -d
# shellcheck disable=SC2086
docker compose $ENV_ARGS -f "$BASE_COMPOSE" -f "$PROTOTYPE_COMPOSE" ps
