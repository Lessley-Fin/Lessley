"""Who the caller is, and which loyalty programs they actually belong to.

Eligibility is a server-side fact. The edge (Caddy) authenticates every ``/optimize``
request against the Gateway and injects the verified ``X-Auth-Email``; this module turns
that identity into the ``source_id``s the deal side keys on. Nothing here trusts the
request body — a client that could name its own memberships could hand itself every
members-only deal in the database.

Reading the Gateway's ``users`` collection directly is the established pattern for a
service exposed at the edge: ``Lessley.Personalization``'s ``user_repository`` does exactly
this, keyed on the same ``NormalizedEmail``. Writes always go through the Gateway; this is
read-only.
"""

from __future__ import annotations

import logging
import os

from pymongo.database import Database

from .deals_source import get_database

logger = logging.getLogger(__name__)

USERS_COLLECTION = os.environ.get("USERS_COLLECTION", "users")
CLUBS_COLLECTION = os.environ.get("CLUBS_COLLECTION", "clubs")

# Clubs are conventionally named ``club_`` + their own source_id. That convention is
# hand-maintained, so it is only the fallback — see club_source_ids.
_CLUB_ID_PREFIX = "club_"


def load_user_clubs(email: str, db: Database | None = None) -> list[str] | None:  # type: ignore[type-arg]
    """The club ids this user has joined, or ``None`` when there is no such user.

    ``None`` and ``[]`` are different answers and both matter: no such user is an error
    the caller should see, while a user who has joined nothing is a *known* user whose
    members-only deals must be pruned.
    """
    database = db if db is not None else get_database()
    # ASP.NET Identity stores the uppercased address; Personalization keys on it the same way.
    user = database[USERS_COLLECTION].find_one(
        {"NormalizedEmail": email.strip().upper()}, {"Clubs": 1}
    )
    if user is None:
        return None
    return [str(club_id) for club_id in (user.get("Clubs") or []) if club_id]


def club_source_ids(club_ids: list[str], db: Database | None = None) -> list[str]:  # type: ignore[type-arg]
    """Map club ids (``club_hot``) to the deal side's ``source_id``s (``hot``).

    The mapping is read from the ``clubs`` collection, which carries a real ``source_id``
    on every row, rather than inferred from the id. The ``club_``-prefix convention is
    only a fallback for a club the collection does not know: a club that broke the
    convention would otherwise silently prune the deals its own members are entitled to.
    """
    if not club_ids:
        return []

    wanted = list(dict.fromkeys(club_ids))
    by_club_id = _source_id_by_club_id(wanted, db)

    resolved: list[str] = []
    for club_id in wanted:
        source_id = by_club_id.get(club_id)
        if source_id is None:
            source_id = club_id[len(_CLUB_ID_PREFIX):] if club_id.startswith(_CLUB_ID_PREFIX) else club_id
            logger.warning(
                "Club %s is not in the clubs collection — falling back to the id convention (%s)",
                club_id,
                source_id,
            )
        if source_id and source_id not in resolved:
            resolved.append(source_id)
    return resolved


def _source_id_by_club_id(club_ids: list[str], db: Database | None) -> dict[str, str]:  # type: ignore[type-arg]
    """``club_id`` -> ``source_id`` for the clubs asked about.

    Matches on ``_id`` or ``id``, because the business key sits in whichever field the
    row was written with — the pipeline pops it into ``_id``, while rows imported from
    ``main/resources/clubs.json`` keep ``id`` and gain an ObjectId ``_id``.
    """
    database = db if db is not None else get_database()
    cursor = database[CLUBS_COLLECTION].find(
        {"$or": [{"_id": {"$in": club_ids}}, {"id": {"$in": club_ids}}]},
        {"_id": 1, "id": 1, "source_id": 1},
    )

    mapping: dict[str, str] = {}
    for club in cursor:
        source_id = club.get("source_id")
        if not source_id:
            continue
        for key in (club.get("id"), club.get("_id")):
            if isinstance(key, str) and key:
                mapping[key] = str(source_id)
    return mapping


def member_source_ids_for(email: str, db: Database | None = None) -> list[str] | None:  # type: ignore[type-arg]
    """Everything the engine needs to prune by eligibility, for one authenticated caller.

    Returns ``None`` only when the user does not exist; an existing user with no clubs
    gets ``[]``, which prunes rather than opens.
    """
    clubs = load_user_clubs(email, db)
    if clubs is None:
        return None
    source_ids = club_source_ids(clubs, db)
    logger.debug("Resolved %d club(s) to %d source_id(s) for the caller", len(clubs), len(source_ids))
    return source_ids
