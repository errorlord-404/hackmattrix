# Seasonal evidence source decision

Checked: 2026-09-20

## Decision

Do not expose a KisanSathi `get_seasonal_evidence` tool that converts the
current India Meteorological Department (IMD) public pages into a numerical,
field-specific, three-month prediction. The currently verified official
surfaces are publications, dashboards, and PDF bulletins rather than a stable
district/field API with a machine-readable forecast, geography, issue date,
expiry, and uncertainty contract.

The farmer agent must instead use its live web-research capability to open the
applicable official bulletin at decision time, retain the source URL, issue or
publication date, geographic scope, horizon, and stated uncertainty, and say
when no suitable bulletin exists. A five-day backend weather response remains
near-term weather only and must never be relabelled as a seasonal outlook.

## Verified official sources

| Source | What it can support | What it cannot safely support alone |
| --- | --- | --- |
| [IMD seasonal forecast catalogue](https://mausam.imd.gov.in/imd_latest/contents/seasonal_forecast.php) | Finding the current long-range/seasonal product family, including monsoon, northeast monsoon, heat/cold and probability products | A parsed, field-specific recommendation; the catalogue itself does not expose one normalized record per farm. |
| [IMD national agromet ERFS bulletin](https://mausam.imd.gov.in/imd_latest/contents/agromet/advisory/national_english_ERFS.php) | Locating the current national extended-range agromet bulletin and its PDF | A seasonal forecast or local field outcome; it is a separate, bounded extended-range product. |
| [IMD extended-range guidance](https://mausam.imd.gov.in/imd_latest/contents/extendedrangeforecast.php) | Locating weekly rainfall/temperature guidance and distinguishing it from seasonal material | A whole-season crop-water budget or a district-specific yield forecast. |

## Requirements before adding an automated backend adapter

1. An official source must provide a stable document or API locator with an
   explicit issue date, valid horizon, scope, category/units, and update policy.
2. The adapter must preserve the original document URL and retrieval time; it
   must return `unavailable` rather than carry a stale record forward as current.
3. Geography matching must be explicit. A national or homogeneous-region
   outlook cannot be promoted to a field, village, or district prediction.
4. Parsing must be evaluated against reviewed fixtures for at least the
   monsoon, heat, and winter product families; PDF layout changes must fail
   closed.
5. The crop-planning workflow must show the seasonal evidence as one
   uncertainty-labelled input alongside soil, water access, rotation, market,
   and farmer-provided cost/yield assumptions.

Until those conditions are met, the Codex prompt and skill require live
official-source research and a cautious scenario comparison. This preserves a
useful workflow without creating unsupported weather precision.
