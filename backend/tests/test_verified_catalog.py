from app.services.verified_catalog import search_verified_programs


def test_verified_catalog_finds_ai_voice_program() -> None:
    programs = search_verified_programs("AI voice")
    advertisers = {program.advertiser for program in programs}

    assert "ElevenLabs" in advertisers


def test_verified_catalog_preserves_program_terms_metadata() -> None:
    programs = search_verified_programs("vibe coding")
    by_name = {program.advertiser: program for program in programs}

    assert by_name["Lovable"].commission_percent == 20.0
    assert by_name["Lovable"].recurring_months == 12
    assert by_name["Hostinger"].commission_percent == 60.0
    assert by_name["Hostinger"].recurring is False
