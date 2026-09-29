# Aman — non-ML data, discovery, and calculation functions

**Status: 6 September 2026.** The API is the single source of truth; the React frontend and MCP tools call the same routes. This matrix distinguishes real provider-backed data from source-configured discovery and explicit-input calculations.

| Farmer capability | Backend API/service | Frontend | AI tool | Data status |
|---|---|---|---|---|
| Mandi latest/history/trend/net comparison | `/market-prices/*`, `services/market.py` | Market, Finance | `get_market_summary`, `get_market_price`, `get_nearby_mandi_prices`, `get_market_history`, `get_market_trend`, `compare_mandis` | AGMARKNET/data.gov.in ingestion |
| MSP | `/msp/by-crop/{crop}`, `/msp/compare-market` | Market/Finance context | `get_msp`, `compare_msp_with_market` | PIB ingestion plus sourced mandi records |
| Weather and warnings | `/v1/weather`, `/v1/weather/alerts` | Weather, dashboard | `get_weather_for_field`, `get_weather_alerts_for_field` | Open-Meteo provider/cache |
| Government scheme discovery | `/gov-schemes/*` | Government Schemes | `find_government_schemes`, `get_scheme_details`, `check_scheme_eligibility` | structured catalog; policy still needs approved sources |
| Seed/fertilizer recommendation | `/seeds/recommend`, `/fertilizer/recommend` | marketplace filters | `recommend_seeds`, `recommend_fertilizers` | catalog-only; no invented agronomy |
| Machinery discovery | `/machinery-rentals` | Machinery Rentals | `list_machinery_rentals`, `find_machinery` | structured catalog |
| Inputs, logistics, buyers, exporters | `/marketplace/listings` | Marketplace | `search_marketplace_listings`, category-specific `find_*` tools | approved-source ingestion; APEDA exporter directory is enabled by default |
| Directory configuration state | `/marketplace/status` | Marketplace API client | `get_marketplace_status` | configuration only; not stock/availability |
| Quote comparison and logistics total | `POST /marketplace/compare-quotes` | assistant/API-ready | `compare_marketplace_quotes`, `compare_machinery_costs`, `compare_logistics_options`, `calculate_logistics_cost` | farmer/supplier-provided quote inputs |

## Explicitly not implemented as fake automation

- booking machinery, transport or storage;
- buying seed/fertilizer, selling crop or applying for schemes;
- exporter eligibility, customs compliance or export cost without destination, commodity, lot/grade and a verified rules/quote source;
- price, stock, distance, rating or availability where the configured source did not publish it.
- tax, insurance, exchange-rate or other unpublished cost in a quote comparison.

These belong to a later partner/API integration. The present system lets the farmer discover verifiable records and then contact the source directly.
