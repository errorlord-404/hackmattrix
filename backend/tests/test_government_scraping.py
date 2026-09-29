from datetime import datetime, timezone

from app.scraping.government import parse_farms_chc_records, parse_mahadbt_scheme_detail, parse_mahadbt_scheme_links


def test_mahadbt_index_parser_deduplicates_official_scheme_links():
    links = parse_mahadbt_scheme_links(
        '<li><a href="/Farmer/SchemeData/SchemeData?str=ABC">Farm tools</a></li>'
        '<li><a href="/Farmer/SchemeData/SchemeData?str=ABC">Farm tools</a></li>',
        index_url="https://mahadbt.maharashtra.gov.in/Farmer/SchemeData/SchemeData?str=ROOT",
    )
    assert links == [{"name": "Farm tools", "url": "https://mahadbt.maharashtra.gov.in/Farmer/SchemeData/SchemeData?str=ABC"}]


def test_mahadbt_detail_parser_keeps_source_and_does_not_invent_benefit_amount():
    record = parse_mahadbt_scheme_detail(
        """
        <h1>Sub-mission on Farm Mechanization</h1>
        <h3>Overview</h3><ul><li>Improve farm power.</li></ul>
        <h3>Benefit</h3><ul>Refer to official benefit document.</ul>
        <h3>Eligibility</h3><ul><li>Aadhaar Card</li><li>Small farmer</li></ul>
        <h3>Required Documents</h3><ul><li>Aadhaar Card</li></ul>
        """,
        source_url="https://mahadbt.example/scheme?str=ABC",
        fallback_name="Fallback",
        fetched_at=datetime(2026, 9, 9, tzinfo=timezone.utc),
    )
    assert record is not None
    assert record["name"] == "Sub-mission on Farm Mechanization"
    assert record["eligibility_criteria"] == ["Aadhaar Card", "Small farmer"]
    assert record["required_documents"] == ["Aadhaar Card"]
    assert record["source"] == "MahaDBT Farmer Portal"
    assert record["fetched_at"].year == 2026
    assert "₹" not in record["benefits"]


def test_farms_chc_parser_maps_real_provider_vehicle_and_preserves_raw_costs():
    records = parse_farms_chc_records({
        "status": "S",
        "listCHC": [{
            "CHCTransactionId": "1001",
            "agency_name": "Example CHC",
            "contact_person_name": "Operator",
            "mobile": "9876543210",
            "address": "Village, Wardha, Maharashtra",
            "lat": "20.10",
            "lng": "78.30",
            "CHC_LastModifiedDate": "09/09/2026 10:20:00",
            "chcVehicles": [{
                "vehicleType": "Tractor",
                "vehicle_unique_id": "v-1",
                "cost_per_hour": "600.00",
                "cost_per_acre": "1800.00",
                "vehicle_status": "1",
                "vehiclePhotograph": "https://agrimachinery.nic.in/image.png",
            }],
        }],
    }, fetched_at=datetime(2026, 9, 9, tzinfo=timezone.utc))
    assert len(records) == 1
    record = records[0]
    assert record["record_kind"] == "provider_listing"
    assert record["provider_name"] == "Example CHC"
    assert record["state"] == "Maharashtra"
    assert record["district"] == "Wardha"
    assert record["price_amount"] == 600.0
    assert record["metadata"]["cost_per_acre"] == 1800.0
    assert record["source"] == "Government of India FARMS CHC public feed"
    assert record["source_status"] == "active"


def test_farms_chc_parser_keeps_provider_without_address_explicitly_queryable():
    records = parse_farms_chc_records({
        "status": "S",
        "listCHC": [{
            "CHCTransactionId": "1002",
            "agency_name": "Addressless CHC",
            "chcVehicles": [{"vehicleType": "Rotavator", "vehicle_unique_id": "v-2"}],
        }],
    })
    assert len(records) == 1
    assert records[0]["location"] == "Location not provided by FARMS"
    assert records[0]["metadata"]["location_missing"] is True
