import json
from datetime import datetime, timezone
from pathlib import Path

from app.scraping.sources import _market_record, parse_kharif_msp, parse_rabi_msp, stable_source_id


FETCHED_AT = datetime(2026, 8, 18, tzinfo=timezone.utc)


def test_market_record_maps_modal_price_without_inventing_arrivals():
    record = _market_record(
        {
            "state": "Punjab",
            "district": "Ludhiana",
            "market": "Ludhiana APMC",
            "commodity": "Wheat",
            "variety": "Dara",
            "grade": "FAQ",
            "arrival_date": "17/08/2026",
            "min_price": "2400",
            "max_price": "2700",
            "modal_price": "2585",
        },
        FETCHED_AT,
    )

    assert record is not None
    assert record["price_per_quintal"] == 2585
    assert record["min_price_per_quintal"] == 2400
    assert record["max_price_per_quintal"] == 2700
    assert record["arrival_quintals"] is None
    assert record["source"] == "AGMARKNET via data.gov.in"


def test_market_source_id_is_stable_and_changes_with_observation_identity():
    first = stable_source_id("agmarknet", "Punjab", "Wheat", "2026-08-17")
    second = stable_source_id("AGMARKNET", " punjab ", "wheat", "2026-08-17")
    next_day = stable_source_id("agmarknet", "Punjab", "Wheat", "2026-08-18")
    assert first == second
    assert first != next_day


def test_pib_msp_table_parsers_handle_varieties_and_plain_rows():
    kharif_html = """
    <table>
      <tr><th>S. No.</th><th>Crops</th><th>MSP 2026-27</th></tr>
      <tr><td>1.</td><td>Paddy</td><td>Common</td><td>2441</td><td>1627</td><td>50</td><td>2369</td><td>1310</td><td>72</td><td>1131</td></tr>
      <tr><td></td><td>Grade A^</td><td>2461</td><td>-</td><td>-</td><td>2389</td><td>1345</td><td>72</td><td>1116</td></tr>
      <tr><td>3.</td><td>Bajra</td><td>2900</td><td>1858</td><td>56</td><td>2775</td></tr>
    </table>
    """
    rabi_html = """
    <table>
      <tr><th>Crops</th><th>MSP RMS 2026-27</th></tr>
      <tr><td>Wheat</td><td>2585</td><td>1239</td></tr>
    </table>
    """

    kharif = parse_kharif_msp(
        kharif_html, marketing_year="2026-27", source_url="https://pib.gov.in/kharif", fetched_at=FETCHED_AT
    )
    rabi = parse_rabi_msp(
        rabi_html, marketing_year="2026-27", source_url="https://pib.gov.in/rabi", fetched_at=FETCHED_AT
    )

    assert [(row["crop_name"], row["variety"], row["msp_price_per_quintal"]) for row in kharif] == [
        ("Paddy", "Common", 2441),
        ("Paddy", "Grade A", 2461),
        ("Bajra", None, 2900),
    ]
    assert rabi[0]["crop_name"] == "Wheat"
    assert rabi[0]["msp_price_per_quintal"] == 2585


def test_n8n_workflow_is_active_and_uses_the_protected_sync_endpoint():
    workflow_path = Path(__file__).parents[1] / "n8n" / "universal-data-sync.json"
    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    request_node = next(node for node in workflow["nodes"] if node["id"] == "sync-request")

    assert workflow["active"] is True
    assert workflow["settings"]["timezone"] == "Asia/Kolkata"
    assert "/internal/universal-data/sync" in request_node["parameters"]["url"]
    headers = request_node["parameters"]["headerParameters"]["parameters"]
    assert headers[0]["name"] == "X-Ingestion-Token"
