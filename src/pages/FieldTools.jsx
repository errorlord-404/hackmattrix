import { useEffect, useState } from "react";
import {
  Camera,
  CheckCircle2,
  ChevronRight,
  List,
  ScanSearch,
  Sprout,
  Upload,
  Wheat,
} from "lucide-react";
import { Link } from "react-router-dom";
import { farmStateApi } from "../api/farmStateApi.js";
import { useFarmData } from "../context/FarmDataContext.jsx";
import { useAIConversation } from "../context/AIConversationContext.jsx";
import FarmBoundaryMap from "../components/maps/FarmBoundaryMap.jsx";
import FieldBoundaryEditor from "../components/fields/FieldBoundaryEditor.jsx";
import { boundaryError, editableBoundaryPoints, farmerDrawnBoundary } from "../components/fields/fieldBoundary.js";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  SourceStamp,
} from "../components/feedback/ApiState.jsx";
import {
  cropOptions,
  cropRoutingState,
  UNKNOWN_CROP,
} from "../features/cropRouting.js";

const Card = ({ children, className = "" }) => (
  <section
    className={`rounded-card border border-border bg-white p-5 shadow-card ${className}`}
  >
    {children}
  </section>
);
const Page = ({ title, subtitle, children }) => (
  <div className="mx-auto max-w-[1440px] px-4 py-5 sm:px-6 lg:px-8 lg:py-7">
    <h1 className="text-2xl font-bold">{title}</h1>
    <p className="mt-1 text-sm text-text-secondary">{subtitle}</p>
    <div className="mt-6">{children}</div>
  </div>
);

export function FarmMap() {
  const { mapFields, fields, loading, error, refresh, updateField } = useFarmData();
  const [selected, setSelected] = useState(null);
  const [mode, setMode] = useState("map");
  const [editingBoundary, setEditingBoundary] = useState(false);
  const [boundaryPoints, setBoundaryPoints] = useState([]);
  const [boundarySaving, setBoundarySaving] = useState(false);
  const [boundaryErrorMessage, setBoundaryErrorMessage] = useState(null);
  const list = mapFields.length ? mapFields : fields;
  const activeSelected = selected || list[0];
  const beginBoundaryEdit = () => {
    setBoundaryPoints(editableBoundaryPoints(activeSelected?.boundary_geojson));
    setBoundaryErrorMessage(null);
    setEditingBoundary(true);
  };
  const saveBoundary = async () => {
    const validationError = boundaryError(boundaryPoints);
    if (validationError) { setBoundaryErrorMessage(validationError); return; }
    setBoundarySaving(true);
    setBoundaryErrorMessage(null);
    try {
      const updated = await updateField(activeSelected.id, { boundary_geojson: farmerDrawnBoundary(boundaryPoints) });
      setSelected(updated);
      setEditingBoundary(false);
    } catch (reason) {
      setBoundaryErrorMessage(reason.message || "The boundary could not be saved. Please try again.");
    } finally {
      setBoundarySaving(false);
    }
  };
  return (
    <Page
      title="My Farm Map"
      subtitle="View the status of every field from recorded boundaries and observations."
    >
      {loading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState error={error} onRetry={refresh} />
      ) : !list.length ? (
        <EmptyState
          title="No mapped fields"
          detail="Create a field with a location before opening the farm map."
        />
      ) : (
        <>
          <div className="mb-5 inline-flex rounded-lg bg-surface-muted p-1">
            <button
              onClick={() => setMode("map")}
              className={
                mode === "map"
                  ? "rounded-md bg-primary px-4 py-2 text-xs font-semibold text-white"
                  : "rounded-md px-4 py-2 text-xs font-semibold text-text-secondary"
              }
            >
              Map View
            </button>
            <button
              onClick={() => setMode("list")}
              className={
                mode === "list"
                  ? "rounded-md bg-primary px-4 py-2 text-xs font-semibold text-white"
                  : "rounded-md px-4 py-2 text-xs font-semibold text-text-secondary"
              }
            >
              <List size={13} className="mr-1 inline" />
              List View
            </button>
          </div>
          {mode === "map" ? (
            <>
            <div className="grid gap-5 lg:grid-cols-[1fr_300px]">
               <FarmBoundaryMap
                 fields={list}
                 selected={activeSelected}
                 onSelect={(field) => { setSelected(field); setEditingBoundary(false); setBoundaryErrorMessage(null); }}
               />
              <Card>
                <Wheat size={21} className="text-primary" />
                <h2 className="mt-4 text-lg font-bold">
                  {activeSelected?.name}
                </h2>
                <p className="mt-1 text-sm text-text-secondary">
                  {activeSelected?.current_crop || "Crop not recorded"} ·{" "}
                  {activeSelected?.area_acres} acres
                </p>
                <div className="mt-5 space-y-3 border-y border-border py-4 text-sm">
                  <p className="flex justify-between">
                    <span className="text-text-secondary">Growth stage</span>
                    <b>{activeSelected?.current_stage || "—"}</b>
                  </p>
                  <p className="flex justify-between">
                    <span className="text-text-secondary">Soil moisture</span>
                    <b>
                      {activeSelected?.latest_moisture_percent == null
                        ? "—"
                        : String(activeSelected.latest_moisture_percent) + "%"}
                    </b>
                  </p>
                  <p className="flex justify-between">
                    <span className="text-text-secondary">Open alerts</span>
                    <b>{activeSelected?.alert_count ?? 0}</b>
                  </p>
                </div>
                 <Link
                  to={"/fields/" + activeSelected?.id}
                  className="mt-5 flex items-center justify-between rounded-lg bg-primary px-4 py-2.5 text-xs font-semibold text-white"
                >
                   View field details <ChevronRight size={15} />
                 </Link>
                 <button type="button" onClick={beginBoundaryEdit} className="mt-3 flex w-full items-center justify-between rounded-lg border border-primary/25 bg-white px-4 py-2.5 text-xs font-semibold text-primary hover:bg-primary-50">
                   Adjust polygon <span aria-hidden="true">↗</span>
                 </button>
               </Card>
             </div>
             {editingBoundary && <section className="mt-5 rounded-card border border-primary/25 bg-white p-5 shadow-card" aria-label="Adjust selected field polygon">
               <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-[0.14em] text-primary">Farmer boundary editor</p><h2 className="mt-1 text-lg font-bold">Adjust {activeSelected?.name} polygon</h2><p className="mt-1 text-sm text-text-secondary">Drag a corner, tap the map to add one, then save the confirmed outline. This remains a farmer-drawn estimate, not a legal survey.</p></div><button type="button" onClick={() => { setEditingBoundary(false); setBoundaryErrorMessage(null); }} className="rounded-lg border border-border px-3 py-2 text-xs font-semibold text-text-secondary">Cancel</button></div>
               <FieldBoundaryEditor latitude={activeSelected?.centroid_lat} longitude={activeSelected?.centroid_lon} points={boundaryPoints} onChange={setBoundaryPoints} />
               {boundaryErrorMessage && <p role="alert" className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-800">{boundaryErrorMessage}</p>}
               <button type="button" disabled={boundarySaving || Boolean(boundaryError(boundaryPoints))} onClick={saveBoundary} className="mt-4 rounded-lg bg-primary px-4 py-2.5 text-sm font-bold text-white disabled:opacity-50">{boundarySaving ? "Saving polygon…" : "Save adjusted polygon"}</button>
              </section>}
            </>
          ) : (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {list.map((field) => (
                <button
                  className="rounded-card border border-border bg-white p-5 text-left shadow-card hover:border-primary"
                  onClick={() => {
                    setSelected(field);
                    setMode("map");
                  }}
                  key={field.id}
                >
                  <div className="flex justify-between">
                    <div>
                      <p className="font-bold">{field.name}</p>
                      <p className="mt-1 text-xs text-text-secondary">
                        {field.current_crop || "Crop not recorded"} ·{" "}
                        {field.area_acres} acres
                      </p>
                    </div>
                    <span className="rounded-full bg-primary-50 px-2 py-1 text-[10px] font-bold text-primary">
                      {field.alert_count || 0} alerts
                    </span>
                  </div>
                  <p className="mt-5 text-sm font-semibold text-primary-dark">
                    {field.current_stage || "No stage recorded"}
                  </p>
                  <p className="mt-1 text-xs text-text-secondary">
                    Moisture:{" "}
                    {field.latest_moisture_percent == null
                      ? "—"
                      : String(field.latest_moisture_percent) + "%"}
                  </p>
                </button>
              ))}
            </div>
          )}
        </>
      )}
    </Page>
  );
}

export function PestDisease() {
  const { fields } = useFarmData();
  const { sendText } = useAIConversation();
  const [fieldId, setFieldId] = useState(fields[0]?.id || "");
  const selectedFieldId = fieldId || fields[0]?.id || "";
  const selectedField = fields.find((field) => field.id === selectedFieldId);
  const defaultCrop =
    String(selectedField?.current_crop || UNKNOWN_CROP)
      .trim()
      .toLowerCase() || UNKNOWN_CROP;
  const [selectedCrop, setSelectedCrop] = useState(UNKNOWN_CROP);
  const [confirmedFieldId, setConfirmedFieldId] = useState(null);
  const cropConfirmed = confirmedFieldId === selectedFieldId;
  const crop = cropConfirmed ? selectedCrop : defaultCrop;
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [feedbackCorrectness, setFeedbackCorrectness] = useState("confirmed");
  const [feedbackLabel, setFeedbackLabel] = useState("");
  const [shareFeedback, setShareFeedback] = useState(false);
  const [feedbackSaving, setFeedbackSaving] = useState(false);
  const [feedbackMessage, setFeedbackMessage] = useState("");
  const [screeningApproved, setScreeningApproved] = useState(false);
  const [agentHandoff, setAgentHandoff] = useState("");
  const routing = cropRoutingState(crop, cropConfirmed);
  const upload = async () => {
    if (!file) {
      setError(new Error("Choose a JPG, PNG, or WebP image first."));
      return;
    }
    if (!cropConfirmed) {
      setError(
        new Error(
          "Please confirm the crop, or select “I do not know”, before uploading.",
        ),
      );
      return;
    }
    if (!screeningApproved) {
      setError(new Error("Approve crop-health screening before the photo can be assessed."));
      return;
    }
    setUploading(true);
    setError(null);
    setAgentHandoff("");
    try {
      // Keep the photograph private until the farmer explicitly authorises this
      // screening request. The returned diagnosis ID is the only image-related
      // value passed to the Codex agent.
      const staged = await farmStateApi.stageCropImage(file, selectedFieldId);
      const consent = await farmStateApi.createCropHealthConsent(
        staged.upload_id,
        "approved",
      );
      const outcome = await farmStateApi.createDiagnosisFromUpload(
        staged.upload_id,
        consent.consent_receipt_id,
        crop === UNKNOWN_CROP ? undefined : crop,
      );
      setResult(outcome);
      setFeedbackCorrectness("confirmed");
      setFeedbackLabel(outcome.label || "");
      setShareFeedback(false);
      setFeedbackMessage("");
      setAgentHandoff("Sending the saved result to KisanSathi for a sensor- and weather-aware review…");
      const delivered = await sendText(
        `The farmer approved a crop-health screening from the Pest & Disease screen. Review diagnosis evidence record ${outcome.id} for field ${selectedFieldId}. Call get_diagnosis for exactly that record, then use the field's current sensor, soil, irrigation, and weather evidence to provide safe triage. The confirmed crop is ${crop === UNKNOWN_CROP ? "unknown" : crop}. Treat visual candidates as screening only; do not prescribe chemicals or doses.`,
        { via: "crop-health-screen", fieldId: selectedFieldId },
      );
      setAgentHandoff(
        delivered
          ? "KisanSathi has the saved diagnosis record and is preparing its field-aware review."
          : "The photo result is saved. Open KisanSathi to request a field-aware review.",
      );
    } catch (err) {
      setError(err);
    } finally {
      setUploading(false);
    }
  };
  const saveFeedback = async () => {
    if (!result?.id) return;
    setFeedbackSaving(true);
    setFeedbackMessage("");
    try {
      const saved = await farmStateApi.createDiagnosisFeedback(result.id, {
        correctness: feedbackCorrectness,
        confirmed_crop: crop === UNKNOWN_CROP ? null : crop,
        label: feedbackCorrectness === "unknown" ? null : feedbackLabel,
        share_for_model_improvement: shareFeedback,
      });
      setFeedbackMessage(saved.share_for_model_improvement ? "Feedback saved. It still needs expert review before it can be used for model work." : "Feedback saved only in your local farm record.");
    } catch (feedbackError) {
      setFeedbackMessage(feedbackError.message || "Feedback could not be saved.");
    } finally {
      setFeedbackSaving(false);
    }
  };
  return (
    <Page
      title="Pest & Disease"
      subtitle="Confirm the crop first, then upload a real crop photo. Disease routing stays explicit when models are unavailable."
    >
      <div className="grid gap-5 lg:grid-cols-[1fr_360px]">
        <Card>
          <div className="min-h-72 rounded-xl border border-primary-light bg-[radial-gradient(circle_at_top_left,_#f1f8df,_#fff_58%)] p-6">
            <div className="flex flex-col items-center text-center">
              <span className="grid size-14 place-items-center rounded-full bg-white text-primary shadow-card">
                <Camera size={26} />
              </span>
              <h2 className="mt-4 font-bold">Confirm crop → inspect photo</h2>
              <p className="mt-2 max-w-sm text-sm leading-6 text-text-secondary">
                The router will ask instead of silently choosing the wrong
                disease specialist.
              </p>
            </div>
            {fields.length > 0 && (
              <label className="mt-5 block text-sm font-semibold">
                Field
                <select
                  value={fieldId}
                  onChange={(event) => {
                    setFieldId(event.target.value);
                    setConfirmedFieldId(null);
                    setResult(null);
                    setAgentHandoff("");
                  }}
                  className="mt-2 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm"
                >
                  <option value="">No field selected</option>
                  {fields.map((field) => (
                    <option value={field.id} key={field.id}>
                      {field.name}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <div className="mt-4 rounded-xl border border-primary-light bg-white/80 p-4">
              <label
                htmlFor="photo-crop"
                className="block text-sm font-semibold"
              >
                What crop is in this photo?
              </label>
              <select
                id="photo-crop"
                value={crop}
                onChange={(event) => {
                  setSelectedCrop(event.target.value);
                  setConfirmedFieldId(selectedFieldId);
                  setResult(null);
                }}
                className="mt-2 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm"
              >
                <option value={UNKNOWN_CROP}>I do not know</option>
                {cropOptions(selectedField?.current_crop).map((option) => (
                  <option key={option} value={option}>
                    {option[0].toUpperCase() + option.slice(1)}
                  </option>
                ))}
              </select>
              <p
                className={
                  routing.status === "ready"
                    ? "mt-2 text-xs text-primary-dark"
                    : "mt-2 text-xs text-amber-800"
                }
              >
                {routing.message}
              </p>
            </div>
            <input
              id="diagnosis-file"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={(event) => {
                setFile(event.target.files?.[0] || null);
                setResult(null);
              }}
              className="mt-4 block max-w-full text-xs"
            />
            {file && <p className="mt-2 text-xs text-primary-dark">Selected: {file.name} · {(file.size / 1024 / 1024).toFixed(1)} MB</p>}
            <label className="mt-4 flex items-start gap-2 rounded-lg border border-primary/20 bg-white/80 p-3 text-xs leading-5 text-text-secondary">
              <input
                aria-label="Approve crop-health screening"
                type="checkbox"
                checked={screeningApproved}
                onChange={(event) => setScreeningApproved(event.target.checked)}
                className="mt-0.5"
              />
              <span>I approve this private photo being assessed by the configured crop-health model. KisanSathi keeps the sensor and soil records in the farm database; the agent receives only the saved diagnosis record.</span>
            </label>
            <button
              onClick={upload}
              disabled={uploading || !file || !cropConfirmed || !screeningApproved}
              className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
            >
              <Upload size={16} />
              {uploading ? "Saving & screening…" : "Save photo & run crop-health check"}
            </button>
            {error && (
              <p className="mt-3 text-xs text-red-700">{error.message}</p>
            )}
          </div>
        </Card>
        <Card>
          <h2 className="font-bold">How the prototype decides</h2>
          <ol className="mt-4 space-y-4 text-sm text-text-secondary">
            <li className="flex gap-2">
              <b className="text-primary">1</b>
              <span>
                Farmer confirms the crop, or explicitly says it is unknown.
              </span>
            </li>
            <li className="flex gap-2">
              <b className="text-primary">2</b>
              <span>
                A local specialist runs only for a supported confirmed crop.
              </span>
            </li>
            <li className="flex gap-2">
              <b className="text-primary">3</b>
              <span>
                The AI explains uncertainty; it does not invent treatment.
              </span>
            </li>
          </ol>
          <h3 className="mt-6 font-semibold">Photo tips</h3>
          <ul className="mt-3 space-y-3 text-sm text-text-secondary">
            <li className="flex gap-2">
              <CheckCircle2 size={17} className="shrink-0 text-primary" />
              Use natural daylight.
            </li>
            <li className="flex gap-2">
              <CheckCircle2 size={17} className="shrink-0 text-primary" />
              Keep the affected area in focus.
            </li>
            <li className="flex gap-2">
              <CheckCircle2 size={17} className="shrink-0 text-primary" />
              Include leaf edges and both sides if possible.
            </li>
          </ul>
        </Card>
      </div>
      {result && (
        <Card className="mt-5 border-primary-light">
          <div className="flex items-start gap-3">
            <ScanSearch size={19} className="text-primary" />
            <div className="min-w-0 flex-1">
              <p className="font-bold">
                {result.status === "completed"
                  ? result.label?.replaceAll("_", " ") || "Crop-health result"
                  : "Photo needs review"}
              </p>
              {result.confidence != null && (
                <p className="mt-1 text-sm font-semibold text-primary-dark">
                  Model confidence: {Math.round(result.confidence * 100)}%
                </p>
              )}
              <p className="mt-2 text-sm leading-6 text-text-secondary">
                {result.error ||
                  (result.status === "completed"
                    ? "This is a screening result, not treatment advice."
                    : "The provider returned no additional explanation.")}
              </p>
              {result.crop_candidates?.length > 0 && (
                <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3">
                  <p className="text-xs font-bold uppercase tracking-wide text-amber-900">
                    Suggested crop — please confirm
                  </p>
                  <ul className="mt-2 space-y-1 text-sm">
                    {result.crop_candidates.map((candidate) => (
                      <li
                        className="flex justify-between"
                        key={candidate.label}
                      >
                        <span>{candidate.label.replaceAll("_", " ")}</span>
                        <span className="font-semibold">
                          {Math.round(candidate.score * 100)}%
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {result.candidates?.length > 0 && (
                <div className="mt-4 rounded-lg bg-surface-muted p-3">
                  <p className="text-xs font-bold uppercase tracking-wide text-text-secondary">
                    Model alternatives
                  </p>
                  <ul className="mt-2 space-y-1 text-sm">
                    {result.candidates.map((candidate) => (
                      <li
                        className="flex justify-between"
                        key={candidate.label}
                      >
                        <span>{candidate.label.replaceAll("_", " ")}</span>
                        <span className="font-semibold">
                          {Math.round(candidate.score * 100)}%
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {result.model_version && (
                <p className="mt-4 text-xs text-text-secondary">
                  {result.model_id} · {result.model_version} ·{" "}
                  {result.inference_location}
                </p>
              )}
              {result.limitations?.map((limitation) => (
                <p className="mt-2 text-xs text-amber-800" key={limitation}>
                  • {limitation}
                </p>
              ))}
              <div className="mt-5 rounded-xl border border-primary/20 bg-primary-50 p-4">
                <p className="font-semibold text-primary-dark">Was this result correct?</p>
                <p className="mt-1 text-xs leading-5 text-text-secondary">Your feedback can be kept as a local record. If you opt in, it is still only a review lead—not automatic model training or an image upload.</p>
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  <label className="text-xs font-semibold">Your assessment
                    <select aria-label="Diagnosis feedback assessment" value={feedbackCorrectness} onChange={(event) => setFeedbackCorrectness(event.target.value)} className="mt-1.5 block w-full rounded-lg border border-border bg-white px-3 py-2 text-sm font-normal">
                      <option value="confirmed">Result is correct</option><option value="corrected">I want to correct it</option><option value="unknown">I am not sure</option>
                    </select>
                  </label>
                  {feedbackCorrectness !== "unknown" && <label className="text-xs font-semibold">Observed condition
                    <input aria-label="Diagnosis feedback label" value={feedbackLabel} onChange={(event) => setFeedbackLabel(event.target.value)} placeholder="For example: late blight" className="mt-1.5 block w-full rounded-lg border border-border bg-white px-3 py-2 text-sm font-normal" />
                  </label>}
                </div>
                <label className="mt-3 flex items-start gap-2 text-xs text-text-secondary"><input aria-label="Share diagnosis feedback for model improvement" type="checkbox" checked={shareFeedback} onChange={(event) => setShareFeedback(event.target.checked)} className="mt-0.5" /><span>I consent to this feedback being considered later for expert-reviewed model improvement. It will not be exported or used for training automatically.</span></label>
                <button onClick={saveFeedback} disabled={feedbackSaving || (feedbackCorrectness !== "unknown" && !feedbackLabel.trim())} className="mt-3 rounded-lg border border-primary bg-white px-3 py-2 text-xs font-semibold text-primary disabled:opacity-50">{feedbackSaving ? "Saving feedback…" : "Save my feedback"}</button>
                {feedbackMessage && <p className="mt-2 text-xs text-primary-dark" role="status">{feedbackMessage}</p>}
              </div>
              <SourceStamp
                source={result.provider}
                fetchedAt={result.created_at}
              />
              {agentHandoff && <div className="mt-4 rounded-lg border border-primary/20 bg-primary-50 p-3 text-xs text-primary-dark" role="status">{agentHandoff} <Link to="/ai" className="ml-1 font-bold underline underline-offset-2">Open KisanSathi agent</Link></div>}
            </div>
          </div>
        </Card>
      )}
    </Page>
  );
}

export function CropGuide() {
  const { fields } = useFarmData();
  const { sendText, processing: agentProcessing } = useAIConversation();
  const [fieldId, setFieldId] = useState(fields[0]?.id || "");
  const selectedFieldId = fieldId || fields[0]?.id || "";
  const [cycles, setCycles] = useState([]);
  const [error, setError] = useState(null);
  const [season, setSeason] = useState("Kharif");
  const [previousCrop, setPreviousCrop] = useState(fields[0]?.current_crop || "");
  const [soilType, setSoilType] = useState("");
  const [options, setOptions] = useState([]);
  const [optionsError, setOptionsError] = useState(null);
  const [optionsLoading, setOptionsLoading] = useState(false);
  const [online, setOnline] = useState(() => typeof navigator === "undefined" || navigator.onLine);
  const [researchRequested, setResearchRequested] = useState(false);
  const [researchError, setResearchError] = useState(null);
  const selected = fields.find((field) => field.id === selectedFieldId);
  useEffect(() => {
    const syncNetwork = () => setOnline(navigator.onLine);
    window.addEventListener("online", syncNetwork);
    window.addEventListener("offline", syncNetwork);
    return () => { window.removeEventListener("online", syncNetwork); window.removeEventListener("offline", syncNetwork); };
  }, []);
  const selectField = (nextFieldId) => {
    const nextField = fields.find((field) => field.id === nextFieldId);
    setFieldId(nextFieldId);
    setError(null);
    setOptions([]);
    setOptionsError(null);
    setPreviousCrop(nextField?.current_crop || "");
  };
  useEffect(() => {
    if (!selectedFieldId) return;
    farmStateApi.getTimeline(selectedFieldId).then(setCycles).catch(setError);
  }, [selectedFieldId]);
  const loadOptions = async () => {
    if (!selectedFieldId) return;
    setOptionsLoading(true);
    setOptionsError(null);
    try {
      setOptions(await farmStateApi.getCropOptions(selectedFieldId, { season, previousCrop, soilType }));
    } catch (nextError) {
      setOptionsError(nextError);
    } finally {
      setOptionsLoading(false);
    }
  };
  const requestResearchPlan = async () => {
    if (!selectedFieldId || !online) return;
    setResearchError(null);
    const sent = await sendText(
      `Help me choose which crop to sow for my recorded field. First load the exact field, timeline, soil health and latest sensor observations, near-term field weather, and crop options for season ${season}, previous crop ${previousCrop || "not recorded"}, and soil type ${soilType || "not recorded"}. Then research current official Indian crop advisories and market/MSP evidence for the viable short-list. Do not invent "in demand" claims: use dated market evidence or say it is unavailable. After you have reviewed the evidence, ask me to choose exactly one planning priority: higher yield, export quality, or organic farming. Only after I answer, compare all supported options with sources, dates, risks, and missing evidence.`,
      { via: "crop-sowing-plan", fieldId: selectedFieldId },
    );
    if (sent) setResearchRequested(true);
    else setResearchError("KisanSathi AI is not available right now. You can still use the local rule-based shortlist below.");
  };
  const cycle = cycles[0];
  return (
    <Page
      title="Crop Guide"
      subtitle="Use a local, explainable crop shortlist offline, or ask KisanSathi to research a full sowing plan online."
    >
      {fields.length ? (
        <select
          value={fieldId}
          onChange={(event) => selectField(event.target.value)}
          className="mb-5 rounded-lg border border-border bg-white px-3 py-2 text-sm"
        >
          {fields.map((field) => (
            <option value={field.id} key={field.id}>
              {field.name}
            </option>
          ))}
        </select>
      ) : (
        <EmptyState title="No fields" detail="Create a field first." />
      )}
      {error && <ErrorState error={error} />}
      {fields.length > 0 && (
        <Card className="mb-5 border-primary/20 bg-[linear-gradient(135deg,#f2f7df,_#fff_56%,_#f7f0dd)]">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-primary">Crop-sowing planner</p>
              <h2 className="mt-1 text-lg font-bold text-primary-dark">Start with a local shortlist, then research when online</h2>
              <p className="mt-1 max-w-2xl text-sm leading-6 text-text-secondary">The local path checks recorded season, rotation and soil constraints without internet. The research path adds field soil/sensor context, near-term weather, current MSP and market evidence before asking whether your priority is higher yield, export quality or organic farming.</p>
            </div>
            <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${online ? "border-primary/20 bg-white text-primary" : "border-amber-200 bg-amber-50 text-amber-900"}`}>{online ? "Online research available" : "Offline · local rules only"}</span>
          </div>
          <div className="mt-5 grid gap-3 md:grid-cols-3">
            <label className="text-sm font-semibold">Season
              <select aria-label="Next crop season" value={season} onChange={(event) => setSeason(event.target.value)} className="mt-2 block w-full rounded-lg border border-border bg-white px-3 py-2 text-sm font-normal">
                <option value="Kharif">Kharif</option><option value="Rabi">Rabi</option><option value="Zaid">Zaid</option>
              </select>
            </label>
            <label className="text-sm font-semibold">Previous crop
              <input aria-label="Previous crop" value={previousCrop} onChange={(event) => setPreviousCrop(event.target.value)} placeholder="For example: Wheat" className="mt-2 block w-full rounded-lg border border-border bg-white px-3 py-2 text-sm font-normal" />
            </label>
            <label className="text-sm font-semibold">Soil type
              <input aria-label="Soil type" value={soilType} onChange={(event) => setSoilType(event.target.value)} placeholder="For example: Loamy" className="mt-2 block w-full rounded-lg border border-border bg-white px-3 py-2 text-sm font-normal" />
            </label>
          </div>
          <div className="mt-4 flex flex-wrap gap-3"><button onClick={loadOptions} disabled={optionsLoading} className="rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-primary-dark disabled:opacity-50">{optionsLoading ? "Checking local rules…" : "Run local crop rules"}</button>{online && <button type="button" onClick={requestResearchPlan} disabled={agentProcessing} className="rounded-lg border border-primary bg-white px-4 py-2.5 text-sm font-semibold text-primary transition hover:bg-primary-50 disabled:opacity-50">{agentProcessing ? "KisanSathi is researching…" : "Research full sowing plan"}</button>}</div>
          <p className="mt-3 text-xs leading-5 text-text-secondary">{online ? "Live research is source-checked and will ask you to choose one goal after reviewing the field: higher yield, export quality, or organic farming." : "No internet connection detected. Results below use only locally recorded/catalogue rules and will not claim current weather, MSP, demand or export suitability."}</p>
          {researchRequested && <p role="status" className="mt-3 rounded-lg border border-primary/20 bg-white px-3 py-2 text-sm text-primary-dark">KisanSathi has the field plan request. <Link to="/ai" className="font-bold underline underline-offset-2">Open AI Advisor</Link> to answer its priority question and see the sourced comparison.</p>}
          {researchError && <p role="alert" className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900">{researchError}</p>}
          {optionsError && <div className="mt-4"><ErrorState error={optionsError} onRetry={loadOptions} /></div>}
          {options.length > 0 && <div className="mt-5 grid gap-3 lg:grid-cols-2">{options.map((option) => <article className="rounded-xl border border-border bg-white p-4 shadow-sm" key={option.crop_name}>
            <div className="flex items-start justify-between gap-3"><div><h3 className="font-bold">{option.crop_name}</h3><p className="mt-1 text-xs text-text-secondary">Catalog season: {option.season || "not recorded"}</p></div><span className={`rounded-full px-2 py-1 text-[10px] font-bold ${option.status === "candidate_needs_review" ? "bg-amber-50 text-amber-800" : "bg-red-50 text-red-800"}`}>{option.status === "candidate_needs_review" ? "Review evidence" : "Conflict found"}</span></div>
            <dl className="mt-4 grid grid-cols-3 gap-2 text-xs"><div className="rounded-lg bg-surface-muted p-2"><dt className="text-text-secondary">Season</dt><dd className="mt-1 font-semibold">{option.checks.season === true ? "Matches" : option.checks.season === false ? "Conflict" : "Missing"}</dd></div><div className="rounded-lg bg-surface-muted p-2"><dt className="text-text-secondary">Rotation</dt><dd className="mt-1 font-semibold">{option.checks.previous_crop_rotation === true ? "Matches" : option.checks.previous_crop_rotation === false ? "Conflict" : "Missing"}</dd></div><div className="rounded-lg bg-surface-muted p-2"><dt className="text-text-secondary">Soil</dt><dd className="mt-1 font-semibold">{option.checks.soil_type === true ? "Matches" : option.checks.soil_type === false ? "Conflict" : "Missing"}</dd></div></dl>
            {option.reference_price_per_quintal != null && <p className="mt-3 text-sm text-text-secondary">Reference price: <b className="text-text-primary">₹{option.reference_price_per_quintal}/quintal</b></p>}
            {option.missing_evidence.length > 0 && <p className="mt-3 text-xs text-amber-800">Still needed: {option.missing_evidence.join(", ")}</p>}
            {option.conflicts.length > 0 && <p className="mt-3 text-xs text-red-800">Conflicts: {option.conflicts.join(", ")}</p>}
            <p className="mt-3 text-[11px] text-text-muted">Local rule source: {option.price_source || "crop catalogue"}</p>
            {option.source_url && <a href={option.source_url} target="_blank" rel="noreferrer" className="mt-2 inline-block text-xs font-semibold text-primary underline">View price source</a>}
          </article>)}</div>}
          {options.length === 0 && !optionsLoading && !optionsError && <p className="mt-4 text-sm text-text-secondary">No crop option has been checked yet. Run local crop rules to get an offline-safe shortlist.</p>}
        </Card>
      )}
      {cycle ? (
        <div className="grid gap-5 lg:grid-cols-[280px_1fr]">
          <Card>
            <Sprout size={23} className="text-primary" />
            <h2 className="mt-4 font-bold">{selected?.name}</h2>
            <p className="mt-1 text-sm text-text-secondary">
              {cycle.crop_name}
            </p>
            <p className="mt-5 text-sm">
              <span className="text-text-secondary">Current stage</span>
              <b className="ml-2 text-primary">{cycle.current_stage}</b>
            </p>
          </Card>
          <div className="space-y-3">
            {cycle.stage_events.map((event) => (
              <Card
                className={
                  event.stage === cycle.current_stage
                    ? "border-primary bg-primary-50"
                    : ""
                }
                key={event.id}
              >
                <div className="flex gap-4">
                  <span className="grid size-10 shrink-0 place-items-center rounded-full bg-primary text-sm font-bold text-white">
                    ✓
                  </span>
                  <div>
                    <h2 className="font-bold">{event.stage}</h2>
                    <p className="mt-1 text-sm text-text-secondary">
                      Recorded on{" "}
                      {new Date(event.occurred_at).toLocaleDateString()}
                    </p>
                    {event.note && (
                      <p className="mt-2 text-xs text-text-secondary">
                        {event.note}
                      </p>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      ) : (
        fields.length > 0 && (
          <EmptyState
            title="No crop cycle recorded"
            detail="Create a crop cycle through the Farm State API before using the live crop guide."
          />
        )
      )}
    </Page>
  );
}
