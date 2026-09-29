from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


MARKET_RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
MARKET_DATASET_URL = "https://www.data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi"
MARKET_API_URL = f"https://api.data.gov.in/resource/{MARKET_RESOURCE_ID}"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36 "
    "KisanSathi-OfficialDataIngestion/1.0"
)


class SourceFetchError(RuntimeError):
    pass


def stable_source_id(*parts: str) -> str:
    canonical = "|".join(part.strip().casefold() for part in parts)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _fetch_bytes(url: str, timeout: float) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json,text/html;q=0.9"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read()
    except HTTPError as exc:
        raise SourceFetchError(f"Official source returned HTTP {exc.code}") from exc
    except (URLError, TimeoutError) as exc:
        raise SourceFetchError(f"Official source could not be reached: {exc.reason if isinstance(exc, URLError) else exc}") from exc


def _fetch_text(url: str, timeout: float) -> str:
    return _fetch_bytes(url, timeout).decode("utf-8", errors="replace")


def discover_data_gov_api_key(timeout: float) -> str:
    """Read the public API key rendered by data.gov.in for this public resource.

    A configured key always takes precedence. This fallback does not persist the
    portal-rendered key and fails closed if the resource page stops publishing it.
    """

    page = _fetch_text(MARKET_DATASET_URL, timeout)
    resource_position = page.find(MARKET_RESOURCE_ID)
    resource_fragment = page[resource_position:resource_position + 4000] if resource_position >= 0 else ""
    candidates = re.findall(r"api-key=([A-Za-z0-9]+)", resource_fragment)
    if not candidates:
        raise SourceFetchError("DATA_GOV_IN_API_KEY is not configured and the official resource page exposed no public API key")
    return candidates[0]


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError:
        return None


def _market_record(raw: dict[str, Any], fetched_at: datetime) -> dict[str, Any] | None:
    required = ["state", "district", "market", "commodity", "arrival_date", "modal_price"]
    if any(not str(raw.get(field, "")).strip() for field in required):
        return None
    try:
        observed_at = datetime.strptime(str(raw["arrival_date"]).strip(), "%d/%m/%Y").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    modal = _number(raw.get("modal_price"))
    if modal is None or modal <= 0:
        return None
    state = str(raw["state"]).strip()
    district = str(raw["district"]).strip()
    market = str(raw["market"]).strip()
    commodity = str(raw["commodity"]).strip()
    variety = str(raw.get("variety") or "").strip() or None
    grade = str(raw.get("grade") or "").strip() or None
    return {
        "source_record_id": stable_source_id(
            "agmarknet", state, district, market, commodity, variety or "", grade or "", observed_at.date().isoformat()
        ),
        "crop_name": commodity,
        "mandi_name": market,
        "price_per_quintal": modal,
        "min_price_per_quintal": _number(raw.get("min_price")),
        "max_price_per_quintal": _number(raw.get("max_price")),
        "date": observed_at,
        "state": state,
        "district": district,
        "arrival_quintals": None,
        "variety": variety,
        "grade": grade,
        "source": "AGMARKNET via data.gov.in",
        "source_url": MARKET_DATASET_URL,
        "observed_at": observed_at,
        "fetched_at": fetched_at,
    }


def fetch_market_records(
    *, api_key: str, timeout: float, page_size: int = 1000, max_records: int = 0
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    resolved_key = api_key.strip() or discover_data_gov_api_key(timeout)
    fetched_at = datetime.now(timezone.utc)
    offset = 0
    records: list[dict[str, Any]] = []
    rejected = 0
    total = 0
    while True:
        limit = page_size
        if max_records:
            limit = min(limit, max_records - offset)
            if limit <= 0:
                break
        query = urlencode({"api-key": resolved_key, "format": "json", "offset": offset, "limit": limit})
        try:
            payload = json.loads(_fetch_bytes(f"{MARKET_API_URL}?{query}", timeout))
        except json.JSONDecodeError as exc:
            raise SourceFetchError("Official market source returned invalid JSON") from exc
        if offset == 0:
            try:
                total = int(payload.get("total", 0))
            except (TypeError, ValueError):
                total = 0
        page = payload.get("records")
        if not isinstance(page, list):
            raise SourceFetchError("Official market source response did not contain a records list")
        for raw in page:
            record = _market_record(raw, fetched_at) if isinstance(raw, dict) else None
            if record is None:
                rejected += 1
            else:
                records.append(record)
        offset += len(page)
        if not page or offset >= total or (max_records and offset >= max_records):
            break
    return records, {"reported_total": total, "fetched": offset, "accepted": len(records), "rejected": rejected}


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self._table_depth = 0
        self._current_table: list[list[str]] | None = None
        self._current_row: list[str] | None = None
        self._current_cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self._table_depth += 1
            if self._table_depth == 1:
                self._current_table = []
        elif self._table_depth == 1 and tag == "tr":
            self._current_row = []
        elif self._table_depth == 1 and tag in {"td", "th"} and self._current_row is not None:
            self._current_cell = []

    def handle_data(self, data: str) -> None:
        if self._current_cell is not None:
            self._current_cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._table_depth == 1 and tag in {"td", "th"} and self._current_cell is not None:
            value = re.sub(r"\s+", " ", " ".join(self._current_cell)).strip()
            if self._current_row is not None:
                self._current_row.append(value)
            self._current_cell = None
        elif self._table_depth == 1 and tag == "tr" and self._current_row is not None:
            if any(self._current_row) and self._current_table is not None:
                self._current_table.append(self._current_row)
            self._current_row = None
        elif tag == "table" and self._table_depth:
            if self._table_depth == 1 and self._current_table is not None:
                self.tables.append(self._current_table)
                self._current_table = None
            self._table_depth -= 1


def extract_html_tables(html: str) -> list[list[list[str]]]:
    parser = _TableParser()
    parser.feed(html)
    return parser.tables


def _clean_label(value: str) -> str:
    return re.sub(r"\s*\^\s*$", "", value).strip()


def _msp_record(
    *, crop: str, variety: str | None, price: float, season: str, marketing_year: str, source_url: str, fetched_at: datetime
) -> dict[str, Any]:
    crop = _clean_label(crop)
    variety = _clean_label(variety) if variety else None
    return {
        "source_record_id": stable_source_id("pib-msp", season, marketing_year, crop, variety or ""),
        "crop_name": crop,
        "variety": variety,
        "msp_price_per_quintal": price,
        "season": season,
        "marketing_year": marketing_year,
        "procurement_centres": [],
        "source": "Press Information Bureau, Government of India",
        "source_url": source_url,
        "fetched_at": fetched_at,
    }


def parse_kharif_msp(html: str, *, marketing_year: str, source_url: str, fetched_at: datetime) -> list[dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    current_crop: str | None = None
    for table in extract_html_tables(html):
        for cells in table:
            first = cells[0].strip() if cells else ""
            numbered = bool(re.fullmatch(r"\d+\.?", first))
            crop: str | None = None
            variety: str | None = None
            price: float | None = None
            if numbered and len(cells) >= 3:
                crop = cells[1]
                current_crop = crop
                if len(cells) >= 10:
                    variety, price = cells[2], _number(cells[3])
                else:
                    price = _number(cells[2])
            elif first == "" and current_crop and len(cells) >= 3 and _number(cells[2]) is not None:
                crop, variety, price = current_crop, cells[1], _number(cells[2])
            if crop and price and price > 0:
                record = _msp_record(
                    crop=crop, variety=variety, price=price, season="Kharif",
                    marketing_year=marketing_year, source_url=source_url, fetched_at=fetched_at,
                )
                output[record["source_record_id"]] = record
    return list(output.values())


def parse_rabi_msp(html: str, *, marketing_year: str, source_url: str, fetched_at: datetime) -> list[dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for table in extract_html_tables(html):
        for cells in table:
            if len(cells) < 2 or "crop" in cells[0].casefold():
                continue
            price = _number(cells[1])
            if not price or price <= 0:
                continue
            record = _msp_record(
                crop=cells[0], variety=None, price=price, season="Rabi",
                marketing_year=marketing_year, source_url=source_url, fetched_at=fetched_at,
            )
            output[record["source_record_id"]] = record
    return list(output.values())


def fetch_msp_records(
    *, kharif_url: str, rabi_url: str, marketing_year: str, timeout: float
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    fetched_at = datetime.now(timezone.utc)
    kharif = parse_kharif_msp(
        _fetch_text(kharif_url, timeout), marketing_year=marketing_year, source_url=kharif_url, fetched_at=fetched_at
    )
    rabi = parse_rabi_msp(
        _fetch_text(rabi_url, timeout), marketing_year=marketing_year, source_url=rabi_url, fetched_at=fetched_at
    )
    return kharif + rabi, {"kharif": len(kharif), "rabi": len(rabi), "accepted": len(kharif) + len(rabi)}
