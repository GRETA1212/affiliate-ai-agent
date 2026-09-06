from app.services.monetization_blueprints import get_blueprint, list_blueprints


def test_hostinger_is_first_priority() -> None:
    blueprints = list_blueprints()
    assert blueprints[0].advertiser == "Hostinger"
    assert blueprints[0].priority == 1
    assert len(blueprints[0].content_angles) >= 3
    assert any("affiliate" in note.lower() for note in blueprints[0].compliance_notes)


def test_semrush_blueprint_is_available() -> None:
    blueprint = get_blueprint("Semrush")
    assert blueprint is not None
    assert blueprint.priority == 2
    assert any(angle.intent == "comparison" for angle in blueprint.content_angles)


def test_product_name_lookup_is_case_insensitive() -> None:
    blueprint = get_blueprint("hostinger horizons")
    assert blueprint is not None
    assert blueprint.advertiser == "Hostinger"


def test_unknown_blueprint_returns_none() -> None:
    assert get_blueprint("unknown product") is None
