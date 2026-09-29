import { useEffect, useMemo, useState } from "react";
import {
  CheckCircle2,
  CircleAlert,
  Clock3,
  Cpu,
  ExternalLink,
  MapPin,
  Radio,
  RefreshCw,
  ShieldCheck,
  WifiOff,
} from "lucide-react";
import { Link } from "react-router-dom";
import { farmStateApi } from "../api/farmStateApi.js";
import { useFarmData } from "../context/FarmDataContext.jsx";
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "../components/feedback/ApiState.jsx";
import { freshnessFor } from "../components/features/sensors/sensorTelemetry.js";

const STORE_KEY = "kisansathi-device-onboarding-v1";
const steps = ["Assign field", "Record placement", "Verify first reading"];
const loadDraft = () => {
  try {
    return JSON.parse(localStorage.getItem(STORE_KEY) || "{}");
  } catch {
    return {};
  }
};

export default function DeviceOnboarding() {
  const { fields, loading: fieldsLoading } = useFarmData();
  const [draft, setDraft] = useState(loadDraft);
  const [selectedFieldId, setSelectedFieldId] = useState(draft.fieldId || "");
  const [placement, setPlacement] = useState(draft.placement || "");
  const [depth, setDepth] = useState(draft.depth || "");
  const [note, setNote] = useState(draft.note || "");
  const [observations, setObservations] = useState([]);
  const [history, setHistory] = useState([]);
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const selectedField = fields.find((field) => field.id === selectedFieldId);
  const latest = useMemo(
    () =>
      observations.reduce(
        (current, value) =>
          !current ||
          new Date(value.observed_at) > new Date(current.observed_at)
            ? value
            : current,
        null,
      ),
    [observations],
  );
  const freshness = freshnessFor(latest?.observed_at);
  const deviceHealth = devices[0] || null;
  const refresh = async () => {
    if (!selectedFieldId) return;
    setLoading(true);
    setError(null);
    try {
      const [nextObservations, nextHistory, nextDevices] = await Promise.all([
        farmStateApi.getLatestObservations(selectedFieldId),
        farmStateApi.getObservationHistory(selectedFieldId),
        farmStateApi.listDeviceHealth(selectedFieldId),
      ]);
      setObservations(nextObservations);
      setHistory(nextHistory);
      setDevices(nextDevices);
    } catch (reason) {
      setError(reason);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    const task = window.setTimeout(() => {
      if (selectedFieldId) void refresh();
    }, 0);
    return () => window.clearTimeout(task);
  }, [selectedFieldId]); // eslint-disable-line react-hooks/exhaustive-deps
  const saveDraft = () => {
    const next = {
      fieldId: selectedFieldId,
      placement,
      depth,
      note,
      savedAt: new Date().toISOString(),
    };
    localStorage.setItem(STORE_KEY, JSON.stringify(next));
    setDraft(next);
  };
  if (fieldsLoading)
    return (
      <main className="mx-auto max-w-5xl px-4 py-7">
        <LoadingState label="Loading fields…" />
      </main>
    );
  if (!fields.length)
    return (
      <main className="mx-auto max-w-5xl px-4 py-7">
        <EmptyState
          title="Create a field first"
          detail="A soil node must be assigned to a named field before its readings can be interpreted."
          action={
            <Link
              className="mt-4 inline-block rounded-lg bg-primary px-4 py-2 text-sm font-bold text-white"
              to="/fields"
            >
              Create field
            </Link>
          }
        />
      </main>
    );
  const completed = [
    Boolean(selectedFieldId),
    Boolean(placement && depth),
    Boolean(latest && freshness.key === "fresh" && (!deviceHealth || deviceHealth.status === "fresh")),
  ];
  const maxHistory = Math.max(...history.map((item) => Number(item.value)), 1);
  return (
    <main className="mx-auto max-w-5xl px-4 py-5 sm:px-6 lg:py-8">
      <header className="rounded-3xl border border-primary/20 bg-[radial-gradient(circle_at_top_right,_#dff5d8,_#f7faf6_55%)] p-6 shadow-card">
        <div className="flex items-start gap-4">
          <span className="grid size-12 place-items-center rounded-2xl bg-primary text-white shadow-lg">
            <Radio size={25} />
          </span>
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary">
              Field setup
            </p>
            <h1 className="mt-1 text-2xl font-bold">Connect a soil node</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-text-secondary">
              Capture where the probe is placed, then verify a real reading.
              Placement notes stay on this device. The gateway has a separate
              provisioned telemetry credential, which is never shown here;
              this screen cannot control a pump.
            </p>
          </div>
        </div>
      </header>
      <ol className="mt-6 grid gap-3 sm:grid-cols-3">
        {steps.map((step, index) => (
          <li
            key={step}
            className={`rounded-xl border p-4 ${completed[index] ? "border-primary/30 bg-primary-50" : "border-border bg-white"}`}
          >
            <div className="flex items-center gap-2">
              {completed[index] ? (
                <CheckCircle2 size={18} className="text-primary" />
              ) : (
                <span className="grid size-5 place-items-center rounded-full border text-[10px] font-bold">
                  {index + 1}
                </span>
              )}
              <b className="text-sm">{step}</b>
            </div>
            <p className="mt-2 text-xs text-text-secondary">
              {index === 0
                ? "Choose the field this node observes."
                : index === 1
                  ? "Record depth and a recognizable placement."
                  : "Fresh data is required; stale data remains unknown."}
            </p>
          </li>
        ))}
      </ol>
      <section className="mt-6 grid gap-5 lg:grid-cols-[1.1fr_.9fr]">
        <form
          onSubmit={(event) => {
            event.preventDefault();
            saveDraft();
          }}
          className="rounded-card border border-border bg-white p-5 shadow-card"
        >
          <h2 className="font-bold">Placement record</h2>
          <p className="mt-1 text-sm text-text-secondary">
            This is a local placement draft. The node is provisioned separately
            and its secret is never displayed in the farmer app.
          </p>
          <label className="mt-5 block text-sm font-semibold">
            Field
            <select
              required
              value={selectedFieldId}
              onChange={(event) => setSelectedFieldId(event.target.value)}
              className="mt-2 w-full rounded-lg border border-border bg-white px-3 py-2.5"
            >
              <option value="">Select field</option>
              {fields.map((field) => (
                <option key={field.id} value={field.id}>
                  {field.name} · {field.current_crop || "no crop recorded"}
                </option>
              ))}
            </select>
          </label>
          <label className="mt-4 block text-sm font-semibold">
            Probe placement
            <input
              required
              value={placement}
              onChange={(event) => setPlacement(event.target.value)}
              placeholder="e.g. North bed, between rows 3 and 4"
              className="mt-2 w-full rounded-lg border border-border px-3 py-2.5"
            />
          </label>
          <label className="mt-4 block text-sm font-semibold">
            Depth (cm)
            <input
              required
              min="1"
              type="number"
              value={depth}
              onChange={(event) => setDepth(event.target.value)}
              placeholder="e.g. 15"
              className="mt-2 w-full rounded-lg border border-border px-3 py-2.5"
            />
          </label>
          <label className="mt-4 block text-sm font-semibold">
            Calibration / placement note
            <textarea
              value={note}
              onChange={(event) => setNote(event.target.value)}
              placeholder="Soil condition, reference check, or date of installation"
              className="mt-2 min-h-24 w-full rounded-lg border border-border px-3 py-2.5"
            />
          </label>
          <button className="mt-5 inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-bold text-white">
            <ShieldCheck size={16} />
            Save local setup record
          </button>
          {draft.savedAt && (
            <p className="mt-3 text-xs text-text-muted">
              Last saved locally: {new Date(draft.savedAt).toLocaleString()}
            </p>
          )}
        </form>
        <aside className="rounded-card border border-border bg-white p-5 shadow-card">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="font-bold">Reading check</h2>
              <p className="mt-1 text-sm text-text-secondary">
                {selectedField ? selectedField.name : "Choose a field first"}
              </p>
            </div>
            <button
              type="button"
              onClick={refresh}
              disabled={!selectedFieldId || loading}
              className="rounded-lg border border-border p-2 text-primary disabled:opacity-50"
              aria-label="Refresh readings"
            >
              <RefreshCw size={17} className={loading ? "animate-spin" : ""} />
            </button>
          </div>
          {selectedFieldId && deviceHealth && (
            <div
              className={`mt-4 rounded-xl border p-3 text-xs ${deviceHealth.status === "fresh" ? "border-primary/20 bg-primary-50 text-primary-dark" : deviceHealth.status === "rejected" ? "border-rose-200 bg-rose-50 text-rose-900" : "border-amber-200 bg-amber-50 text-amber-900"}`}
            >
              <p className="font-bold">
                Gateway {deviceHealth.status}: {deviceHealth.device_id}
              </p>
              <p className="mt-1">
                Last packet {new Date(deviceHealth.last_received_at).toLocaleString()} · firmware {deviceHealth.firmware_version}
                {deviceHealth.rejection_reason ? ` · ${deviceHealth.rejection_reason}` : ""}
              </p>
            </div>
          )}
          {error ? (
            <div className="mt-5">
              <ErrorState error={error} onRetry={refresh} />
            </div>
          ) : !selectedFieldId ? (
            <div className="mt-6 rounded-xl bg-surface-muted p-4 text-sm text-text-secondary">
              <MapPin size={20} className="text-primary" />
              <p className="mt-3">
                Assign a field to check its latest reading.
              </p>
            </div>
          ) : !latest ? (
            <div className="mt-6 rounded-xl border border-dashed border-border bg-surface-muted p-4">
              <WifiOff size={21} className="text-text-muted" />
              <p className="mt-3 font-bold">No reading yet</p>
              <p className="mt-1 text-sm text-text-secondary">
                Keep this status as unknown until the node posts a verified
                observation.
              </p>
            </div>
          ) : (
            <div
              className={`mt-5 rounded-xl p-4 ${freshness.key === "fresh" ? "bg-primary-50" : "bg-amber-50"}`}
            >
              <div className="flex items-center gap-2">
                <Clock3 size={18} />
                <b>{freshness.label}</b>
              </div>
              <p className="mt-3 text-2xl font-bold">
                {latest.measurement}: {latest.value} {latest.unit}
              </p>
              <p className="mt-2 text-sm text-text-secondary">
                Observed {new Date(latest.observed_at).toLocaleString()}
              </p>
              <p className="mt-3 text-xs">
                {freshness.detail}. Source: {latest.source || "not recorded"}.
              </p>
            </div>
          )}
          <Link
            to={selectedFieldId ? `/fields/${selectedFieldId}` : "/soil"}
            className="mt-5 inline-flex items-center gap-1 text-sm font-bold text-primary"
          >
            Open field history <ExternalLink size={15} />
          </Link>
          <p className="mt-5 flex gap-2 rounded-lg bg-amber-50 p-3 text-xs leading-5 text-amber-900">
            <CircleAlert size={16} className="shrink-0" />
            Sensor values are screening observations. Verify unusual N/P/K
            readings with a laboratory test or Soil Health Card.
          </p>
        </aside>
      </section>
      <section className="mt-6 rounded-card border border-border bg-white p-5 shadow-card">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-bold">Moisture history</h2>
            <p className="mt-1 text-sm text-text-secondary">
              Last {history.length} sourced observations. A missing series is
              unknown, not a flat trend.
            </p>
          </div>
          <span className="text-xs text-text-muted">
            {history.at(-1)?.unit || "%"}
          </span>
        </div>
        {history.length ? (
          <div
            className="mt-5 flex h-32 items-end gap-1"
            aria-label="Moisture history chart"
          >
            {history.map((item) => (
              <div
                className="group relative min-w-0 flex-1 rounded-t bg-primary/70"
                key={item.id}
                style={{
                  height: `${Math.max(6, (Number(item.value) / maxHistory) * 100)}%`,
                }}
                title={`${item.value} ${item.unit} · ${new Date(item.observed_at).toLocaleString()}`}
              >
                <span className="sr-only">
                  {item.value} {item.unit} at{" "}
                  {new Date(item.observed_at).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="mt-5 rounded-lg bg-surface-muted p-4 text-sm text-text-secondary">
            No moisture history has been recorded for this field yet.
          </p>
        )}
      </section>
      <section className="mt-6 rounded-card border border-border bg-white p-5 shadow-card">
        <div className="flex gap-3">
          <Cpu className="text-primary" />
          <div>
            <h2 className="font-bold">SIH demo handoff</h2>
            <p className="mt-1 text-sm text-text-secondary">
              Show field assignment → placement record → fresh reading → Soil
              Health advisory. If offline or stale, say “unknown”; do not infer
              healthy soil or activate irrigation.
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}
