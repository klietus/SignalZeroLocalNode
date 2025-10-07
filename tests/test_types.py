from app.types import Facets, Symbol


def test_symbol_allows_extra_fields():
    symbol = Symbol(id="sym", extra_field="value")
    assert symbol.id == "sym"
    assert symbol.extra_field == "value"


def test_facets_defaults():
    facets = Facets()
    assert facets.function is None
    assert facets.gate is None
