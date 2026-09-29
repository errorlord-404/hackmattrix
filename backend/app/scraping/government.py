"""Adapters for bounded, official government agriculture sources.

The adapters intentionally ingest only public pages/endpoints published by the
government. They preserve source URLs and fetch times. The FARMS KisanRath CHC
feed contains provider/vehicle records and published cost fields; the separate
dashboard count feed remains an explicitly labelled aggregate health signal.
Neither source is treated as a booking or a guarantee of current availability.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from typing import Any

from app.scraping.sources import SourceFetchError, USER_AGENT, _fetch_text, stable_source_id


MAHADBT_FARMER_SCHEME_INDEX = "https://mahadbt.maharashtra.gov.in/Farmer/SchemeData/SchemeData?str=E9DDFA703C38E51A23C0254248DAFF28"
FARMS_PROVIDER_COUNTS_URL = "https://agrimachinery.nic.in/GraphReport/SMAMFmtti/ServiceData2.asmx/GetCHCAppServiceProviders"
FARMS_HIRING_STATUS_URL = "https://agrimachinery.nic.in/GraphReport/SMAMFmtti/ServiceData2.asmx/GetStatusofImplementHiring"
FARMS_CHC_DATA_URL = "https://agrimachinery.nic.in/CHCApp/KisanRath/getChcData"


def _clean_html(value: str) -> str:
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"[ \t\r\f\v]+", " ", unescape(value)).strip()


def _list_items(fragment: str) -> list[str]:
    return [item for item in (_clean_html(value) for value in re.findall(r"<li[^>]*>(.*?)</li>", fragment, re.I | re.S)) if item]


def parse_mahadbt_scheme_links(html: str, *, index_url: str) -> list[dict[str, str]]:
    """Extract the finite scheme links rendered in MahaDBT's farmer page."""
    links: dict[str, dict[str, str]] = {}
    for href, label in re.findall(r'<a\b[^>]*href=["\']([^"\']*SchemeData/SchemeData\?str=[^"\']+)["\'][^>]*>(.*?)</a>', html, re.I | re.S):
        name = _clean_html(label)
        if not name:
            continue
        url = urljoin(index_url, unescape(href))
        key_match = re.search(r"[?&]str=([A-Za-z0-9]+)", url)
        if key_match:
            links[key_match.group(1)] = {"name": name, "url": url}
    return list(links.values())


def _section(html: str, heading: str) -> str:
    match = re.search(rf"<h3[^>]*>\s*{re.escape(heading)}\s*</h3>(.*?)(?=<h3\b|</div>\s*</div>\s*</div>|$)", html, re.I | re.S)
    return match.group(1) if match else ""


def parse_mahadbt_scheme_detail(html: str, *, source_url: str, fallback_name: str, fetched_at: datetime | None = None) -> dict[str, Any] | None:
    heading = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.I | re.S)
    name = _clean_html(heading.group(1)) if heading else fallback_name
    if not name:
        return None
    overview = _clean_html(_section(html, "Overview"))
    benefit_fragment = _section(html, "Benefit")
    eligibility_fragment = _section(html, "Eligibility")
    documents_fragment = _section(html, "Required Documents")
    benefit = _clean_html(benefit_fragment) or "Benefits are described in the official scheme documents."
    eligibility = _list_items(eligibility_fragment)
    documents = _list_items(documents_fragment)
    if not overview:
        overview = "Official scheme details are published on the MahaDBT Farmer Portal."
    timestamp = fetched_at or datetime.now(timezone.utc)
    return {
        "source_record_id": stable_source_id("mahadbt-farmer-scheme", source_url),
        "name": name,
        "description": overview,
        "eligibility_criteria": eligibility,
        "benefits": benefit,
        "required_documents": documents,
        "application_deadline": None,
        "application_steps": ["Review eligibility and required documents on the official MahaDBT portal.", "Apply through the official MahaDBT Farmer Portal when applications are open."],
        "official_source_url": source_url,
        "applicable_states": ["Maharashtra"],
        "source": "MahaDBT Farmer Portal",
        "fetched_at": timestamp,
    }


def fetch_mahadbt_scheme_records(*, index_url: str = MAHADBT_FARMER_SCHEME_INDEX, timeout: float = 30.0, max_schemes: int = 30) -> tuple[list[dict[str, Any]], dict[str, int]]:
    index_html = _fetch_text(index_url, timeout)
    links = parse_mahadbt_scheme_links(index_html, index_url=index_url)
    records: list[dict[str, Any]] = []
    rejected = 0
    for link in links[:max_schemes]:
        try:
            detail = parse_mahadbt_scheme_detail(_fetch_text(link["url"], timeout), source_url=link["url"], fallback_name=link["name"])
        except SourceFetchError:
            raise
        if detail:
            records.append(detail)
        else:
            rejected += 1
    return records, {"discovered": len(links), "accepted": len(records), "rejected": rejected}


def _post_json(url: str, timeout: float) -> Any:
    request = Request(url, data=b"{}", headers={"User-Agent": USER_AGENT, "Accept": "application/json", "Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        raise SourceFetchError(f"Official source returned HTTP {exc.code}") from exc
    except (URLError, TimeoutError) as exc:
        raise SourceFetchError(f"Official source could not be reached: {exc.reason if isinstance(exc, URLError) else exc}") from exc
    try:
        # A legacy ASP.NET endpoint appends a second ``{"d":null}`` envelope
        # after the valid payload. Decode the first complete JSON value and
        # deliberately ignore only that known transport suffix.
        outer, _ = json.JSONDecoder().raw_decode(raw.lstrip())
        value = outer.get("d") if isinstance(outer, dict) else None
        if isinstance(value, str):
            return json.loads(value)
        return outer
    except json.JSONDecodeError as exc:
        raise SourceFetchError("Official FARMS endpoint returned invalid JSON") from exc


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _observed_at(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    for fmt in ("%m/%d/%Y %I:%M:%S %p", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _address_parts(value: Any) -> tuple[str | None, str | None, str | None]:
    address = re.sub(r"\s+", " ", str(value or "")).strip(" ,") or None
    if not address:
        return None, None, None
    parts = [part.strip() for part in address.split(",") if part.strip()]
    state = parts[-1].title() if parts else None
    district = parts[-2].title() if len(parts) > 1 else None
    return address, district, state


def _farms_chc_rows(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or payload.get("status") != "S" or not isinstance(payload.get("listCHC"), list):
        raise SourceFetchError("Official FARMS CHC endpoint returned no usable provider data")
    return [row for row in payload["listCHC"] if isinstance(row, dict)]


def parse_farms_chc_records(
    payload: dict[str, Any], *, source_url: str = FARMS_CHC_DATA_URL, fetched_at: datetime | None = None,
    max_records: int = 5000,
) -> list[dict[str, Any]]:
    """Map the official public KisanRath CHC feed to source-attributed rentals."""
    timestamp = fetched_at or datetime.now(timezone.utc)
    records: dict[str, dict[str, Any]] = {}
    for provider in _farms_chc_rows(payload):
        transaction_id = str(provider.get("CHCTransactionId") or "").strip()
        agency = str(provider.get("agency_name") or provider.get("contact_person_name") or "").strip()
        if not transaction_id or not agency:
            continue
        location, district, state = _address_parts(provider.get("address"))
        # FARMS sometimes publishes a provider without an address. Preserve
        # that fact instead of dropping the source row, while satisfying the
        # legacy response contract with an explicit non-location label.
        location_missing = not bool(location or district or state)
        location = location or district or state or "Location not provided by FARMS"
        latitude = _number(provider.get("lat"))
        longitude = _number(provider.get("lng"))
        observed_at = _observed_at(provider.get("CHC_LastModifiedDate")) or _observed_at(provider.get("CHC_AddedDate"))
        vehicles = provider.get("chcVehicles") if isinstance(provider.get("chcVehicles"), list) else []
        if not vehicles:
            vehicles = [{}]
        for vehicle in vehicles:
            if not isinstance(vehicle, dict):
                vehicle = {}
            vehicle_id = str(vehicle.get("vehicle_unique_id") or "provider")
            vehicle_type = str(vehicle.get("vehicleType") or "custom hiring equipment").strip()
            record_id = stable_source_id("farms-chc", transaction_id, vehicle_id)
            cost_per_hour = _number(vehicle.get("cost_per_hour"))
            cost_per_acre = _number(vehicle.get("cost_per_acre"))
            records[record_id] = {
                "source_record_id": record_id,
                "record_kind": "provider_listing",
                "listing_type": "machinery",
                "title": f"{vehicle_type} — {agency}",
                "category": vehicle_type.casefold(),
                "provider_name": agency,
                "description": "Official FARMS custom-hiring provider record. Confirm current quote, scope, timing and availability directly before relying on it.",
                "location": location,
                "district": district,
                "state": state,
                "latitude": latitude,
                "longitude": longitude,
                "location_point": {"type": "Point", "coordinates": [longitude, latitude]} if latitude is not None and longitude is not None else None,
                "price_amount": cost_per_hour,
                "price_currency": "INR",
                "price_unit": "per hour" if cost_per_hour is not None else None,
                "contact_phone": str(provider.get("mobile") or "").strip() or None,
                "contact_email": None,
                "listing_url": "https://agrimachinery.nic.in/Index/farmsapp",
                "source": "Government of India FARMS CHC public feed",
                "source_url": source_url,
                "observed_at": observed_at,
                "fetched_at": timestamp,
                "source_status": "active",
                "image_url": str(vehicle.get("vehiclePhotograph") or "").strip() or None,
                "hourly_rate": cost_per_hour,
                "availability_status": "published",
                "metadata": {
                    "chc_transaction_id": transaction_id,
                    "vehicle_unique_id": vehicle_id,
                    "vehicle_count": vehicle.get("numberOfVehicles"),
                    "cost_per_acre": cost_per_acre,
                    "vehicle_status": vehicle.get("vehicle_status"),
                    "user_type": provider.get("UserType"),
                    "state_lgdcode": provider.get("state_lgdcode"),
                    "district_lgdcode": provider.get("district_lgdcode"),
                    "location_missing": location_missing,
                },
            }
            if len(records) >= max_records:
                return list(records.values())
    return list(records.values())


def fetch_farms_chc_records(*, timeout: float = 30.0, lookback_days: int = 365, max_records: int = 5000) -> tuple[list[dict[str, Any]], dict[str, int]]:
    today = datetime.now(timezone.utc).date()
    from_date = today - timedelta(days=max(1, lookback_days))
    url = f"{FARMS_CHC_DATA_URL}?fromdate={from_date.strftime('%d/%m/%Y')}&toDate={today.strftime('%d/%m/%Y')}"
    records = parse_farms_chc_records(_post_json(url, timeout), source_url=FARMS_CHC_DATA_URL, max_records=max_records)
    return records, {"accepted": len(records), "from_date": from_date.isoformat(), "to_date": today.isoformat()}


def _farms_rows(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or payload.get("ResponseCode") != "Success" or not isinstance(payload.get("data"), list):
        raise SourceFetchError("Official FARMS endpoint returned no usable data")
    return [row for row in payload["data"] if isinstance(row, dict)]


def fetch_farms_network_records(*, timeout: float = 30.0) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Return transparent state-level network snapshots, not invented rentals."""
    provider_rows = _farms_rows(_post_json(FARMS_PROVIDER_COUNTS_URL, timeout))
    hiring_rows = _farms_rows(_post_json(FARMS_HIRING_STATUS_URL, timeout))
    hiring_by_state = {str(row.get("StateName") or "").strip().casefold(): row for row in hiring_rows}
    fetched_at = datetime.now(timezone.utc)
    records: list[dict[str, Any]] = []
    for row in provider_rows:
        state = str(row.get("StateName") or "").strip()
        if not state:
            continue
        hiring = hiring_by_state.get(state.casefold(), {})
        counts = {key: value for key, value in {
            "farmer_service_providers": row.get("Farmer"),
            "society_service_providers": row.get("Societies"),
            "entrepreneur_service_providers": row.get("Entrepreneur"),
            "farmer_as_chc": row.get("FarmerAsCHC"),
            "booking_requests": row.get("BookingRequestGenerated"),
            "implement_booking_requests": hiring.get("NoOfUserRequestedForBooking"),
            "implement_bookings": hiring.get("TotalImplementBooking"),
            "implements_hired": hiring.get("NoOfImplementsHired"),
        }.items() if value is not None}
        record_id = stable_source_id("farms-network-status", state)
        records.append({
            "source_record_id": record_id,
            "listing_type": "machinery",
            "title": f"FARMS custom-hiring network — {state.title()}",
            "category": "government custom hiring network",
            "provider_name": "Government of India FARMS dashboard",
            "description": "Official state-level network status. This is not an individual rental listing; verify equipment, rate and availability through the official FARMS app before acting.",
            "location": state.title(), "district": None, "state": state.title(),
            "price_amount": None, "price_currency": "INR", "price_unit": None,
            "contact_phone": None, "contact_email": None,
            "listing_url": "https://agrimachinery.nic.in/Index/farmsapp",
            "source": "Government of India FARMS dashboard", "source_url": FARMS_PROVIDER_COUNTS_URL,
            "observed_at": None, "fetched_at": fetched_at,
            "record_kind": "network_status", "metadata": counts,
        })
    return records, {"provider_states": len(provider_rows), "hiring_states": len(hiring_rows), "accepted": len(records)}
