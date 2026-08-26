"""Bulk-resolve the store-match review queue from evidence, not from guesswork.

The interactive TUI (``deals review``) asks a human about one item at a time. That is
the right tool when the answer needs judgment. It is the wrong tool for a queue that
has filled up with items a rule can settle — and most of this queue is exactly that.

Three rules decide an item here, in descending order of how much they prove:

``matcher``
    Re-run the project's own :class:`MatchPipeline` against the current catalogue.
    An item queued months ago may simply match now, because a store was added since
    or because the normalizer that queued it has been fixed. Nothing beats the
    matcher's own AUTO_MATCH — it is the same verdict a scrape would produce.

``same domain``
    The scraped record and an existing store point at the same registrable domain.
    A website is the closest thing a store has to a primary key, so this settles
    Hebrew-vs-English spellings of one brand that no string metric would pair up.

``identical name form``
    The compact name form is already carried by a store or one of its aliases.

Over all three sits one veto, and it is the reason this module exists rather than a
looser "merge anything that looks similar":

**Online parity.** A name carrying an online marker names a *different business* from
the same brand without one. ``vans online`` is not ``vans``: different inventory,
different prices, and a benefit valid at one is routinely invalid at the other. So a
link is only ever allowed between two names that agree on the marker, whatever the
evidence says. The same veto is what makes an online storefront eligible to become a
store of its own instead of being folded into the brand.

Anything the rules cannot settle stays pending for a human. Under-resolving is
recoverable; a silent mismatch quietly prices a benefit the user cannot actually use.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import urlparse

from lessley_deals.domain.enums import MatchDecision
from lessley_deals.enrichment.hot_categories import category_for
from lessley_deals.domain.models import NormalizedRecord
from lessley_deals.normalization.text import (
    collapse_whitespace,
    extract_branch,
    strip_legal_suffixes,
)
from lessley_deals.review.actions import build_name_forms

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from lessley_deals.domain.models import CanonicalStore, NameForms, ReviewItem, StoreAlias
    from lessley_deals.matching.index import AliasIndex
    from lessley_deals.matching.pipeline import MatchPipeline

# "vans online", "נעמן אונליין", "H&O און ליין", "shop on-line".
_ONLINE_RE = re.compile(r"(online|on[\s\-]?line|אונליי?ן|און[\s\-]?ליי?ן)", re.IGNORECASE)

# Israeli second-level domains: the registrable name is one label further left.
_IL_SUFFIXES = (".co.il", ".org.il", ".net.il", ".ac.il", ".gov.il", ".muni.il", ".k12.il")

# The benefit aggregators themselves. Hundreds of merchants are listed under one of
# these because the scraped record links to the *offer page*, not to the merchant, so
# a shared aggregator domain says only "both are sold by PaisPlus" — it is not
# identity. 184 stores in the catalogue already carry hvr.co.il and 54 carry
# paisplus.co.il; treating that as evidence would collapse them into one business.
SOURCE_DOMAINS = frozenset({
    "paisplus.co.il", "behatsdaa.org.il", "hot.co.il", "topcash.co.il",
    "isracard.co.il", "mastercard.co.il", "mastercard.com", "hvr.co.il", "k4a.co.il",
})

# Generic Hebrew wrappers a source puts in front of a brand: "חנויות H&O" is H&O.
_NAME_PREFIX_RE = re.compile(r"^(?:ה?חנויות|רשת(?:ות)?|קבוצת|אתר)\s+")

# Names that describe a *voucher*, not a shop — "שובר זוגי להצגה", "תו קנייה בשווי
# 350 ₪ לאתר X". The merchant may be buried inside, but pulling it out reliably is a
# parsing problem of its own; creating a store from the sentence would file
# "couple voucher for a show" in the catalogue as a business.
_VOUCHER_RE = re.compile(r"(תו\s*קני|תווי\s*קני|שובר|בשווי\s*[\d,]|כרטיס נטען|גיפט\s*קארד)")


def has_online_marker(name: str | None) -> bool:
    """Whether a store name advertises itself as the brand's online storefront."""
    return bool(_ONLINE_RE.search(name or ""))


def strip_online_marker(name: str) -> str:
    """The same name with the online marker removed — the brand behind the storefront."""
    return collapse_whitespace(_ONLINE_RE.sub(" ", name or "")).strip(" -–—")


def registrable_domain(url: str | None) -> str | None:
    """``https://shop.vans.co.il/x`` → ``vans.co.il``.

    Subdomains are dropped on purpose: a brand's shop, its landing page and its www
    host are one business, and matching on the full host would miss that.
    """
    if not url:
        return None
    if "//" not in url:
        url = "https://" + url
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return None
    host = host.removeprefix("www.")
    if not host:
        return None
    for suffix in _IL_SUFFIXES:
        if host.endswith(suffix):
            label = host[: -len(suffix)].rsplit(".", 1)[-1]
            return f"{label}{suffix}" if label else host
    parts = host.split(".")
    domain = ".".join(parts[-2:]) if len(parts) > 2 else host
    return domain if _is_plausible_domain(domain) else None


def is_merchant_domain(domain: str | None) -> bool:
    """Whether a domain identifies a merchant rather than the aggregator listing it."""
    return bool(domain) and domain not in SOURCE_DOMAINS


def looks_like_voucher(name: str) -> bool:
    """Whether the text describes a voucher rather than naming a shop."""
    return bool(_VOUCHER_RE.search(name or ""))


def strip_name_prefix(name: str) -> str:
    """``חנויות H&O`` → ``H&O``; returns the name unchanged when it has no wrapper."""
    return collapse_whitespace(_NAME_PREFIX_RE.sub("", name or "")).strip(" \"'")


# Second-level labels that are part of a public suffix, never a business's own name.
_PUBLIC_SECOND_LEVEL = frozenset({"co", "com", "net", "org", "ac", "gov", "edu", "muni", "k12"})


def _is_plausible_domain(domain: str) -> bool:
    """Reject the shapes that mean a URL was truncated, not that a brand was found.

    The scraped data contains ``https://www.cakenet.co.i`` — a ``.co.il`` with the
    last character lost. Naive two-label logic reads that as the domain ``co.i``,
    which then "matches" every other truncated URL in the catalogue and merges two
    unrelated businesses. A domain is the strongest evidence this module has, so a
    malformed one has to be discarded rather than trusted.
    """
    head, _, tld = domain.rpartition(".")
    if not head or len(tld) < 2 or not tld.isalpha():
        return False
    return head not in _PUBLIC_SECOND_LEVEL


def normalize_store_name(raw_name: str) -> NameForms:
    """The store-name half of the normalization pipeline, applied to one name.

    Deliberately re-derived rather than read off ``ReviewItem.input_name_forms``: those
    were computed by whichever normalizer was current when the item was queued, and a
    queue this old has outlived more than one version of it.
    """
    name, _branch = extract_branch(strip_legal_suffixes(raw_name))
    return build_name_forms(collapse_whitespace(name))


Action = Literal["link", "create", "defer"]


@dataclass
class Resolution:
    """What to do with one review item, and what it rests on."""

    item_id: str
    input_name: str
    action: Action
    reason: str
    source_id: str | None = None
    store_id: str | None = None
    store_name: str | None = None
    club_id: str | None = None
    mcc_codes: tuple[str, ...] = ()
    """Categories for a store being created — inherited from the brand it belongs to."""

    online: bool = False


@dataclass
class CatalogueIndex:
    """The existing catalogue, indexed the three ways the rules interrogate it."""

    stores_by_id: dict[str, CanonicalStore]
    by_domain: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    by_compact: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))

    @classmethod
    def build(
        cls, stores: Sequence[CanonicalStore], aliases: Sequence[StoreAlias]
    ) -> CatalogueIndex:
        index = cls(stores_by_id={s.id: s for s in stores})
        for store in stores:
            domain = registrable_domain(store.metadata.get("store_url")) or store.metadata.get(
                "domain"
            )
            if domain:
                index.by_domain[domain].add(store.id)
            index.by_compact[store.name_forms.compact].add(store.id)
        for alias in aliases:
            index.by_compact[alias.alias_forms.compact].add(alias.store_id)
        return index

    def parity_matches(self, store_id: str, online: bool) -> bool:
        """The online veto: a store only qualifies if it agrees about being online."""
        store = self.stores_by_id.get(store_id)
        return store is not None and has_online_marker(store.name) == online

    def sole_match(self, store_ids: set[str], online: bool) -> str | None:
        """The one store that satisfies the veto, or None if zero or several do.

        Ambiguity is treated as no evidence: two candidate stores mean the catalogue
        already holds a duplicate, and picking either would guess which one wins.
        """
        eligible = [sid for sid in store_ids if self.parity_matches(sid, online)]
        return eligible[0] if len(eligible) == 1 else None


def plan_resolutions(
    items: Sequence[ReviewItem],
    *,
    catalogue: CatalogueIndex,
    match_index: AliasIndex,
    matcher: MatchPipeline,
    raw_by_id: Mapping[str, Mapping[str, Any]],
    club_by_source: Mapping[str, str],
    allow_create: bool = True,
) -> list[Resolution]:
    """Decide every item. Performs no I/O, so the whole rule set is unit-testable."""
    resolutions: list[Resolution] = []

    for item in items:
        raw_name = item.raw_input_name or item.input_name
        online = has_online_marker(raw_name)
        record = raw_by_id.get(item.raw_id, {})
        source_id = record.get("source_id")
        base = Resolution(
            item_id=item.id,
            input_name=raw_name,
            action="defer",
            reason="no evidence",
            source_id=source_id,
            club_id=club_by_source.get(source_id or ""),
            online=online,
        )

        forms = normalize_store_name(raw_name)

        # --- 1. the matcher's own verdict against today's catalogue --------------
        verdict = matcher.match(
            NormalizedRecord(
                raw_id=item.raw_id,
                source_id=source_id or "",
                store_name_forms=forms,
                deal_description="",
                normalized_at=item.created_at,
                domain=registrable_domain(record.get("store_url") or record.get("url")),
            ),
            match_index,
        )
        if (
            verdict.decision == MatchDecision.AUTO_MATCH
            and verdict.best
            and catalogue.parity_matches(verdict.best.store_id, online)
        ):
            # One guard the matcher itself does not apply. Its exact-alias index keeps
            # the *first* store it saw for a given compact form, so when the catalogue
            # holds two stores under one name it picks by insertion order. A single
            # scrape can live with that; an unattended pass over hundreds of items
            # should not, and a duplicate name is precisely the kind of mess this
            # cleanup exists to surface rather than cement.
            if _ambiguous(catalogue, raw_name, forms, online):
                base.reason = "ambiguous — the catalogue holds more than one such store"
                resolutions.append(base)
                continue
            store = catalogue.stores_by_id[verdict.best.store_id]
            resolutions.append(
                _linked(base, store, f"matcher {verdict.best.stage} {verdict.best.confidence:.2f}")
            )
            continue

        # --- 2. same registrable domain -----------------------------------------
        domain = registrable_domain(record.get("store_url") or record.get("url"))
        if not is_merchant_domain(domain):
            domain = None
        store_id = catalogue.sole_match(catalogue.by_domain.get(domain, set()), online) if domain else None
        if store_id:
            resolutions.append(
                _linked(base, catalogue.stores_by_id[store_id], f"same domain {domain}")
            )
            continue

        # --- 3. the name is already on a store or one of its aliases -------------
        # The *whole* scraped name is tried before the branch-stripped one. Plenty of
        # real store names contain a dash — "LISA - Beer Garden", "אקווה גן - כפר רות"
        # — and the catalogue stores them whole. Looking up only the stripped form asks
        # for "LISA" and misses the store sitting there under its own full name.
        by_name = next(
            (
                (sid, why)
                for compact, why in (
                    (build_name_forms(raw_name).compact, "identical name form"),
                    (forms.compact, "identical name form (branch stripped)"),
                )
                if (sid := catalogue.sole_match(catalogue.by_compact.get(compact, set()), online))
            ),
            None,
        )
        if by_name:
            store_id, why = by_name
            resolutions.append(_linked(base, catalogue.stores_by_id[store_id], why))
            continue

        # --- 3b. the same name with a generic wrapper removed --------------------
        # Sources wrap a brand for display: PaisPlus lists H&O as "חנויות H&O".
        # The wrapper is the source's word, not part of the business's name.
        unwrapped = strip_name_prefix(raw_name)
        if unwrapped and unwrapped != raw_name:
            store_id = catalogue.sole_match(
                catalogue.by_compact.get(build_name_forms(unwrapped).compact, set()), online
            )
            if store_id:
                resolutions.append(
                    _linked(base, catalogue.stores_by_id[store_id], "name without its wrapper")
                )
                continue

        # --- 4. an online storefront of a brand we know becomes its own store ----
        # Only for online names, and only when the brand behind it is already in the
        # catalogue: that is what makes this a storefront of a known business rather
        # than an unknown name nobody has vetted. Its categories come from the brand,
        # which is the one thing about it we genuinely know.
        if allow_create and not looks_like_voucher(raw_name):
            brand = _brand_behind(raw_name, catalogue) if online else None
            if brand is not None:
                # Its categories come from the brand — the one thing we know about it.
                base.action = "create"
                base.reason = f"online storefront of {brand.name}"
                base.mcc_codes = tuple(brand.metadata.get("mcc_codes") or ())
                resolutions.append(base)
                continue

            # --- 5. a business the catalogue simply does not have yet ------------
            # Nothing matched it, and it is not a voucher description: it is a real
            # merchant nobody has entered. Leaving it out is not neutral — its deals
            # stay invisible to every consumer until someone types the name in by hand.
            #
            # Two things can vouch for it being a business rather than a stray piece of
            # ad copy, and either will do. A merchant domain of its own is one. A
            # category the *source* assigned it is the other, and it is the stronger of
            # the two: a marketing sentence does not get filed under "עולם הקפה" by
            # HOT's own taxonomy. Requiring the domain alone excluded every HOT
            # merchant — the one source that publishes a category at all.
            category = category_for(record.get("category"))
            has_domain = is_merchant_domain(
                registrable_domain(record.get("store_url") or record.get("url"))
            )
            if has_domain or record.get("category"):
                base.action = "create"
                base.mcc_codes = tuple(filter(None, (category,)))
                base.reason = (
                    f"new business, category from {source_id}"
                    if category
                    else "new business, category unknown"
                )
                resolutions.append(base)
                continue

        resolutions.append(base)

    return resolutions


def _ambiguous(
    catalogue: CatalogueIndex, raw_name: str, forms: NameForms, online: bool
) -> bool:
    """Whether this name is carried by more than one store that survives the veto."""
    for compact in (build_name_forms(raw_name).compact, forms.compact):
        holders = [
            sid
            for sid in catalogue.by_compact.get(compact, set())
            if catalogue.parity_matches(sid, online)
        ]
        if len(holders) > 1:
            return True
    return False


def _linked(base: Resolution, store: CanonicalStore, reason: str) -> Resolution:
    base.action = "link"
    base.reason = reason
    base.store_id = store.id
    base.store_name = store.name
    return base


def _store_metadata(res: Resolution, reviewed_by: str) -> dict[str, Any]:
    """Categories for a store being created, with an honest confidence marker.

    Codes go through the canonical vocabulary rather than being copied verbatim: a
    brand's own list is not always normalized, and an over-long or loosely-spelled one
    would spread from here into every store created after it.

    With no evidence at all the store still gets created, under ``OTHER`` and flagged
    ``UNKNOWN``. That is the deliberate trade: a store filed under OTHER is a business
    whose deals are visible and whose category one ``deals enrich-stores`` run fixes,
    whereas a business left out of the catalogue is invisible until somebody types its
    name in by hand. ``mcc_source`` is what makes them findable later.
    """
    from lessley_deals.enrichment.mcc_catalog import FALLBACK_CATEGORY, normalize_mcc_codes

    codes = normalize_mcc_codes(res.mcc_codes)
    return {
        "mcc_codes": codes or [FALLBACK_CATEGORY],
        "mcc_confidence": "INHERITED" if codes else "UNKNOWN",
        "mcc_source": f"review:{reviewed_by} ({res.reason})",
    }


def _brand_behind(online_name: str, catalogue: CatalogueIndex) -> CanonicalStore | None:
    """The non-online store this storefront belongs to, if the catalogue holds it."""
    brand = strip_online_marker(online_name)
    if len(brand) < 2:
        return None
    compact = normalize_store_name(brand).compact
    store_id = catalogue.sole_match(catalogue.by_compact.get(compact, set()), online=False)
    return catalogue.stores_by_id[store_id] if store_id else None


# ---------------------------------------------------------------------------
# Applying a plan
# ---------------------------------------------------------------------------

@dataclass
class ApplyReport:
    linked: int = 0
    created_stores: int = 0
    created_links: int = 0
    """Items that pointed at a store this run created rather than creating another."""

    aliases_written: int = 0
    club_attachments: int = 0
    deferred: int = 0

    def summary(self) -> str:
        return (
            f"linked={self.linked} new stores={self.created_stores} "
            f"(+{self.created_links} more items onto them) aliases={self.aliases_written} "
            f"club links={self.club_attachments} deferred={self.deferred}"
        )


def apply_resolutions(
    resolutions: Sequence[Resolution],
    items_by_id: Mapping[str, ReviewItem],
    *,
    store_repo: Any,
    alias_repo: Any,
    review_repo: Any,
    club_repo: Any,
    reviewed_by: str = "system:bulk-resolve",
    now: datetime | None = None,
) -> ApplyReport:
    """Write a plan out: stores, aliases, review decisions, club membership.

    Deliberately writes no ``Deal``. A review decision's durable output is the alias —
    it teaches the matcher, and the next pipeline run then builds the deal from the raw
    record it still holds, with the title, URL, terms and discount logic that a
    fabricated stub would not have.

    Items are grouped by name before anything is created, so a storefront appearing
    three times in the queue becomes one store with three items pointing at it rather
    than three competing duplicates — which is the exact failure this queue exists to
    clean up.
    """
    from lessley_deals.domain.enums import AliasSource, ReviewAction, ReviewStatus
    from lessley_deals.domain.models import CanonicalStore, ReviewDecision, StoreAlias
    from lessley_deals.persistence.id_gen import generate_id

    now = now or datetime.now(timezone.utc)
    report = ApplyReport()
    club_additions: dict[str, set[str]] = defaultdict(set)

    def write_alias(store_id: str, text: str) -> None:
        alias_repo.save(
            StoreAlias(
                id=generate_id(),
                store_id=store_id,
                alias=text,
                alias_forms=build_name_forms(text),
                source=AliasSource.REVIEW,
                created_at=now,
            )
        )
        report.aliases_written += 1

    def close_item(res: Resolution, store_id: str, action: ReviewAction, status: ReviewStatus,
                   new_name: str | None = None) -> None:
        item = items_by_id[res.item_id]
        item.status = status
        item.reviewed_at = now
        item.decision = ReviewDecision(
            action=action,
            reviewed_by=reviewed_by,
            store_id=store_id,
            new_store_name=new_name,
            note=res.reason,
        )
        review_repo.update(item)
        if res.club_id:
            club_additions[res.club_id].add(store_id)

    # --- stores to create, one per distinct name -----------------------------
    creates: dict[str, list[Resolution]] = defaultdict(list)
    for res in resolutions:
        if res.action == "create":
            creates[build_name_forms(res.input_name).compact].append(res)

    for group in creates.values():
        first = group[0]
        store = CanonicalStore(
            id=generate_id(),
            name=first.input_name,
            name_forms=build_name_forms(first.input_name),
            created_at=now,
            updated_at=now,
            metadata=_store_metadata(first, reviewed_by),
        )
        store_repo.save(store)
        report.created_stores += 1
        write_alias(store.id, first.input_name)

        for res in group:
            close_item(res, store.id, ReviewAction.CREATE_NEW, ReviewStatus.CREATED,
                       new_name=store.name)
            if res is not first:
                report.created_links += 1

    # --- links onto stores that already existed ------------------------------
    for res in resolutions:
        if res.action == "link" and res.store_id:
            write_alias(res.store_id, res.input_name)
            close_item(res, res.store_id, ReviewAction.APPROVE, ReviewStatus.APPROVED)
            report.linked += 1
        elif res.action == "defer":
            report.deferred += 1

    # --- club membership ------------------------------------------------------
    for club_id, store_ids in club_additions.items():
        club = club_repo.get_by_id(club_id)
        if club is None:
            continue
        known = set(club.stores)
        fresh = [sid for sid in sorted(store_ids) if sid not in known]
        if fresh:
            club.stores.extend(fresh)
            club_repo.save(club)
            report.club_attachments += len(fresh)

    return report
