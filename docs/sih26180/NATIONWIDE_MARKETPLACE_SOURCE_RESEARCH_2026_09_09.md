# Nationwide Marketplace Source Research

## Scope

This source plan supports a read-only Indian farm-discovery directory. A record
may help a farmer discover a provider or facility, but it must never imply that
the provider is available, certified for the farmer's need, offering a current
price, or accepting a booking.

## Source matrix

| Marketplace tab | Source | What is published | Current ingestion decision | Important limit |
| --- | --- | --- | --- | --- |
| Machinery | [Government of India FARMS / KisanRath](https://agrimachinery.nic.in/CHCApp/Help) | CHC provider/vehicle records, source-published coordinates, contact and rate fields | Import public CHC feed and dashboard snapshots | Published status/rate is not a guaranteed booking or availability |
| Exporters | [APEDA Agri Exchange registered exporters](https://agriexchange.apeda.gov.in/AgriDirectory/Exporter/Exporters) | Exporter name, address, commodities and state across public pages | Import all publisher-advertised pages, subject to configured cap | Never follow protected contact controls |
| Buyers | [APEDA FarmerConnect importer directory](https://farmerconnect.apeda.gov.in/Buyer/BuyerDirectory?BusinessType=Importer&Commodities=All&Country=All&Culture=en) | Public importer name, business type, address and profile link | Import only cards published as `Importer` | Directory presence is not an active purchase order or demand signal |
| Logistics / post-harvest | [APEDA recognised packhouses](https://agriexchange.apeda.gov.in/AgriDirectory/SProvider/Index) | Facility name, address, products, recognition certificate and dates | Import as `logistics` / packhouse facilities | A packhouse is not a transport operator or a capacity quote |
| Seed reference | [ICAR notified field-crop varieties](https://www.data.gov.in/catalog/list-field-crops-varieties-hybrids-released-and-notified) and [horticulture varieties](https://kerala.data.gov.in/catalog/horticulture-crops-varieties) | Variety/reference data | Keep as a separate agronomy catalog after source-date and license validation | These datasets are older reference material, not seller stock or a recommendation by themselves |
| Fertilizer reference | [Department of Fertilizers e-Urvarak / iFMS](https://urvarak.nic.in/) | Public aggregate availability and PMKSK coverage reporting | Use only after a stable published endpoint is validated | It is not a current retailer-contact or per-shop stock directory |
| Fertilizer dealer coverage | [Department of Fertilizers dealer-count dataset](https://data.gov.in/catalog/details-number-dealers-each-district-india) | District-level dealer counts | Do not show as current retail inventory; retain only as historical coverage evidence if imported | Dataset update shown by portal is 2014 |
| Local discovery supplement | [OpenStreetMap / Overpass](https://dev.overpass-api.de/overpass-doc/en/) | Community-mapped POIs by geographic tag | Optional, location-bounded discovery adapter only | Coverage varies; retain OSM attribution and ODbL obligations |

## Evidence and source boundaries

### Machinery

FARMS publishes a public KisanRath API help page that lists the CHC data route
and a public provider/vehicle contract. The existing service uses that public
feed rather than attempting to bypass encrypted provider-detail flows. The
source can support nearby machinery discovery because it includes provider and
vehicle data, but a farmer still needs to call the provider to confirm price,
fuel/operator inclusion, service radius and timing.

### Exporters

APEDA's registered-exporter directory exposes cards with name, address,
commodity category and state, as well as a finite public page range. It is the
best nationwide official source for the Exporters tab. The importer stores the
published directory fields and page provenance, but not any data behind the
contact button.

### Buyers

The APEDA FarmerConnect directory supports a public `BusinessType=Importer`
filter. This is an appropriate source for a buyer-discovery tab because the
publisher identifies these records as importers. It is deliberately not treated
as a buy lead: buyer demand, required grade, volume, delivery term and price
must be confirmed outside KisanSathi.

### Logistics and post-harvest facilities

APEDA publishes a recognised-packhouse directory with facility/product and
certificate fields. It materially improves the farmer's post-harvest path,
especially for export-oriented fruit and vegetable crops. The UI and agent must
call it a packhouse or post-harvest facility, not a freight service. Certificate
expiry is displayed as source evidence and not a legal eligibility decision.

### Seeds

The ICAR/DARE entries on the Open Government Data platform describe notified
field-crop and horticulture varieties. They are useful to enrich crop-stage and
variety-selection reference data. Their published catalog dates are old, so
they must carry source date and a `reference_only` label. They cannot populate
a live Seed Marketplace tab because neither stock, certified dealer, price nor
regional inventory is published through these catalog pages.

### Fertilizers

The Department of Fertilizers describes e-Urvarak/iFMS as a public reporting
system for availability, demand/supply and PMKSK installation information.
This can support district-level availability context after endpoint validation.
It is not evidence that a particular retailer has a particular product today.
The data.gov.in dealer-count catalog is historic district coverage, not a
real-time directory, and must not be rendered as local availability.

### OpenStreetMap as a conditional supplement

OpenStreetMap can provide public POIs such as agricultural-supply shops, storage
and transport-related facilities near a field. Overpass is intended for
structured tag/location searches. OSM data is licensed under ODbL; any use must
show OpenStreetMap attribution and preserve applicable share-alike obligations.
Because tags and coverage are community-maintained, the importer should run
only for a farmer-selected bounded area, retain tag evidence and never mark a
result as verified or available.

## Implemented ingestion program

The backend now has three explicit APEDA adapters:

1. `apeda_exporters` follows the registered-exporter public page range.
2. `apeda_buyers` follows FarmerConnect public importer pages and ignores
   contact links/query-string values.
3. `apeda_packhouses` follows recognised-packhouse pages and preserves product,
   certificate number, issued date and certificate-valid-until metadata.

The source registry, page caps and request delay are configured through:

```text
MARKETPLACE_DIRECTORY_SOURCES_JSON
APEDA_EXPORTER_MAX_PAGES
APEDA_BUYER_MAX_PAGES
APEDA_PACKHOUSE_MAX_PAGES
APEDA_DIRECTORY_PAGE_DELAY_SECONDS
```

`0` means the complete public page range. A positive cap is appropriate for
development or recovery testing. Records are upserted by stable source ID,
retain `source`, `source_url` and `fetched_at`, and are never silently replaced
with placeholder supplier data.

## Recommended data model and operational rules

| Field | Rule |
| --- | --- |
| `source_record_id` | Deterministic source-native identity; never use a generated UI ID |
| `source`, `source_url`, `listing_url`, `fetched_at` | Required on every directory row |
| `listing_type` | Must distinguish machinery, exporter, buyer, logistics, seed and fertilizer |
| `record_kind` | Keep provider facility records separate from aggregate network status |
| `availability_status` | Only publisher wording or a narrowly derived certificate-date status; never infer live stock/capacity |
| Contact details | Store only clearly public source fields; never scrape protected/contact-action values |
| Price | Store only a publisher-disclosed dated rate with unit; never estimate a supplier quote |
| Geographic distance | Calculate locally from published coordinates; label the approximation and do not send farm pins to sources |

## Rollout order

1. Refresh APEDA and FARMS records into MongoDB and validate counts per
   `listing_type`.
2. Display category coverage and source timestamps in the frontend.
3. Add ICAR varieties as a dated reference catalog, separate from vendor
   discovery.
4. Add fertilizer district-availability only after a stable e-Urvarak endpoint
   and freshness policy are tested.
5. Add a bounded OSM location importer only with visible attribution, an ODbL
   review and field-level result QA.
6. Add commercial/Google Places sources only after obtaining a key, reviewing
   provider terms and building an explicit opt-in adapter; do not scrape search
   result pages.

## Sources

1. Government of India, Ministry of Agriculture & Farmers Welfare, [FARMS CHC API Help](https://agrimachinery.nic.in/CHCApp/Help). Accessed 2026-09-09.
2. Agricultural and Processed Food Products Export Development Authority,
   [List of Registered Exporters](https://agriexchange.apeda.gov.in/AgriDirectory/Exporter/Exporters). Accessed 2026-09-09.
3. Agricultural and Processed Food Products Export Development Authority,
   [FarmerConnect Importer Directory](https://farmerconnect.apeda.gov.in/Buyer/BuyerDirectory?BusinessType=Importer&Commodities=All&Country=All&Culture=en). Accessed 2026-09-09.
4. Agricultural and Processed Food Products Export Development Authority,
   [Recognised Packhouses](https://agriexchange.apeda.gov.in/AgriDirectory/SProvider/Index). Accessed 2026-09-09.
5. Indian Council of Agricultural Research / data.gov.in, [List of field crops varieties hybrids released and notified](https://www.data.gov.in/catalog/list-field-crops-varieties-hybrids-released-and-notified). Accessed 2026-09-09.
6. Indian Council of Agricultural Research / data.gov.in, [Horticulture Crops Varieties](https://kerala.data.gov.in/catalog/horticulture-crops-varieties). Accessed 2026-09-09.
7. Department of Fertilizers, [iFMS Dashboard](https://urvarak.nic.in/). Accessed 2026-09-09.
8. Department of Fertilizers / data.gov.in, [Details of Number of Dealers in Each District of India](https://data.gov.in/catalog/details-number-dealers-each-district-india). Accessed 2026-09-09.
9. OpenStreetMap Foundation, [Copyright and License](https://www.openstreetmap.org/copyright), and Overpass API, [User’s Manual](https://dev.overpass-api.de/overpass-doc/en/). Accessed 2026-09-09.
