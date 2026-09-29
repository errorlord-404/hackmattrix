# crop.health provider contract

This adapter is disabled unless `DIAGNOSIS_PROVIDER=kindwise_crop_health`,
`KINDWISE_CROP_HEALTH_API_KEY`, and `KINDWISE_CROP_HEALTH_BASE_URL` are set
server-side. The official API documentation is [crop.health docs](https://crop.kindwise.com/docs).

The configured endpoint and path are intentionally environment-owned because
the provider documentation is versioned separately from this repository. The
adapter uses the documented `Api-Key` header and JSON image payload shape.
Before a live release, record a redacted request/response fixture from the
account's enabled API version, confirm image-field and details names, and run
the provider contract tests against that fixture.

Only JPEG/PNG/WebP image bytes and an optional crop hint leave KisanSathi.
Farmer identity, field coordinates, sensor readings, and provider keys do not.
Provider candidates are screening evidence only; they cannot directly prescribe
chemical inputs or fertilizer doses.
