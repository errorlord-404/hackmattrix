# MVP baseline and release evidence — 9 September 2026

## Workspace protection

- Branch: `pranav`
- Planning commit: `a11d6fe`
- Map/Codex implementation commits: `16ebcfd`, `4512f52`, `c906ad7`
- Existing user-owned dirty and untracked changes were preserved; no reset,
  clean, checkout-overwrite, or broad deletion was used.
- Ports `8001` and `5173` were already occupied by user-owned processes during
  the audit. Isolated launcher ports were selected explicitly and cleaned on
  exit.

## Automated baseline

| Gate | Evidence |
|---|---|
| Backend | 51 pytest tests passed |
| Codex agent | 12 pytest tests passed |
| Frontend | 11 Vitest files / 18 tests passed |
| Desktop harness | 6 Node tests passed |
| Adapter contract | `npm run demo:contracts`: 53 frontend path shapes matched OpenAPI |
| Lint | ESLint passed |
| Build | Vite production build passed; existing >500 kB bundle warning remains |
| Launcher syntax | PowerShell AST parse passed |

## Runtime evidence

`-ResetDemo` on a custom backend port followed by `npm run demo:check` produced:

- two non-overlapping fields;
- three machinery records;
- twelve marketplace records (two for each demonstrated type);
- three government schemes;
- farmer-local soil/sensor/task/ledger fixture data;
- available FastAPI farm state and Mongo reference database.

The same run launched Electron and Vite, and Ctrl+C removed only the owned
backend/renderer/Electron process trees. The browser automation surface could
inspect the renderer and map/list workflows; native Electron screenshot capture
was not exposed by this desktop session.

## Contract inventory status

The frontend adapters in `src/api/client.js`, `src/api/farmStateApi.js`, and
`src/api/referenceApi.js` now target the FastAPI routes exercised by the UI and
Codex tests. Nearby endpoints, diagnostics, export, and audit routes have
contract tests. Any future adapter must add a route test before release.

## Known non-MVP claims

Physical pump actuation, production identity/authentication, live supplier
availability, guaranteed market/yield/profit predictions, official scheme
eligibility, and field-released crop-health inference are not claimed by this
demo. Hardware and ML evidence remain separate pilot gates.
