import pytest

from bootstrap_hostinger_campaign import _validate_affiliate_url


def test_rejects_personal_referral_link() -> None:
    with pytest.raises(SystemExit, match="Referral-code"):
        _validate_affiliate_url("https://www.hostinger.com?REFERRALCODE=SHBEXAMPLE")


def test_rejects_hpanel_link() -> None:
    with pytest.raises(SystemExit, match="hPanel"):
        _validate_affiliate_url("https://hpanel.hostinger.com/ai-builder-trial")


def test_rejects_private_horizons_project_link() -> None:
    with pytest.raises(SystemExit, match="project URL"):
        _validate_affiliate_url(
            "https://horizons.hostinger.com/63ed579b-347b-46e6-9eb1-9fcefee42817?onboarding=true"
        )


def test_accepts_public_hostinger_tracking_shape() -> None:
    _validate_affiliate_url("https://www.hostinger.com/horizons?utm_source=affiliate")
