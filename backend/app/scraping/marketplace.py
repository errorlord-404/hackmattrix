"""Bounded extraction for explicitly configured public directory pages.

This module deliberately does not search Google, bypass logins, or scrape an
unbounded third-party marketplace. Operators supply a vetted public URL and a
category. We ingest only JSON-LD records the publisher has made available.
"""

from __future__ import annotations

import json
import re
import time
from html import unescape
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any, Callable
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from app.scraping.sources import SourceFetchError, _fetch_text, stable_source_id


ALLOWED_LISTING_TYPES = {"machinery", "seed", "fertilizer", "logistics", "buyer", "exporter"}


def _html_text(value: str) -> str | None:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", value))).strip() or None


def parse_apeda_exporters(html: str, *, source_url: str, fetched_at: datetime | None = None) -> list[dict[str, Any]]:
    """Parse APEDA's public exporter cards; never follows protected contact flows."""
    timestamp = fetched_at or datetime.now(timezone.utc)
    cards = re.findall(r'<div class="box col-md-4">(.*?)(?=<div class="box col-md-4">|<div class="pagination|</section>)', html, flags=re.DOTALL)
    records: dict[str, dict[str, Any]] = {}
    for card in cards:
        paragraphs = [_html_text(value) for value in re.findall(r"<p[^>]*>(.*?)</p>", card, flags=re.DOTALL)]
        values = [value for value in paragraphs if value]
        if len(values) < 4:
            continue
        title, address, commodities, state = values[:4]
        record_id = stable_source_id("apeda-exporter", title, address, state)
        records[record_id] = {
            "source_record_id": record_id, "listing_type": "exporter", "title": title,
            "category": commodities, "provider_name": title, "description": "APEDA registered exporter directory record.",
            "location": address, "district": None, "state": state, "price_amount": None, "price_currency": "INR",
            "price_unit": None, "contact_phone": None, "contact_email": None, "listing_url": source_url,
            "source": "APEDA Agri Exchange registered exporter directory", "source_url": source_url,
            "observed_at": None, "fetched_at": timestamp,
        }
    return list(records.values())


def _parse_apeda_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%d/%m/%Y").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _label_value(value: str) -> tuple[str, str]:
    cleaned = re.sub(r"\s+", " ", value).strip()
    if ":" not in cleaned:
        return "", cleaned
    label, text = cleaned.split(":", 1)
    return label.strip().casefold(), text.strip()


def parse_apeda_packhouses(html: str, *, source_url: str, fetched_at: datetime | None = None) -> list[dict[str, Any]]:
    """Parse APEDA-recognised packhouses as post-harvest logistics facilities.

    A packhouse is not represented as a freight quote or booking. Certificate
    dates are preserved so callers can distinguish published recognition from
    current operational availability.
    """
    timestamp = fetched_at or datetime.now(timezone.utc)
    cards = re.findall(r'<div class="box"[^>]*>(.*?)(?=<div class="box"|<div class="pagination|</section>)', html, flags=re.DOTALL)
    records: dict[str, dict[str, Any]] = {}
    for card in cards:
        values = [value for value in (_html_text(value) for value in re.findall(r"<p[^>]*>(.*?)</p>", card, flags=re.DOTALL)) if value]
        if len(values) < 5:
            continue
        title, address, state = values[:3]
        fields: dict[str, str] = {}
        for value in values[3:]:
            label, text = _label_value(value)
            if not label:
                matched = re.match(r"^(Product\(s\)|Product|Certificate No\.?|Issued On|Valid Upto)\s*(.*)$", value, flags=re.IGNORECASE)
                if matched:
                    label, text = matched.group(1).casefold(), matched.group(2).strip()
            if label:
                fields[label] = text
        products = fields.get("product(s)") or fields.get("product")
        certificate = fields.get("certificate no.") or fields.get("certificate no")
        issued_on = _parse_apeda_date(fields.get("issued on"))
        valid_upto = _parse_apeda_date(fields.get("valid upto"))
        record_id = stable_source_id("apeda-packhouse", certificate or title, address, state)
        records[record_id] = {
            "source_record_id": record_id,
            "listing_type": "logistics",
            "title": title,
            "category": "APEDA recognised packhouse",
            "provider_name": title,
            "description": "APEDA-recognised packhouse / post-harvest facility. Confirm handling scope, capacity, pricing and current availability directly before acting.",
            "location": address,
            "district": None,
            "state": state,
            "price_amount": None,
            "price_currency": "INR",
            "price_unit": None,
            "availability_status": "certificate valid" if valid_upto and valid_upto >= timestamp else "certificate date requires verification",
            "contact_phone": None,
            "contact_email": None,
            "listing_url": source_url,
            "source": "APEDA Agri Exchange recognised packhouse directory",
            "source_url": source_url,
            "observed_at": issued_on,
            "fetched_at": timestamp,
            "metadata": {"facility_type": "packhouse", "products": products, "certificate_number": certificate, "certificate_valid_upto": valid_upto.isoformat() if valid_upto else None},
        }
    return list(records.values())


def parse_apeda_buyers(html: str, *, source_url: str, fetched_at: datetime | None = None) -> list[dict[str, Any]]:
    """Parse public APEDA FarmerConnect importer cards without contact links."""
    timestamp = fetched_at or datetime.now(timezone.utc)
    cards = re.findall(r'<div class="prod-list"[^>]*>(.*?)(?=<div class="prod-list"|<div style="text-align: center"|</section>)', html, flags=re.DOTALL)
    records: dict[str, dict[str, Any]] = {}
    for card in cards:
        title_match = re.search(r"<h3[^>]*>(.*?)</h3>", card, flags=re.DOTALL)
        title = _html_text(title_match.group(1)) if title_match else None
        business_match = re.search(r"Business\s*Type\s*:</strong>\s*&nbsp;\s*([^<\r\n]+)", card, flags=re.IGNORECASE)
        business_type = _html_text(business_match.group(1)) if business_match else None
        address_match = re.search(r"Address\s*:</strong>\s*&nbsp;\s*(.*?)(?:<br|</p>)", card, flags=re.IGNORECASE | re.DOTALL)
        address = _html_text(address_match.group(1)) if address_match else None
        profile_match = re.search(r'<a\s+href="([^"]*/Buyer/BuyerProfile[^"]*)"', card, flags=re.IGNORECASE)
        profile_url = urljoin(source_url, unescape(profile_match.group(1))) if profile_match else source_url
        if not title or not address or (business_type or "").casefold() != "importer":
            continue
        record_id = stable_source_id("apeda-farmerconnect-importer", title, address)
        records[record_id] = {
            "source_record_id": record_id,
            "listing_type": "buyer",
            "title": title,
            "category": "agricultural importer",
            "provider_name": title,
            "description": "APEDA FarmerConnect public importer directory record. Confirm commodity demand, purchase terms and current interest directly before acting.",
            "location": address,
            "district": None,
            "state": None,
            "price_amount": None,
            "price_currency": "INR",
            "price_unit": None,
            "availability_status": "directory listed",
            "contact_phone": None,
            "contact_email": None,
            "listing_url": profile_url,
            "source": "APEDA FarmerConnect importer directory",
            "source_url": source_url,
            "observed_at": None,
            "fetched_at": timestamp,
            "metadata": {"business_type": business_type},
        }
    return list(records.values())


def _with_page(url: str, page: int) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["page"] = str(page)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _page_count(html: str) -> int:
    pages = [int(value) for value in re.findall(r"[?&]page=(\d+)", html, flags=re.IGNORECASE)]
    return max(pages, default=1)


def _fetch_paginated_apeda_records(
    *, source_url: str, timeout: float, parser: Callable[..., list[dict[str, Any]]], max_pages: int, page_delay_seconds: float
) -> list[dict[str, Any]]:
    """Fetch only the publisher's public pagination range, at a small delay."""
    first_page = _fetch_text(_with_page(source_url, 1), timeout)
    last_page = _page_count(first_page)
    target_pages = last_page if max_pages <= 0 else min(last_page, max_pages)
    timestamp = datetime.now(timezone.utc)
    records: dict[str, dict[str, Any]] = {}
    for page in range(1, target_pages + 1):
        html = first_page if page == 1 else _fetch_text(_with_page(source_url, page), timeout)
        for record in parser(html, source_url=source_url, fetched_at=timestamp):
            records[record["source_record_id"]] = record
        if page < target_pages and page_delay_seconds > 0:
            time.sleep(page_delay_seconds)
    return list(records.values())


class _JsonLdParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self._capture = False
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "script" and "ld+json" in (attributes.get("type") or "").casefold():
            self._capture = True
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._capture:
            self.blocks.append("".join(self._parts))
            self._capture = False
            self._parts = []


def _objects(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        output = [value]
        for nested in value.get("@graph", []) if isinstance(value.get("@graph"), list) else []:
            output.extend(_objects(nested))
        return output
    if isinstance(value, list):
        return [item for value_item in value for item in _objects(value_item)]
    return []


def _text(value: Any) -> str | None:
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value).strip() or None
    return None


def _address(value: Any) -> tuple[str | None, str | None, str | None]:
    if not isinstance(value, dict):
        return None, None, None
    location = ", ".join(filter(None, [_text(value.get("streetAddress")), _text(value.get("addressLocality"))])) or None
    return location, _text(value.get("addressLocality")), _text(value.get("addressRegion"))


def _offer(value: Any) -> tuple[float | None, str, str | None]:
    offers = value if isinstance(value, list) else [value]
    for offer in offers:
        if not isinstance(offer, dict):
            continue
        try:
            price = float(offer.get("price")) if offer.get("price") is not None else None
        except (TypeError, ValueError):
            price = None
        if price is not None and price >= 0:
            return price, _text(offer.get("priceCurrency")) or "INR", _text(offer.get("unitText"))
    return None, "INR", None


def parse_jsonld_listings(
    html: str, *, source_url: str, source_name: str, listing_type: str, fetched_at: datetime | None = None
) -> list[dict[str, Any]]:
    """Map publisher-provided Product/Service/Business JSON-LD into directory records."""
    normalized_type = listing_type.strip().casefold()
    if normalized_type not in ALLOWED_LISTING_TYPES:
        raise ValueError(f"Unsupported marketplace listing type: {listing_type}")
    parser = _JsonLdParser()
    parser.feed(html)
    timestamp = fetched_at or datetime.now(timezone.utc)
    records: dict[str, dict[str, Any]] = {}
    supported = {"product", "service", "localbusiness", "organization", "store"}
    for block in parser.blocks:
        try:
            values = _objects(json.loads(block))
        except json.JSONDecodeError:
            continue
        for item in values:
            item_types = item.get("@type")
            names = {str(value).casefold() for value in (item_types if isinstance(item_types, list) else [item_types]) if value}
            if not names.intersection(supported):
                continue
            title = _text(item.get("name"))
            if not title:
                continue
            location, district, state = _address(item.get("address"))
            price, currency, unit = _offer(item.get("offers"))
            listing_url = _text(item.get("url")) or source_url
            record_id = stable_source_id("marketplace", normalized_type, source_url, title, listing_url)
            records[record_id] = {
                "source_record_id": record_id,
                "listing_type": normalized_type,
                "title": title,
                "category": _text(item.get("category")),
                "provider_name": _text(item.get("brand")) or _text(item.get("legalName")) or source_name,
                "description": _text(item.get("description")),
                "location": location,
                "district": district,
                "state": state,
                "price_amount": price,
                "price_currency": currency,
                "price_unit": unit,
                "contact_phone": _text(item.get("telephone")),
                "contact_email": _text(item.get("email")),
                "listing_url": listing_url,
                "source": source_name,
                "source_url": source_url,
                "observed_at": None,
                "fetched_at": timestamp,
            }
    return list(records.values())


def fetch_marketplace_records(*, source_url: str, source_name: str, listing_type: str, timeout: float) -> list[dict[str, Any]]:
    try:
        html = _fetch_text(source_url, timeout)
    except SourceFetchError:
        raise
    return parse_jsonld_listings(html, source_url=source_url, source_name=source_name, listing_type=listing_type)


def fetch_apeda_exporter_records(
    *, source_url: str, timeout: float, max_pages: int = 1, page_delay_seconds: float = 0.0
) -> list[dict[str, Any]]:
    return _fetch_paginated_apeda_records(
        source_url=source_url,
        timeout=timeout,
        parser=parse_apeda_exporters,
        max_pages=max_pages,
        page_delay_seconds=page_delay_seconds,
    )


def fetch_apeda_packhouse_records(
    *, source_url: str, timeout: float, max_pages: int = 1, page_delay_seconds: float = 0.0
) -> list[dict[str, Any]]:
    return _fetch_paginated_apeda_records(
        source_url=source_url,
        timeout=timeout,
        parser=parse_apeda_packhouses,
        max_pages=max_pages,
        page_delay_seconds=page_delay_seconds,
    )


def fetch_apeda_buyer_records(
    *, source_url: str, timeout: float, max_pages: int = 1, page_delay_seconds: float = 0.0
) -> list[dict[str, Any]]:
    return _fetch_paginated_apeda_records(
        source_url=source_url,
        timeout=timeout,
        parser=parse_apeda_buyers,
        max_pages=max_pages,
        page_delay_seconds=page_delay_seconds,
    )
