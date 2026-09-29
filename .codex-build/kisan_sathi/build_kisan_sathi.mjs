import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const workspaceDir = "C:/Users/prana/Desktop/sih mvp";
const SKILL_DIR = "C:/Users/prana/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations";
const RUNTIME_PYTHON = "C:/Users/prana/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe";
const TMP_DIR = path.join(workspaceDir, ".codex-build", "kisan_sathi");
const FINAL_PPTX = path.join(workspaceDir, "output", "KisanSathi_Beamer_Minimalist_Final.pptx");
const sourcePath = "C:/Users/prana/Downloads/SIH_Kisan_Sathi_PS-180.pptx";
const { resolvePresentationFont, finalizePresentation } = await import(pathToFileURL(path.join(SKILL_DIR, "container_tools", "artifact_tool_utils.mjs")).href);
await fs.mkdir(TMP_DIR, { recursive: true });
await fs.mkdir(path.dirname(FINAL_PPTX), { recursive: true });

const font = resolvePresentationFont({ fontFamily: "Aptos" });
const C = { ink: "#102A43", muted: "#50677C", pale: "#F5F8F5", line: "#D5E0DA", green: "#176B4D", lime: "#A7D948", teal: "#2A9D8F", sand: "#EAF1D3", white: "#FFFFFF", soft: "#EEF5F0", gold: "#E9B949", charcoal: "#173042" };
const W = 1280, H = 720;
const sourceNote = "Source: SIH_Kisan_Sathi_PS-180.pptx supplied by the user.";

function rect(slide, left, top, width, height, fill, line = "none", radius = 0) {
  return slide.shapes.add({ geometry: radius ? "roundRect" : "rect", position: { left, top, width, height }, fill, line: line === "none" ? { fill: "none", width: 0 } : { style: "solid", fill: line, width: 1 }, borderRadius: radius || undefined });
}
function text(slide, value, left, top, width, height, size = 20, color = C.ink, opts = {}) {
  const shape = slide.shapes.add({ geometry: "textbox", position: { left, top, width, height }, fill: "none", line: { fill: "none", width: 0 } });
  shape.text = value;
  shape.text.style = { typeface: font, fontSize: size, color, bold: opts.bold ?? false, italic: opts.italic ?? false, align: opts.align ?? "left", autoFit: "shrinkText" };
  return shape;
}
function frame(slide, title, num) {
  slide.background.fill = C.white;
  rect(slide, 0, 0, W, 12, C.green);
  text(slide, title, 80, 42, 900, 46, 30, C.ink, { bold: true });
  text(slide, `0${num}`, 1134, 44, 74, 36, 15, C.green, { bold: true, align: "right" });
  rect(slide, 70, 649, 1140, 1, C.line);
  text(slide, "KISAN SATHI", 70, 664, 180, 22, 11, C.green, { bold: true });
  text(slide, "SMART INDIA HACKATHON 2026", 940, 664, 270, 22, 11, C.muted, { align: "right" });
}
function tag(slide, value, left, top, width, fill = C.sand, color = C.green) {
  rect(slide, left, top, width, 28, fill, "none", 12);
  text(slide, value.toUpperCase(), left + 10, top + 5, width - 20, 18, 11, color, { bold: true, align: "center" });
}
function block(slide, {x, y, w, h, title, body, accent = C.green, fill = C.white, titleSize = 18, bodySize = 14}) {
  rect(slide, x, y, w, h, fill, C.line, 14);
  rect(slide, x, y, 7, h, accent, "none", 5);
  text(slide, title, x + 23, y + 20, w - 44, 27, titleSize, C.ink, { bold: true });
  text(slide, body, x + 23, y + 55, w - 44, h - 68, bodySize, C.muted);
}
function flowArrow(slide, from, to, direction = "right", color = C.green) {
  slide.shapes.connect(from, to, { kind: "straight", fromSide: direction === "right" ? "right" : "bottom", toSide: direction === "right" ? "left" : "top", line: { style: "solid", fill: color, width: 2 }, tail: { type: "triangle", width: "sm", length: "sm" } });
}

const p = Presentation.create({ slideSize: { width: W, height: H } });

// 1. Objective
{
  const s = p.slides.add(); frame(s, "Project objective", 1);
  tag(s, "Field-deployable farm copilot", 70, 108, 270);
  text(s, "Turn field evidence into\nclear, safe action", 70, 158, 540, 125, 38, C.ink, { bold: true });
  text(s, "KisanSathi helps farmers detect crop and soil stress early, understand irrigation needs and act despite weak connectivity.", 70, 306, 500, 80, 18, C.muted);
  rect(s, 70, 430, 510, 145, C.soft, "none", 16);
  text(s, "Design principle", 95, 456, 170, 24, 15, C.green, { bold: true });
  text(s, "AI recommends. The farmer confirms. The edge device enforces safety limits.", 95, 494, 435, 53, 18, C.ink, { bold: true });
  text(s, "FIELD EVIDENCE", 660, 120, 210, 20, 12, C.green, { bold: true });
  const a = rect(s, 660, 180, 220, 96, C.pale, C.line, 14); text(s, "Sense\nsoil, crop, weather", 680, 202, 180, 55, 19, C.ink, { bold: true, align: "center" });
  const b = rect(s, 920, 180, 220, 96, C.pale, C.line, 14); text(s, "Diagnose\nlocally", 940, 202, 180, 55, 19, C.ink, { bold: true, align: "center" });
  const c = rect(s, 660, 352, 220, 96, C.pale, C.line, 14); text(s, "Recommend\nwith context", 680, 374, 180, 55, 19, C.ink, { bold: true, align: "center" });
  const d = rect(s, 920, 352, 220, 96, C.green, C.green, 14); text(s, "Act safely\nand record", 940, 374, 180, 55, 19, C.white, { bold: true, align: "center" });
  flowArrow(s, a, b); flowArrow(s, b, d, "bottom"); flowArrow(s, c, d); flowArrow(s, a, c, "bottom");
  text(s, "A practical loop for disease, pests, nutrient stress and irrigation decisions", 660, 500, 480, 40, 16, C.muted, { italic: true, align: "center" });
  s.speakerNotes.textFrame.setText(sourceNote);
}

// 2. Problem and need
{
  const s = p.slides.add(); frame(s, "Problem statement and need", 2);
  tag(s, "The field reality", 70, 108, 170, C.sand);
  text(s, "Farmers make high-stakes decisions with fragmented, delayed evidence", 70, 158, 720, 55, 29, C.ink, { bold: true });
  block(s, { x: 70, y: 260, w: 325, h: 250, title: "Disconnected signals", body: "Images, soil readings, field notes and weather data sit in separate tools. The farmer must interpret them under time pressure.", accent: C.gold, fill: "#FFF9EC", bodySize: 16 });
  block(s, { x: 430, y: 260, w: 325, h: 250, title: "Connectivity gaps", body: "Cloud-only applications lose value when the network is unreliable, especially where timely advice matters most.", accent: C.teal, fill: "#F1FAF8", bodySize: 16 });
  block(s, { x: 790, y: 260, w: 350, h: 250, title: "Unsafe automation risk", body: "A generic AI response must not directly control pumps or turn uncertain sensor data into costly decisions.", accent: C.green, fill: C.soft, bodySize: 16 });
  text(s, "The solution needs local intelligence, understandable advice and a safety boundary around every action.", 70, 560, 1050, 31, 18, C.green, { bold: true });
  s.speakerNotes.textFrame.setText(sourceNote);
}

// 3. Key features
{
  const s = p.slides.add(); frame(s, "Key features", 3);
  text(s, "A field-first assistant built around the farmer’s decisions", 70, 108, 900, 34, 20, C.muted);
  const data = [
    ["Offline-first operation", "SQLite storage, local inference and queued sync keep core workflows available during outages.", C.green],
    ["Multilingual guidance", "Hindi and Marathi voice interactions make advice accessible without complex screens.", C.teal],
    ["Early stress detection", "On-device vision and sensor readings identify disease, pests, nutrient stress and irrigation needs.", C.gold],
    ["Explainable recommendations", "Advice includes priority, confidence, evidence and data freshness so farmers can judge it.", C.green],
    ["Farmer-scoped digital twin", "Observations, tasks and interventions remain traceable at the individual farm level.", C.teal],
    ["Safe escalation", "Low confidence or unsupported crops route evidence to KVKs and human experts.", C.gold],
  ];
  data.forEach(([title, body, accent], i) => { const col = i % 3; const row = Math.floor(i / 3); block(s, { x: 70 + col * 380, y: 190 + row * 190, w: 335, h: 145, title, body, accent, fill: i % 2 ? C.white : C.pale, titleSize: 18, bodySize: 14 }); });
  rect(s, 70, 575, 1070, 1, C.line);
  text(s, "The system combines fast local detection with accountable, tool-driven reasoning.", 70, 594, 860, 28, 17, C.ink, { bold: true });
  s.speakerNotes.textFrame.setText(sourceNote);
}

// 4. Technical approach
{
  const s = p.slides.add(); frame(s, "Technical approach", 4);
  tag(s, "Sense · diagnose · reason · deliver", 70, 108, 280, C.sand);
  text(s, "A local decision loop with connected support when available", 70, 156, 900, 42, 28, C.ink, { bold: true });
  const steps = [
    ["01", "Sense", "ESP32 probes, crop images, field records and weather capture relevant field evidence."],
    ["02", "Diagnose", "On-device vision and deterministic agronomy APIs identify stress and irrigation needs."],
    ["03", "Reason", "A Codex agent uses farmer-scoped MCP tools, local state and verified data services."],
    ["04", "Deliver & record", "Voice and simple screens return prioritized advice, create confirmed tasks and sync later."],
  ];
  const nodes = [];
  steps.forEach(([n, t, b], i) => {
    const x = 70 + i * 280;
    rect(s, x, 255, 230, 210, i === 3 ? C.green : C.white, i === 3 ? C.green : C.line, 14);
    text(s, n, x + 22, 276, 45, 22, 13, i === 3 ? C.lime : C.green, { bold: true });
    text(s, t, x + 22, 314, 180, 26, 21, i === 3 ? C.white : C.ink, { bold: true });
    text(s, b, x + 22, 359, 185, 76, 14, i === 3 ? "#E9F4E2" : C.muted);
    nodes.push(rect(s, x + 102, 500, 28, 28, i === 3 ? C.green : C.sand, "none", 14));
  });
  for (let i = 0; i < nodes.length - 1; i++) flowArrow(s, nodes[i], nodes[i + 1]);
  text(s, "Local runtime", 142, 536, 180, 22, 13, C.green, { bold: true, align: "center" });
  text(s, "Agent orchestration", 412, 536, 200, 22, 13, C.green, { bold: true, align: "center" });
  text(s, "Farmer confirmation", 690, 536, 220, 22, 13, C.green, { bold: true, align: "center" });
  text(s, "Record & sync", 960, 536, 165, 22, 13, C.green, { bold: true, align: "center" });
  text(s, "The edge device and human remain the final safety controls.", 70, 585, 860, 24, 17, C.muted, { italic: true });
  s.speakerNotes.textFrame.setText(sourceNote);
}

// 5. Architecture
{
  const s = p.slides.add(); frame(s, "System architecture", 5);
  text(s, "Architecture retained from the source design", 70, 108, 720, 28, 18, C.muted);
  // connectors first so they sit behind blocks
  const edge = rect(s, 70, 245, 230, 250, "#F1FAF8", C.line, 14);
  const data = rect(s, 365, 245, 215, 250, C.pale, C.line, 14);
  const agent = rect(s, 645, 215, 245, 310, "#F5F9EE", C.green, 14);
  const services = rect(s, 955, 245, 255, 250, "#FFF9EC", C.line, 14);
  flowArrow(s, edge, data); flowArrow(s, data, agent);
  s.shapes.connect(agent, services, { kind: "straight", fromSide: "right", toSide: "left", line: { style: "solid", fill: C.gold, width: 2 }, head: { type: "triangle", width: "sm", length: "sm" }, tail: { type: "triangle", width: "sm", length: "sm" } });
  text(s, "FIELD / EDGE", 92, 270, 184, 18, 12, C.green, { bold: true, align: "center" });
  text(s, "ESP32-S3", 92, 306, 184, 26, 21, C.ink, { bold: true, align: "center" });
  text(s, "WiFi / MQTT buffering\nSoil moisture, temperature, EC, pH and NPK probes\nOn-device TFLite / QNN vision", 92, 350, 184, 105, 14, C.muted, { align: "center" });
  text(s, "BACKEND & DATA", 385, 270, 175, 18, 12, C.green, { bold: true, align: "center" });
  text(s, "FastAPI", 385, 306, 175, 26, 21, C.ink, { bold: true, align: "center" });
  text(s, "Python 3.11+ with Pydantic\nSQLite for local state\nMongoDB catalogues via Beanie\nDeterministic agronomy endpoints", 385, 350, 175, 105, 14, C.muted, { align: "center" });
  text(s, "AI ORCHESTRATION", 667, 242, 200, 18, 12, C.green, { bold: true, align: "center" });
  text(s, "Codex App-Server", 667, 280, 200, 26, 21, C.ink, { bold: true, align: "center" });
  text(s, "Agent loop via MCP\n47 deterministic tools\nFarmer-scoped context\nNo direct hardware authority", 667, 328, 200, 105, 15, C.muted, { align: "center" });
  rect(s, 681, 454, 174, 38, C.green, "none", 12); text(s, "SAFETY GATE", 691, 466, 154, 15, 11, C.white, { bold: true, align: "center" });
  text(s, "EXTERNAL SERVICES", 976, 270, 212, 18, 12, "#956B12", { bold: true, align: "center" });
  text(s, "Farmer interface", 976, 306, 212, 26, 21, C.ink, { bold: true, align: "center" });
  text(s, "React 19 / Vite / Tailwind\nSarvam AI for speech and translation\nOpen-Meteo, data.gov.in, FARMS and MahaDBT", 976, 350, 212, 105, 14, C.muted, { align: "center" });
  text(s, "Cloud services enrich the decision. Core field functions remain available locally.", 70, 565, 1140, 28, 17, C.ink, { bold: true, align: "center" });
  s.speakerNotes.textFrame.setText(sourceNote);
}

const requirements = { explicitTotalSlideCount: 5, requiredNativeTableOwnerSlides: [], requiredNativeChartOwnerSlides: [] };
const candidatePath = path.join(TMP_DIR, "candidate.pptx");
await (await PresentationFile.exportPptx(p)).save(candidatePath);
const result = await finalizePresentation({
  ...requirements, workspaceDir, candidatePath, finalPath: FINAL_PPTX, pythonExecutable: RUNTIME_PYTHON,
  integrityValidatorPath: path.join(SKILL_DIR, "container_tools", "inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(SKILL_DIR, "container_tools", "inspect_presentation_layout_geometry.py"),
  layoutArgs: ["--expected-slide-size-emu", "12192000,6858000", "--validate-bullet-geometry", "--validate-heading-fit"],
  fontPolicy: { basis: "design", families: [font] }, verifyArtifactToolImport: true,
  receiptPath: path.join(TMP_DIR, "KisanSathi_Beamer_Minimalist_Final.validation.json"),
});
console.log(JSON.stringify({ finalPath: FINAL_PPTX, font, result }, null, 2));
