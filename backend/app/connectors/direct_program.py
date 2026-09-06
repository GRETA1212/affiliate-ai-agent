import ipaddress
import os
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx
from pydantic import BaseModel, Field, HttpUrl

MAX_DOWNLOAD_BYTES = 1_000_000
MAX_REDIRECTS = 3


class DirectProgramScanError(RuntimeError):
    pass


class DirectProgramScanRequest(BaseModel):
    url: HttpUrl


class DirectProgramScan(BaseModel):
    url: str
    final_url: str
    title: str | None
    commission_percent: float | None
    commission_text: str | None
    cookie_days: int | None
    recurring: bool
    network_hint: str | None
    application_url: str | None
    evidence: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.text_parts: list[str] = []
        self.links: list[tuple[str, str]] = []
        self._active_href: str | None = None
        self._active_text: list[str] = []
        self.title_parts: list[str] = []
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "a":
            self._active_href = attributes.get("href")
            self._active_text = []
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._active_href:
            text = _normalize_space(" ".join(self._active_text))
            self.links.append((self._active_href, text))
            self._active_href = None
            self._active_text = []
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text:
            return
        self.text_parts.append(text)
        if self._active_href is not None:
            self._active_text.append(text)
        if self._in_title:
            self.title_parts.append(text)


def scan_program(
    request: DirectProgramScanRequest,
    *,
    client: httpx.Client | None = None,
) -> DirectProgramScan:
    start_url = str(request.url)
    _validate_public_url(start_url)
    owns_client = client is None
    http_client = client or httpx.Client(timeout=15.0, follow_redirects=False)
    try:
        final_url, html = _fetch_html(start_url, http_client)
    finally:
        if owns_client:
            http_client.close()
    return parse_program_html(start_url, final_url, html)


def parse_program_html(original_url: str, final_url: str, html: str) -> DirectProgramScan:
    parser = _TextExtractor()
    parser.feed(html)
    text = _normalize_space(" ".join(parser.text_parts))
    title = _normalize_space(" ".join(parser.title_parts)) or None

    commission_percent, commission_text = _extract_commission(text)
    cookie_days = _extract_cookie_days(text)
    recurring = bool(
        re.search(
            r"\b(recurring commission|recurring earnings|recurring revenue|lifetime commission)\b",
            text,
            flags=re.IGNORECASE,
        )
    )
    network_hint = _network_hint(text, final_url)
    application_url = _application_url(parser.links, final_url)

    evidence: list[str] = []
    if commission_text:
        evidence.append(commission_text)
    if cookie_days is not None:
        evidence.append(f"{cookie_days}-day cookie/attribution window")
    if recurring:
        evidence.append("Recurring commission language detected")
    if network_hint:
        evidence.append(f"Network hint: {network_hint}")

    populated = sum(
        value is not None
        for value in (commission_percent, cookie_days, network_hint, application_url)
    ) + int(recurring)
    confidence = min(1.0, round(0.25 + populated * 0.13, 2))

    return DirectProgramScan(
        url=original_url,
        final_url=final_url,
        title=title,
        commission_percent=commission_percent,
        commission_text=commission_text,
        cookie_days=cookie_days,
        recurring=recurring,
        network_hint=network_hint,
        application_url=application_url,
        evidence=evidence,
        confidence=confidence,
    )


def _fetch_html(url: str, client: httpx.Client) -> tuple[str, str]:
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        try:
            response = client.get(
                current,
                headers={
                    "Accept": "text/html,application/xhtml+xml",
                    "User-Agent": os.getenv(
                        "DIRECT_SCAN_USER_AGENT",
                        "AffiliateAIAgent/0.3 (+public affiliate program research)",
                    ),
                },
            )
        except httpx.RequestError as exc:
            raise DirectProgramScanError("Could not reach the affiliate program page.") from exc

        if response.status_code in {301, 302, 303, 307, 308}:
            location = response.headers.get("location")
            if not location:
                raise DirectProgramScanError("Affiliate page returned an invalid redirect.")
            current = urljoin(current, location)
            _validate_public_url(current)
            continue
        if response.status_code >= 400:
            raise DirectProgramScanError(
                f"Affiliate program page returned HTTP {response.status_code}."
            )
        content_type = response.headers.get("content-type", "").lower()
        if "html" not in content_type and content_type:
            raise DirectProgramScanError("Affiliate program URL did not return HTML.")
        if len(response.content) > MAX_DOWNLOAD_BYTES:
            raise DirectProgramScanError("Affiliate program page is too large to scan safely.")
        return current, response.text
    raise DirectProgramScanError("Affiliate program page redirected too many times.")


def _validate_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise DirectProgramScanError("Only HTTP(S) affiliate program URLs can be scanned.")
    host = (parsed.hostname or "").lower().strip(".")
    if not host or host == "localhost" or host.endswith(".local"):
        raise DirectProgramScanError("Local/private hosts cannot be scanned.")
    if host in {"metadata.google.internal", "host.docker.internal"}:
        raise DirectProgramScanError("Local/private hosts cannot be scanned.")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return
    if not address.is_global:
        raise DirectProgramScanError("Local/private IP addresses cannot be scanned.")


def _extract_commission(text: str) -> tuple[float | None, str | None]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    candidates: list[tuple[float, str]] = []
    for sentence in sentences:
        if not re.search(
            r"\b(commission|affiliate|referral|payout|revenue share|revshare|earn)\b",
            sentence,
            flags=re.IGNORECASE,
        ):
            continue
        for match in re.finditer(r"(?<!\d)(\d{1,3}(?:\.\d+)?)\s*%", sentence):
            value = float(match.group(1))
            if 0 < value <= 100:
                candidates.append((value, _trim_evidence(sentence)))
    if not candidates:
        return None, None
    value, evidence = max(candidates, key=lambda item: item[0])
    return value, evidence


def _extract_cookie_days(text: str) -> int | None:
    patterns = (
        r"(?<!\d)(\d{1,4})\s*[- ]?day(?:s)?\s+(?:cookie|attribution)",
        r"(?:cookie|attribution)(?:\s+window)?\D{0,20}(\d{1,4})\s*day",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            days = int(match.group(1))
            if 0 < days <= 3650:
                return days
    return None


def _network_hint(text: str, url: str) -> str | None:
    combined = f"{text} {url}".lower()
    networks = {
        "impact": ("impact.com", "impact radius", "impactradius"),
        "cj": ("commission junction", "cj.com", "anrdoezrs", "tkqlhce"),
        "partnerstack": ("partnerstack",),
        "awin": ("awin",),
        "shareasale": ("shareasale",),
    }
    for network, markers in networks.items():
        if any(marker in combined for marker in markers):
            return network
    return None


def _application_url(links: list[tuple[str, str]], base_url: str) -> str | None:
    for href, anchor_text in links:
        text = anchor_text.lower()
        if any(term in text for term in ("apply", "join", "sign up", "become an affiliate")):
            candidate = urljoin(base_url, href)
            parsed = urlparse(candidate)
            if parsed.scheme in {"http", "https"}:
                return candidate
    return None


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _trim_evidence(value: str) -> str:
    normalized = _normalize_space(value)
    return normalized if len(normalized) <= 240 else f"{normalized[:237]}..."
