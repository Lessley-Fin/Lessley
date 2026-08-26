#!/usr/bin/env bash
#
# Seed the Lessley MongoDB with the reference collections.
#
# Imports users, mccs, clubs, stores, store_aliases and deals from a directory of
# <collection>.json files (JSON arrays), streaming each one into mongoimport inside
# the running mongodb container. See README.md → Seeding MongoDB for the data layout.
#
# Defaults for the credentials and database name are read from ./.env (DB_USER,
# DB_PASS, DB_NAME) when it exists, so on a configured checkout this is just:
#
#     ./seed-db.sh
#
# Usage:  ./seed-db.sh [options]
#   -u, --username USER     Mongo user            (default: DB_USER from .env, else guest)
#   -p, --password PASS     Mongo password        (default: DB_PASS from .env, else guest)
#   -d, --database NAME     Target database       (default: DB_NAME from .env, else lessley)
#   -f, --path DIR          Directory holding <collection>.json
#                                                 (default: ../lessley-deals/data/seed)
#   -c, --container NAME    Mongo container name  (default: mongodb)
#       --collections LIST  Comma-separated subset
#                                                 (default: every collection above)
#       --drop              Drop each collection before importing (destructive)
#       --insert            Plain inserts instead of upserts (fails on existing keys)
#       --env-file FILE     Read defaults from FILE  (default: ./.env)
#       --dry-run           Print what would run, change nothing
#   -h, --help              This help
#
# Re-running is safe by default: rows are upserted on their business key (id, or
# _id for users), so an existing row is updated instead of duplicated.
#
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# ── Collection table ─────────────────────────────────────────────────────────────
# Import order matters only for readability; each import is independent.
# The upsert key differs for users: ASP.NET Identity writes the account id as _id,
# while the scraping pipeline's exports keep the business key in id.
# store_aliases follows stores because every alias row points at one by store_id.
COLLECTION_ORDER=(users mccs clubs stores store_aliases deals)

upsert_field_for() {
    case "$1" in
        users) printf '_id' ;;
        *)     printf 'id'  ;;
    esac
}

# ── Defaults ─────────────────────────────────────────────────────────────────────
ENV_FILE="$SCRIPT_DIR/.env"
DATA_DIR=""
CONTAINER="mongodb"
DB_USERNAME=""
DB_PASSWORD=""
DB_DATABASE=""
COLLECTIONS=""
DROP=0
MODE="upsert"
DRY_RUN=0

usage() {
    # Anchored on `set -euo pipefail` rather than a fixed line range, so editing
    # the header block above cannot silently truncate (or overrun) --help.
    sed -n '3,/^set -euo pipefail$/p' "${BASH_SOURCE[0]}" \
        | sed -e '$d' -e 's/^#\{1,\} \{0,1\}//' -e 's/^#$//'
}

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

# Read one KEY from a dotenv file, stripping an inline "  # comment" and any
# surrounding quotes. Returns empty when the file or the key is absent.
env_value() {
    local key="$1" file="$2" line
    [[ -f "$file" ]] || return 0
    line="$(grep -E "^[[:space:]]*${key}=" "$file" | tail -n 1 || true)"
    [[ -n "$line" ]] || return 0
    line="${line#*=}"
    line="$(printf '%s' "$line" | sed -E 's/[[:space:]]+#.*$//; s/^[[:space:]]+//; s/[[:space:]]+$//')"
    line="${line%\"}"; line="${line#\"}"
    line="${line%\'}"; line="${line#\'}"
    printf '%s' "$line"
}

# ── Arguments ────────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        -u|--username)  DB_USERNAME="${2:?--username needs a value}";     shift 2 ;;
        -p|--password)  DB_PASSWORD="${2:?--password needs a value}";     shift 2 ;;
        -d|--database)  DB_DATABASE="${2:?--database needs a value}";     shift 2 ;;
        -f|--path)      DATA_DIR="${2:?--path needs a value}";            shift 2 ;;
        -c|--container) CONTAINER="${2:?--container needs a value}";      shift 2 ;;
        --collections)  COLLECTIONS="${2:?--collections needs a value}";  shift 2 ;;
        --env-file)     ENV_FILE="${2:?--env-file needs a value}";        shift 2 ;;
        --drop)         DROP=1;         shift ;;
        --insert)       MODE="insert";  shift ;;
        --dry-run)      DRY_RUN=1;      shift ;;
        -h|--help)      usage; exit 0 ;;
        *)              die "unknown option: $1 (try --help)" ;;
    esac
done

# .env fills in whatever was not passed explicitly.
[[ -n "$DB_USERNAME" ]] || DB_USERNAME="$(env_value DB_USER "$ENV_FILE")"
[[ -n "$DB_PASSWORD" ]] || DB_PASSWORD="$(env_value DB_PASS "$ENV_FILE")"
[[ -n "$DB_DATABASE" ]] || DB_DATABASE="$(env_value DB_NAME "$ENV_FILE")"
[[ -n "$DB_USERNAME" ]] || DB_USERNAME="guest"
[[ -n "$DB_PASSWORD" ]] || DB_PASSWORD="guest"
[[ -n "$DB_DATABASE" ]] || DB_DATABASE="lessley"
[[ -n "$DATA_DIR"    ]] || DATA_DIR="$SCRIPT_DIR/../lessley-deals/data/seed"

[[ -d "$DATA_DIR" ]] || die "seed directory not found: $DATA_DIR (pass --path)"
DATA_DIR="$(cd -- "$DATA_DIR" && pwd)"

# Requested subset, validated against the table above so a typo fails loudly
# instead of quietly seeding nothing.
selected=()
if [[ -n "$COLLECTIONS" ]]; then
    IFS=',' read -r -a requested <<< "$COLLECTIONS"
    for want in "${requested[@]}"; do
        want="$(printf '%s' "$want" | tr -d '[:space:]')"
        [[ -n "$want" ]] || continue
        known=0
        for col in "${COLLECTION_ORDER[@]}"; do
            if [[ "$col" == "$want" ]]; then known=1; break; fi
        done
        (( known )) || die "unknown collection: $want (known: ${COLLECTION_ORDER[*]})"
        selected+=("$want")
    done
    [[ ${#selected[@]} -gt 0 ]] || die "--collections was empty"
else
    selected=("${COLLECTION_ORDER[@]}")
fi

# ── Preflight ────────────────────────────────────────────────────────────────────
command -v docker >/dev/null 2>&1 || die "docker not found on PATH"
if [[ $DRY_RUN -eq 0 ]]; then
    docker inspect --format '{{.State.Running}}' "$CONTAINER" 2>/dev/null | grep -q true \
        || die "container '$CONTAINER' is not running (start it with: docker compose up -d mongodb)"
fi

drop_note=""
(( DROP )) && drop_note=" (drop first)"
printf 'Seeding %s on container %s from %s\n' "$DB_DATABASE" "$CONTAINER" "$DATA_DIR"
printf 'User: %s   Mode: %s%s\n\n' "$DB_USERNAME" "$MODE" "$drop_note"

imported=0
skipped=()
failed=()

for collection in "${selected[@]}"; do
    file="$DATA_DIR/$collection.json"
    if [[ ! -f "$file" ]]; then
        printf '  ~ %-13s no %s.json in %s — skipped\n' "$collection" "$collection" "$DATA_DIR"
        skipped+=("$collection")
        continue
    fi

    printf '  > %-13s %s\n' "$collection" "$file"

    # Streamed on stdin rather than `docker cp`-ed to a temp file and read with
    # --file: no copy, no cleanup, and no absolute in-container path for MSYS
    # (Git Bash on Windows) to rewrite into a Windows path the container cannot
    # open. mongoimport reads stdin whenever --file is absent.
    args=(mongoimport
          --db "$DB_DATABASE"
          --collection "$collection"
          --jsonArray
          --username "$DB_USERNAME"
          --password "$DB_PASSWORD"
          --authenticationDatabase admin)
    # --drop already guarantees an empty collection, so upserting on top of it
    # would only cost a lookup per row.
    if (( DROP )); then
        args+=(--drop)
    elif [[ "$MODE" == "upsert" ]]; then
        args+=(--mode=upsert "--upsertFields=$(upsert_field_for "$collection")")
    fi

    ok=1
    if [[ $DRY_RUN -eq 1 ]]; then
        printf '  [dry-run] docker exec -i %s %s < %s\n' "$CONTAINER" "${args[*]}" "$file"
    else
        docker exec -i "$CONTAINER" "${args[@]}" < "$file" || ok=0
    fi

    if (( ok )); then
        imported=$((imported + 1))
    else
        printf '  ! %-13s import failed\n' "$collection"
        failed+=("$collection")
    fi
done

printf '\nImported %d collection(s).' "$imported"
[[ ${#skipped[@]} -gt 0 ]] && printf ' Skipped (no file): %s.' "${skipped[*]}"
[[ ${#failed[@]}  -gt 0 ]] && printf ' Failed: %s.' "${failed[*]}"
printf '\n'

[[ ${#failed[@]} -eq 0 ]] || exit 1
