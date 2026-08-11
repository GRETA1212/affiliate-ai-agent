import httpx

from app.connectors.direct_program import (
    DirectProgramScanRequest,
    parse_program_html,
    scan_program,
)

SAMPLE_HTML = """
<html>
<head><title>Acme AI Affiliate Program</title></head>
<body>
  <h1>Join our affiliate program</h1>
  <p>Earn up to 30% commission on every eligible sale.</p>
  <p>We offer recurring commission for subscriptions.</p>
  <p>Your referrals are tracked with a 90-day cookie.</p>
  <p>Our program is powered by Impact.com.</p>
  <a href="/apply">Apply now</a>
</body>
</html>
"""


def test_parse_direct_program_terms() -> None:
    result = parse_program_html(
        "https://acme.example/affiliates",
        "https://acme.example/affiliates",
        SAMPLE_HTML,
    )

    assert result.title == "Acme AI Affiliate Program"
    assert result.commission_percent == 30.0
    assert result.cookie_days == 90
    assert result.recurring is True
    assert result.network_hint == "impact"
    assert result.application_url == "https://acme.example/apply"
    assert result.confidence > 0.5


def test_scan_program_fetches_public_html() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("https://acme.example/affiliates")
        return httpx.Response(
            200,
            text=SAMPLE_HTML,
            headers={"content-type": "text/html; charset=utf-8"},
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = scan_program(
            DirectProgramScanRequest(url="https://acme.example/affiliates"),
            client=client,
        )

    assert result.commission_percent == 30.0
    assert result.cookie_days == 90
