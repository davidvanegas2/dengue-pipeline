"""Text utilities for Colombian public data.

Parse numbers such as "9 504" and "30,3", and normalize capitalization and
accents. Place-name aliases such as CALI / SANTIAGO DE CALI require the
reference tables under data/reference.
"""

from __future__ import annotations

import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")
_NON_ALPHANUMERIC = re.compile(r"[^A-Z0-9 ]")


def strip_accents(text: str) -> str:
    """Remove accents and diaereses, mapping Ñ to N.

    >>> strip_accents("Atlántico, Bogotá, Nariño")
    'Atlantico, Bogota, Narino'
    """
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def normalize_name(text: str) -> str:
    """Uppercase a place name, remove accents and punctuation, and collapse spaces.

    >>> normalize_name("  Bogotá, D.C. ")
    'BOGOTA D C'
    >>> normalize_name("Valle Del Cauca") == normalize_name("VALLE DEL CAUCA")
    True
    """
    cleaned = strip_accents(text).upper()
    cleaned = _NON_ALPHANUMERIC.sub(" ", cleaned)
    return _WHITESPACE.sub(" ", cleaned).strip()


def parse_integer(text: str) -> int:
    """Parse Colombian thousands separators (spaces, nonbreaking spaces or dots).

    >>> parse_integer("56 797")
    56797
    >>> parse_integer("1.959")
    1959
    """
    cleaned = re.sub(r"[\s .]", "", text)
    if not cleaned.lstrip("-").isdigit():
        raise ValueError(f"Invalid integer: {text!r}")
    return int(cleaned)


def parse_decimal(text: str) -> float:
    """Parse a comma-decimal number as a float.

    >>> parse_decimal("30,3")
    30.3
    >>> parse_decimal("-74,815546")
    -74.815546
    """
    cleaned = re.sub(r"[\s ]", "", text)
    if cleaned.count(",") == 1:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError as error:
        raise ValueError(f"Invalid decimal: {text!r}") from error
