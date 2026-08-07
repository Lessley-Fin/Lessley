"""Seeding the canonical stores/aliases/clubs into MongoDB from the seed files.

Lives here rather than in the CLI because both entry points need it: the CLI
builds repositories for one-off commands, and the worker's composition root
(:mod:`lessley_deals.pipeline.factory`) builds them for the scheduled pipeline.
Without stores in the database the match stage has nothing to resolve against,
so every scraped record lands in NO_MATCH — a silent failure that looks like a
scraper bug.

Idempotent throughout: every write is ``$setOnInsert``, so re-running never
overwrites a store that has since been edited or enriched.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Fallback only. The canonical list is data/seed/clubs.json — a club is needed
# for every registered source, because PersistStage stamps Deal.club_id from a
# source_id → club_id map (persist_stage.py), so a source with no club silently
# produces deals with club_id = None. Keeping the list in a seed file means
# adding a scraper doesn't require a code change here.
CLUBS: list[dict[str, Any]] = [
    {"_id": "club_hot",        "name": "HOT Israel",        "source_id": "hot",        "description": "HOT Israel — cable TV & internet member benefits", "metadata": {}, "stores": []},
    {"_id": "club_mastercard", "name": "Mastercard Israel", "source_id": "mastercard", "description": "Mastercard Israel credit card benefits",            "metadata": {}, "stores": []},
    {"_id": "club_topcash",    "name": "Isracard TopCash",  "source_id": "topcash",    "description": "Isracard TopCash cashback benefits",                "metadata": {}, "stores": []},
    {"_id": "club_behatsdaa",  "name": "Behatsdaa",         "source_id": "behatsdaa",  "description": "Behatsdaa deals aggregator",                        "metadata": {}, "stores": []},
]


def load_clubs(data_dir: str | Path = "data") -> list[dict[str, Any]]:
    """Clubs from ``seed/clubs.json``, falling back to the built-in list."""
    for seed_dir in seed_candidate_dirs(data_dir):
        path = seed_dir / "clubs.json"
        if path.exists():
            clubs = json.loads(path.read_text(encoding="utf-8"))
            return [
                {**{k: v for k, v in club.items() if k != "id"}, "_id": club.get("id") or club.get("_id")}
                for club in clubs
            ]
    logger.warning("No seed/clubs.json found — falling back to the %d built-in clubs", len(CLUBS))
    return CLUBS


def upsert_seed_file(db: Any, collection: str, path: Path) -> int:
    """Upsert every record in ``path`` into ``collection``; return how many were new."""
    if not path.exists():
        return 0
    items = json.loads(path.read_text(encoding="utf-8"))
    inserted = 0
    for item in items:
        doc = dict(item)
        doc_id = doc.pop("id", None) or doc.pop("_id", None)
        doc["_id"] = doc_id
        result = db[collection].update_one({"_id": doc_id}, {"$setOnInsert": doc}, upsert=True)
        if result.upserted_id is not None:
            inserted += 1
    return inserted


def seed_candidate_dirs(data_dir: str | Path) -> list[Path]:
    """Where to look for the seed files, most specific first.

    Both candidates are derived from ``data_dir`` rather than including a
    hardcoded ``data/seed``: since ``data_dir`` itself defaults to ``"data"``,
    that literal was both redundant and a trap — it resolved against the current
    working directory, so seeding silently changed behaviour depending on where
    the process was started from.
    """
    return [Path(data_dir) / "seed", Path(data_dir)]


def seed_clubs(db: Any, data_dir: str | Path = "data") -> int:
    """Upsert every club; return how many were new.

    Deliberately not behind the stores-empty guard. Clubs track the registered
    scrapers, so the set grows whenever a source is added — gating them on an
    empty stores collection meant a new club could only ever land on a fresh
    database. There are ~10 of them and every write is ``$setOnInsert``, so
    running this on each startup is both cheap and safe.
    """
    inserted = 0
    for club in load_clubs(data_dir):
        result = db["clubs"].update_one({"_id": club["_id"]}, {"$setOnInsert": club}, upsert=True)
        if result.upserted_id is not None:
            inserted += 1
    if inserted:
        logger.info("Seeded %d new club(s)", inserted)
    return inserted


def seed_clubs_json(clubs_path: Path, data_dir: str | Path = "data") -> int:
    """Materialise ``clubs.json`` next to the other JSON stores; return how many
    clubs were written (0 if it already exists).

    The JSON backend's counterpart to :func:`seed_clubs`. Without it
    ``ClubJsonRepository`` points at a file nobody creates, ``PersistStage``
    builds an empty ``source_id -> club_id`` map, and **every** deal a JSON-mode
    run produces gets ``club_id = None`` — which is exactly how the 8,262 deals
    in ``data/deals.json`` ended up with no club.

    Only ever creates the file. Once it exists it is the live store — ``save()``
    appends member stores to it — so re-seeding would clobber that.
    """
    if clubs_path.exists():
        return 0
    clubs = [
        {**{k: v for k, v in club.items() if k != "_id"}, "id": club["_id"]}
        for club in load_clubs(data_dir)
    ]
    clubs_path.parent.mkdir(parents=True, exist_ok=True)
    clubs_path.write_text(json.dumps(clubs, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Seeded %d club(s) into %s", len(clubs), clubs_path)
    return len(clubs)


def seed_mcc_list(db: Any, data_dir: str | Path = "data") -> int:
    """Upsert the MCC category catalogue into ``mcc_list``; return how many were new.

    Keyed on ``mcc`` rather than routed through :func:`upsert_seed_file`, because
    this collection is read by two services that both bind ``_id`` to a real
    **ObjectId** (the Gateway's ``MccRepository`` and Personalization's
    ``MccCode``).  Promoting the catalogue's own numeric ``id`` into ``_id`` — as
    ``upsert_seed_file`` does — would make every row fail Personalization's model
    validation, so the seed file carries only ``mcc``/``category`` and Mongo
    assigns the key.  ``mcc`` is unique across all 5,952 rows, which is what
    makes the upsert idempotent without one.

    Guarded on its own emptiness rather than on ``stores``: the two are
    independent, and the catalogue is what the app's category filter is built
    from — an empty ``mcc_list`` means the UI offers no categories at all.
    """
    if db["mcc_list"].count_documents({}, limit=1) > 0:
        return 0

    for seed_dir in seed_candidate_dirs(data_dir):
        path = seed_dir / "mcc_list.json"
        if not path.exists():
            continue
        rows = json.loads(path.read_text(encoding="utf-8"))
        inserted = 0
        for row in rows:
            result = db["mcc_list"].update_one(
                {"mcc": row["mcc"]},
                {"$setOnInsert": {"mcc": row["mcc"], "category": row["category"]}},
                upsert=True,
            )
            if result.upserted_id is not None:
                inserted += 1
        logger.info("Auto-seeded %d MCC categor(ies) from %s", inserted, path)
        return inserted

    logger.warning(
        "No mcc_list.json found in any of %s — the category filter will be empty",
        ", ".join(str(d) for d in seed_candidate_dirs(data_dir)),
    )
    return 0


def seed_mongo_if_empty(db: Any, data_dir: str | Path = "data") -> None:
    """Seed stores, aliases and the MCC catalogue; always reconcile clubs.

    Deals are deliberately never seeded — they are what the scrapers produce, so
    shipping a snapshot of them would put stale benefits in front of users.

    Cheap to call on every startup: each guard is a single indexed count that
    returns immediately once the collection has anything in it.
    """
    seed_clubs(db, data_dir)
    seed_mcc_list(db, data_dir)

    if db["stores"].count_documents({}, limit=1) > 0:
        return

    logger.info("MongoDB stores collection is empty — seeding from seed files…")

    for seed_dir in seed_candidate_dirs(data_dir):
        stores_file = seed_dir / "stores.json"
        if not stores_file.exists():
            continue
        stores = upsert_seed_file(db, "stores", stores_file)
        aliases = upsert_seed_file(db, "store_aliases", seed_dir / "store_aliases.json")
        logger.info("Auto-seeded %d stores and %d aliases from %s", stores, aliases, seed_dir)
        break
    else:
        logger.warning(
            "No stores.json found in any of %s — the match stage will have no "
            "canonical stores to resolve against",
            ", ".join(str(d) for d in seed_candidate_dirs(data_dir)),
        )
