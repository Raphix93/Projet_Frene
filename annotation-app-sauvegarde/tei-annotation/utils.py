from __future__ import annotations

import hashlib
import re

from .constants import WIKIDATA_ENTITY_PREFIX


WIKIDATA_ID_PATTERN = re.compile(r"^Q[1-9][0-9]*$")


def sha256_text(text: str) -> str:
    """Calcule le SHA-256 UTF-8 d’une chaîne."""

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_wikidata_uri(value: str | None) -> str | None:
    """Normalise un identifiant Q ou une URI d’entité Wikidata."""

    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        return None

    if WIKIDATA_ID_PATTERN.fullmatch(normalized):
        return f"{WIKIDATA_ENTITY_PREFIX}{normalized}"

    if normalized.startswith(WIKIDATA_ENTITY_PREFIX):
        entity_id = normalized.removeprefix(WIKIDATA_ENTITY_PREFIX)
        if WIKIDATA_ID_PATTERN.fullmatch(entity_id):
            return normalized

    return normalized


def wikidata_id(uri: str | None) -> str | None:
    """Retourne l’identifiant Q d’une URI Wikidata valide."""

    normalized = normalize_wikidata_uri(uri)
    if not normalized or not normalized.startswith(WIKIDATA_ENTITY_PREFIX):
        return None

    entity_id = normalized.removeprefix(WIKIDATA_ENTITY_PREFIX)
    return entity_id if WIKIDATA_ID_PATTERN.fullmatch(entity_id) else None
