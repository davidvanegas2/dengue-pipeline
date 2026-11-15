import pytest

from dengue_pipeline.text import normalize_name, parse_decimal, parse_integer, strip_accents


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("9 504", 9504),
        ("56 797", 56797),
        ("1959", 1959),
        ("75", 75),
        ("1.234", 1234),
        ("9 504", 9504),  # nonbreaking space, common in PDFs
        (" 12 ", 12),
    ],
)
def test_parse_integer(text: str, expected: int) -> None:
    assert parse_integer(text) == expected


@pytest.mark.parametrize("text", ["", "abc", "30,3", "9 5o4"])
def test_parse_integer_rejects_invalid_input(text: str) -> None:
    with pytest.raises(ValueError, match="integer"):
        parse_integer(text)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("30,3", 30.3),
        ("0,9", 0.9),
        ("-74,815546", -74.815546),
        ("10.97", 10.97),
        ("1.234,5", 1234.5),
    ],
)
def test_parse_decimal(text: str, expected: float) -> None:
    assert parse_decimal(text) == pytest.approx(expected)


def test_parse_decimal_rejects_invalid_input() -> None:
    with pytest.raises(ValueError, match="decimal"):
        parse_decimal("thirty")


def test_strip_accents_preserves_letters() -> None:
    assert strip_accents("Nariño, Bogotá, Chocó, Güicán") == "Narino, Bogota, Choco, Guican"


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("Valle Del Cauca", "VALLE DEL CAUCA"),
        ("Atlántico", "ATLANTICO"),
        ("BOGOTA, D.C", "Bogotá D.C."),
        ("  Santiago   de Cali ", "SANTIAGO DE CALI"),
    ],
)
def test_normalize_name_matches_variants(a: str, b: str) -> None:
    assert normalize_name(a) == normalize_name(b)
