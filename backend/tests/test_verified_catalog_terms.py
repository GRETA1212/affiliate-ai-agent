from app.services.verified_catalog import search_verified_programs


def test_hostinger_horizons_current_terms() -> None:
    programs = search_verified_programs("Hostinger Horizons")
    hostinger = next(program for program in programs if program.advertiser == "Hostinger")
    assert hostinger.commission_percent == 60.0
    assert hostinger.cookie_days == 30
    assert hostinger.recurring is False


def test_semrush_current_terms() -> None:
    programs = search_verified_programs("Semrush")
    semrush = next(program for program in programs if program.advertiser == "Semrush")
    assert semrush.fixed_payout_amount == 450.0
    assert semrush.cookie_days == 120
    assert semrush.fixed_payout_currency == "USD"
