# Marketplace directory ingestion

KisanSathi's marketplace is a **discovery directory**, not an e-commerce or
booking system. It exposes source-attributed public records for machinery,
seed, fertilizer, logistics, buyers and exporters through:

- `GET /marketplace/listings`
- frontend route `/marketplace`
- MCP tool `search_marketplace_listings`

## Source policy

The importer does not search Google, scrape login-protected sites, bypass rate
limits, or guess provider contacts/prices. It only reads JSON-LD structured
data published by an administrator-approved HTTPS source. Each resulting row
retains `source`, `source_url`, `listing_url` and `fetched_at`.

Three APEDA public directories are configured as the safe default: registered
exporters, FarmerConnect importers and recognised packhouses. The last is
shown as a post-harvest/logistics facility, not a transport quote. Override the
registry outside version control to add reviewed sources:

```env
MARKETPLACE_DIRECTORY_SOURCES_JSON=[
  {"url":"https://example.org/public-tractor-directory","name":"Example FPO directory","listing_type":"machinery"},
  {"url":"https://example.org/public-logistics-directory","name":"Example logistics directory","listing_type":"logistics"}
]
```

Allowed `listing_type` values are `machinery`, `seed`, `fertilizer`,
`logistics`, `buyer`, and `exporter`. The configured source must be public,
permitted for automated access, and reviewed by the team. A page without
publisher-provided JSON-LD creates no listings.

The approved APEDA adapters are explicit public-directory contracts:

```env
MARKETPLACE_DIRECTORY_SOURCES_JSON=[
  {"url":"https://agriexchange.apeda.gov.in/AgriDirectory/Exporter/Exporters","name":"APEDA registered exporters","listing_type":"exporter","adapter":"apeda_exporters"},
  {"url":"https://farmerconnect.apeda.gov.in/Buyer/BuyerDirectory?BusinessType=Importer&Commodities=All&Country=All&Culture=en","name":"APEDA FarmerConnect importers","listing_type":"buyer","adapter":"apeda_buyers"},
  {"url":"https://agriexchange.apeda.gov.in/AgriDirectory/SProvider/Index","name":"APEDA recognised packhouses","listing_type":"logistics","adapter":"apeda_packhouses"}
]
```

They follow only the pagination range publicly published by APEDA. The exporter
adapter retains exporter name, address, commodity category and state; the buyer
adapter retains only public importer name, address and public profile URL; the
packhouse adapter retains facility details and source-published certificate
dates. All three leave protected contact flows alone. They do not decrypt
identifiers, collect button query-string contact data, create a booking, or
claim current inventory, demand, capacity or price.

Set `APEDA_EXPORTER_MAX_PAGES`, `APEDA_BUYER_MAX_PAGES` and
`APEDA_PACKHOUSE_MAX_PAGES` to positive caps for development, or `0` to follow
all advertised pages. `APEDA_DIRECTORY_PAGE_DELAY_SECONDS` adds a small delay
between public-page requests.

## Government refreshes

The universal-data service also supports two source-specific official adapters:

- `gov_schemes` follows the published agricultural links on the [MahaDBT
  Farmer Portal](https://mahadbt.maharashtra.gov.in/) and stores the detail
  page's eligibility/documents with a stable source ID.
- `machinery` reads the public [Government of India FARMS
  dashboard](https://agrimachinery.nic.in/Index/farmsapp). Its current public
  dashboard endpoints expose state-level custom-hiring provider and booking
  counts, stored as `record_kind=network_status`. The public KisanRath CHC feed
  additionally exposes provider/vehicle rows; those are stored as
  `record_kind=provider_listing` with the source-published contact, coordinates
  and cost fields.

The official [FARMS API help](https://agrimachinery.nic.in/CHCApp/Help) also lists
private provider/implement endpoints whose request body requires an
`EncryptedRequest`. We do not reverse-engineer those flows; the public CHC feed
is the approved read-only provider source currently used here.

Run both along with APEDA using:

```powershell
python -m app.scraping --sources gov_schemes,machinery,marketplace
```

`backend/scripts/refresh_live_reference_data.py` performs this refresh and
removes only local directory fixtures after all three sources succeed.

## Run and verify

1. Configure `SCRAPER_WEBHOOK_TOKEN` and the source registry.
2. Trigger `POST /internal/universal-data/sync?sources=marketplace` with
   `X-Ingestion-Token`.
3. Inspect the protected `/internal/universal-data/runs` result for accepted
   counts and per-source errors.
4. Open `/marketplace` or `/machinery`, filter by category/location, and
   inspect each source/fetched timestamp. Network-status rows are discovery
   evidence only; they do not contain a rental quote.

The endpoint and MCP tool only reveal listings. They do not place calls, make
purchases, submit export documents, book transport, or represent a provider's
availability as guaranteed.

## Research-backed data boundaries

The JSON-LD importer intentionally does not attempt to infer records from a
generic page layout. Before adding a source-specific adapter, the team must
review its terms, robots/access policy, rate limit and field mapping. Current
research candidates are:

- APEDA's public [Agri Exchange registered-exporter directory](https://agriexchange.apeda.gov.in/AgriDirectory/Exporter/Exporters), [FarmerConnect importer directory](https://farmerconnect.apeda.gov.in/Buyer/BuyerDirectory?BusinessType=Importer&Commodities=All&Country=All&Culture=en), and [recognised packhouse directory](https://agriexchange.apeda.gov.in/AgriDirectory/SProvider/Index) are covered by source-specific adapters because their public HTML layout is not the JSON-LD contract used by the generic importer.
- The Ministry of Agriculture's [FARMS/custom-hiring information](https://agrimachinery.nic.in/Index/farmsapp) and its public [CHC KisanRath feed](https://agrimachinery.nic.in/CHCApp/Help). The dashboard provides aggregate status, while the CHC feed provides source-published provider/vehicle discovery records. Current availability still requires direct provider verification.
- The Department of Fertilizers' public [e-Urvarak/iFMS](https://urvarak.nic.in/) reporting is useful for aggregate availability and PMKSK coverage, but it is not a verified dealer-contact directory; do not represent it as one. ICAR/data.gov.in variety datasets are seed-selection references, not live seed stock or retailer records.

Do not add an individual commercial directory until its terms, source approval
and adapter test fixture have been committed.
