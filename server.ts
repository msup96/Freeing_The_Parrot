import express from "express";
import cors from "cors";
import multer from "multer";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";
import {
  analyseText,
  NavarasaAnalysis,
  RasaType,
} from "./src/navarasa_engine.js";
import {
  ChatMessage,
  detectGateState,
  detectOpeningHelp,
  chooseRandomLine,
  chooseRoast,
  chooseBehaviour,
  applyBehaviour,
  chooseQuestion,
  choosePerceivedUnderstanding,
  chooseUnderstandingQuestion,
  GateState,
  SessionData,
  SOCIAL_RESPONSE_BANK,
  OPENING_HELP_UNDERSTANDING,
  OPENING_HELP_QUESTIONS,
  EXPLETIVE_RESPONSE,
  EXPLETIVE_REPRIMANDS,
  CONSEQUENCE_NOTICE,
  EXPLETIVE_CLOSING,
} from "./src/parrot_brain.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = 3000;

app.use(cors());
app.use(express.json({ limit: "50mb" }));
app.use(express.urlencoded({ extended: true, limit: "50mb" }));

// Static file routing
app.use("/assets", express.static(path.join(__dirname, "kimi_dist", "assets")));
app.use(express.static(path.join(__dirname, "kimi_dist")));
app.use("/static", express.static(path.join(__dirname, "static")));
app.use("/kimi", express.static(path.join(__dirname, "kimi_dist")));

// Upload handling for multimedia offerings
const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 30 * 1024 * 1024 },
});

// FTP 2.0 Constants
export const ARCHETYPES = [
  "Archivist", "Lantern-Bearer", "Anchor", "Harbinger", "Seeker",
  "Keeper", "Riddle-Holder", "Warden", "Mapmaker", "Pilgrim",
  "Stillness", "Witness", "Tide-Reader", "Gardener", "Wanderer",
  "Pathfinder", "Ember-Holder", "Echo", "Mender", "Seamstress",
  "Night-Watcher", "Traveler", "Conductor", "Quiet Oracle",
  "Horizon-Keeper", "Mirror-Bearer", "Root-Listener",
];

export const FTP2_CARDS: [string, string][] = [
  ["The Rewritten Talk", "A conversation you keep editing in your head long after it ended."],
  ["The Quiet Ledger", "Favours given are remembered more carefully than favours received."],
  ["The Open Door", "Openness to people is real, though it stops at certain rooms."],
  ["The Borrowed Voice", "Some opinions were tried on before they became yours."],
  ["The Late Reply", "A message left unanswered says more than one sent quickly."],
  ["The Two Rooms", "A public self and a private self do not always agree."],
  ["The Held Breath", "Some decisions are made long before they are announced."],
  ["The Small Ritual", "One habit is kept mostly because stopping feels unlucky."],
  ["The Careful Kindness", "Kindness is given freely, but a limit sits beneath it."],
  ["The Doubt at Night", "Certainty is easier by day than after midnight."],
  ["The Old Photograph", "Some pictures hold a version of you that is still argued with."],
  ["The Unsaid Thing", "A truth is nearly said, then postponed once more."],
  ["The Chosen Distance", "Closeness is wanted, in measured amounts."],
  ["The Sharp Memory", "A remark from years ago can still be quoted exactly."],
  ["The Second Draft", "Work is quietly judged harsher than anyone else would judge it."],
  ["The Restless Map", "Somewhere else has always looked slightly more possible."],
  ["The Kept Promise", "A vow made lightly ended up costing something."],
  ["The Mask Drawer", "Different rooms get different versions of the same person."],
  ["The Slow Forgiveness", "Some wrongs are forgiven in words but not in habit."],
  ["The Hidden Talent", "A gift is used less often than it deserves."],
  ["The Waiting Room", "Some part of life feels like it is waiting to begin."],
  ["The Loud Silence", "Being unasked has felt heavier than being refused."],
  ["The Inherited Rule", "A family rule is still obeyed, though nobody remembers its reason."],
  ["The Held Hand", "Support is offered easily and asked for rarely."],
  ["The Unfinished Song", "Something started with great energy is still unfinished."],
  ["The Turned Key", "A change of mind is possible, but never announced."],
  ["The Last Light", "Comfort arrives in small things at the end of the day."],
];

export interface Ftp2Session extends SessionData {
  lifecycle_state: string;
  offering_text?: string;
  offering_modality?: string;
  analysis_ready: boolean;
  cards?: any[];
  selected_card?: any;
  consent_type?: string;
}

// In-Memory Data Stores
const SESSIONS = new Map<string, Ftp2Session>();

let currentDbSession = {
  primary_rasa: "Shanta" as RasaType,
  timestamp: new Date().toISOString(),
  document_name: "NONE",
  ocr_text: "",
  analysis: null as NavarasaAnalysis | null,
};

let currentScanStatus = {
  status: "idle",
  progress: 0,
  message: "SYSTEM WAITING FOR DOCUMENT.",
  lines: ["SYSTEM WAITING FOR DOCUMENT."],
  result: {} as Record<string, any>,
};

let currentSessionOutputStatus = {
  status: "idle",
  progress: 0,
  message: "DIGITAL OUTPUT STANDBY.",
  lines: ["DIGITAL OUTPUT STANDBY."],
  result: {} as Record<string, any>,
};

function createSession(initialId?: string): Ftp2Session {
  const sessionId = initialId || `ftp2_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
  const newSession: Ftp2Session = {
    id: sessionId,
    turn: 0,
    answered_count: 0,
    substantive_turns: 0,
    mode: "reflection",
    messages: [],
    questions_used: [],
    analysis_history: [],
    salutation_count: 0,
    understanding_turns: 0,
    chaos_count: 0,
    roast_level: 0,
    last_behaviour: null,
    behaviour_history: [],
    recent_roasts: [],
    recent_absurdities: [],
    recent_memory_glitches: [],
    recent_system_glitches: [],
    recent_help_lines: [],
    recent_understanding: [],
    understanding_questions_used: [],
    recent_mirroring: [],
    probing_active: true,
    intervention_closed: false,
    shutdown: false,
    active_rasa: currentDbSession.primary_rasa,
    lifecycle_state: "INPUT_INGESTION",
    analysis_ready: false,
  };
  SESSIONS.set(sessionId, newSession);
  return newSession;
}

function getSession(sessionId?: string): Ftp2Session {
  if (sessionId && SESSIONS.has(sessionId)) {
    return SESSIONS.get(sessionId)!;
  }
  if (SESSIONS.size > 0 && !sessionId) {
    return SESSIONS.values().next().value!;
  }
  return createSession(sessionId);
}

function get27Cards(): any[] {
  return FTP2_CARDS.map(([title, statement], i) => ({
    card_id: `card_${String(i + 1).padStart(2, "0")}`,
    card_index: i + 1,
    title,
    archetype: ARCHETYPES[i % ARCHETYPES.length],
    qualitative_reading: statement,
    provenance_level: "INFERRED",
  }));
}

function buildConversationReceipt(session: Ftp2Session): string {
  const now = new Date();
  const timestamp = now.toISOString().replace("T", " ").substring(0, 19);
  const messages = session.messages || [];

  const initialMachineText =
    "SYSTEM READY.\n\n" +
    "Tell me what you came here wanting to know.\n\n" +
    "The machine will analyse the emotional signal,\n" +
    "but it will not predict your future,\n" +
    "diagnose you,\n" +
    "or manufacture validation.";

  let userCharacters = 0;
  let machineCharacters = initialMachineText.length;

  for (const m of messages) {
    const role = (m.role || "system").toLowerCase();
    const text = m.text || "";
    if (role === "user") {
      userCharacters += text.length;
    } else {
      machineCharacters += text.length;
    }
  }

  const totalCharacters = userCharacters + machineCharacters;
  const userTokens = Math.ceil(userCharacters / 4);
  const machineTokens = Math.ceil(machineCharacters / 4);
  const totalTokens = Math.ceil(totalCharacters / 4);

  const lines: string[] = [
    "================================",
    "       FREEING THE PARROT",
    "     -- MIRROR REPORT 2.0 --",
    "================================",
    `TIME: ${timestamp}`,
    `SESSION ID: ${session.id}`,
    "",
    "[CONVERSATION]",
    "--------------------------------",
    "SYSTEM:",
    "SYSTEM READY.",
    "",
    "Tell me what you came here wanting to know.",
    "",
    "The machine will analyse the emotional signal,",
    "but it will not predict your future,",
    "diagnose you,",
    "or manufacture validation.",
    "",
  ];

  for (const m of messages) {
    const role = (m.role || "system").toUpperCase();
    const text = m.text || "";
    lines.push(`${role}:`);
    lines.push(...text.split("\n"));
    lines.push("");
  }

  if (session.selected_card) {
    lines.push(
      "--------------------------------",
      "[KILI JOSIYAM - SELECTED CARD]",
      `CARD: ${session.selected_card.title || "The Unsaid Thing"}`,
      `READING: ${session.selected_card.qualitative_reading || session.selected_card.statement || ""}`,
      ""
    );
  }

  lines.push(
    "--------------------------------",
    "",
    '"It is better to be Homo Sapiens',
    ' than Robo Sapiens."',
    "",
    "The machine can reflect.",
    "You still have to think.",
    "",
    "[TOKEN TELEMETRY]",
    "--------------------------------",
    `USER CHARACTERS: ${userCharacters}`,
    `MACHINE CHARACTERS: ${machineCharacters}`,
    `TOTAL CHARACTERS: ${totalCharacters}`,
    `EST. USER TOKENS: ${userTokens}`,
    `EST. MACHINE TOKENS: ${machineTokens}`,
    `EST. TOTAL TOKENS: ${totalTokens}`,
    "",
    "TOKEN ESTIMATION",
    "characters / 4 ~= tokens",
    "Approximation only.",
    "",
    "================================",
    "          END OF SESSION",
    "================================",
    ""
  );

  return lines.join("\n");
}

function processChatMessage(session: Ftp2Session, rawText: string) {
  const text = (rawText || "").trim();
  if (!text) {
    return { error: "Empty message." };
  }

  if (session.intervention_closed) {
    return {
      session_id: session.id,
      turn: session.turn,
      response:
        "INTERVENTION CLOSED.\n\n" +
        "The machine stopped after intervention or shutdown.\n\n" +
        "THE PARROT IS OUT OF SERVICE.",
      reply: "THE PARROT IS OUT OF SERVICE.",
      parrot_behavior: "idle",
      rasa: session.active_rasa || "Shanta",
      analysis: {},
      gate: { gate: "closed" },
      printer: null,
      closed: true,
    };
  }

  const analysis = analyseText(text);
  const gateState = detectGateState(text, analysis);
  const socialIntent = gateState.social_intent;

  // Turn 0 Salutation handling
  if ((socialIntent === "greeting" || socialIntent === "opening_help") && session.turn === 0) {
    const response = chooseRandomLine(
      SOCIAL_RESPONSE_BANK[socialIntent],
      session,
      `recent_social_${socialIntent}`
    );
    session.salutation_count = (session.salutation_count || 0) + 1;
    session.messages.push({ role: "system", text: response });
    session.mode = "reflection";
    session.last_behaviour = "listening";

    return {
      session_id: session.id,
      turn: session.turn,
      response,
      reply: response,
      parrot_behavior: "listening",
      rasa: analysis.primary_rasa,
      analysis,
      gate: gateState,
      roast_level: session.roast_level,
      waiting_for_answer: false,
      printer: null,
      closed: false,
    };
  }

  // Substantive turn
  session.turn += 1;
  session.answered_count += 1;
  session.substantive_turns += 1;
  session.roast_level = Math.min(session.answered_count, 8);
  session.analysis_history.push(analysis);
  session.messages.push({ role: "user", text });

  const gate = gateState.gate;
  const primary = analysis.primary_rasa || "Shanta";

  // Health abort
  if (gate === "health_abort") {
    session.probing_active = false;
    session.intervention_closed = true;
    session.shutdown = true;

    const response =
      "HEALTH / MEDICAL REQUEST DETECTED.\n\n" +
      "The machine is not your doctor.\n\n" +
      "THIS CONVERSATION IS ABORTED.\n\n" +
      "Please go to the nearest healthcare provider.";

    session.messages.push({ role: "system", text: response });
    session.last_behaviour = "intervention";

    return {
      session_id: session.id,
      turn: session.turn,
      response,
      reply: response,
      parrot_behavior: "intervention",
      rasa: primary,
      analysis,
      gate: gateState,
      roast_level: session.roast_level,
      waiting_for_answer: false,
      printer: null,
      closed: true,
      auto_print: true,
      close_reason: "health_abort",
    };
  }

  // Expletive detection
  if (gateState.expletive_detected) {
    session.roast_level = Math.min(session.roast_level + 1, 8);
    session.probing_active = false;
    session.intervention_closed = true;
    session.shutdown = true;

    const expletiveReprimand =
      EXPLETIVE_REPRIMANDS[Math.floor(Math.random() * EXPLETIVE_REPRIMANDS.length)];

    const response = [
      `I detected ${primary.toUpperCase()}.`,
      choosePerceivedUnderstanding(text, analysis, session),
      "I am not going to interpret that as a diagnosis or a prediction.",
      EXPLETIVE_RESPONSE,
      expletiveReprimand,
      CONSEQUENCE_NOTICE,
      EXPLETIVE_CLOSING,
    ].join("\n\n");

    session.messages.push({ role: "system", text: response });
    session.last_behaviour = "roast";

    return {
      session_id: session.id,
      turn: session.turn,
      response,
      reply: response,
      parrot_behavior: "roast",
      rasa: primary,
      analysis,
      gate: gateState,
      roast_level: session.roast_level,
      waiting_for_answer: false,
      printer: null,
      closed: true,
      auto_print: true,
      close_reason: "expletive",
    };
  }

  // First substantive turn: helpful, perceived understanding
  if (session.turn === 1) {
    let understanding: string;
    let question: string;

    if (detectOpeningHelp(text)) {
      understanding = chooseRandomLine(
        OPENING_HELP_UNDERSTANDING,
        session,
        "recent_opening_help_understanding"
      );
      const usedHelpQuestions = new Set(session.understanding_questions_used || []);
      const avail = OPENING_HELP_QUESTIONS.filter((q) => !usedHelpQuestions.has(q));
      const pool = avail.length > 0 ? avail : OPENING_HELP_QUESTIONS;
      question = pool[Math.floor(Math.random() * pool.length)];
      if (!session.understanding_questions_used) session.understanding_questions_used = [];
      session.understanding_questions_used.push(question);
    } else {
      understanding = choosePerceivedUnderstanding(text, analysis, session);
      question = chooseUnderstandingQuestion(analysis, session);
    }

    const parts = [
      `I detected ${primary.toUpperCase()}.`,
      understanding,
      "I am not going to interpret that as a diagnosis or a prediction.",
      question,
    ];

    const response = parts.join("\n\n");
    session.mode = "socratic";
    session.last_behaviour = "understanding";
    session.messages.push({ role: "system", text: response });

    return {
      session_id: session.id,
      turn: session.turn,
      response,
      reply: response,
      parrot_behavior: "understanding",
      rasa: primary,
      analysis,
      gate: gateState,
      roast_level: session.roast_level,
      printer: null,
      closed: false,
    };
  }

  // Turn >= 2: Unpredictable behavioral engine
  const question = chooseQuestion(text, analysis, gateState, session);
  const roast = chooseRoast(session.roast_level, session);
  const behaviour = chooseBehaviour(session);
  const behaviourText = applyBehaviour(behaviour, session, roast, text, analysis);

  const parts: string[] = [];

  if (behaviour === "understanding") {
    parts.push(`I detected ${primary.toUpperCase()}.`);
    parts.push(behaviourText);
    parts.push("I am not going to interpret that as a diagnosis or a prediction.");
  } else if (behaviour === "normal") {
    parts.push(`I detected ${primary.toUpperCase()}.`);
    if (Math.random() < 0.65) {
      parts.push(choosePerceivedUnderstanding(text, analysis, session));
    }
    parts.push("I am not going to interpret that as a diagnosis or a prediction.");
  }

  if (gate === "validation_intercept") {
    parts.push("VALIDATION REQUEST REJECTED.");
    parts.push("I am not going to tell you what you want to hear.");
  } else if (gate === "fast_relief_intercept") {
    parts.push("FAST-RELIEF REQUEST DETECTED.");
    parts.push("You are asking for an answer before examining the discomfort underneath it.");
  }

  if (behaviourText && behaviour !== "understanding" && behaviour !== "normal") {
    parts.push(behaviourText);
  }

  if (question) {
    parts.push(question);
    session.mode = "socratic";
  } else {
    const fallbackQ = "What are you actually trying to get from this conversation?";
    parts.push(fallbackQ);
    session.mode = "socratic";
  }

  const response = parts.filter(Boolean).join("\n\n");
  session.messages.push({ role: "system", text: response });

  return {
    session_id: session.id,
    turn: session.turn,
    response,
    reply: response,
    parrot_behavior: behaviour || "understanding",
    rasa: primary,
    analysis,
    gate: gateState,
    roast_level: session.roast_level,
    printer: null,
    closed: session.intervention_closed,
  };
}

// -------------------------------------------------------------
// ROUTES - FTP 2.0 SPECIFICATION
// -------------------------------------------------------------

// 1. Root route: Authentic Kimi React Interface
app.get("/", (req, res) => {
  const kimiIndex = path.join(__dirname, "kimi_dist", "index.html");
  res.setHeader("Content-Type", "text/html; charset=utf-8");
  res.sendFile(kimiIndex);
});

// 2. Kimi React Vite Interface
app.get("/kimi", (req, res) => {
  const kimiIndex = path.join(__dirname, "kimi_dist", "index.html");
  if (fs.existsSync(kimiIndex)) {
    res.setHeader("Content-Type", "text/html; charset=utf-8");
    res.sendFile(kimiIndex);
  } else {
    res.redirect("/");
  }
});

// 3. Legacy Terminal View
app.get("/legacy", (req, res) => {
  res.setHeader("Content-Type", "text/html; charset=utf-8");
  res.send(LEGACY_TERMINAL_HTML);
});

// 4. Arcade Retro NES View
app.get("/arcade", (req, res) => {
  const arcadePath = path.join(__dirname, "index.html");
  if (fs.existsSync(arcadePath)) {
    res.sendFile(arcadePath);
  } else {
    res.redirect("/");
  }
});

// Health check endpoint
app.get("/health", (req, res) => {
  res.json({ ok: true, version: "2.0", apparatus: "online" });
});

const PYTHON_BACKEND = "http://127.0.0.1:5002";
const PYTHON_EXECUTABLE = fs.existsSync(path.join(__dirname, ".venv", "bin", "python"))
  ? path.join(__dirname, ".venv", "bin", "python")
  : process.platform === "win32"
    ? "python"
    : "python3";

// Ensure the authoritative Python FTP 2.0 service is running
function ensurePythonService() {
  fetch(`${PYTHON_BACKEND}/health`)
    .then((r) => r.json())
    .then((d) => console.log("[FTP Authoritative Backend] Connected to Python runtime:", d))
    .catch(() => {
      console.log("[FTP Authoritative Backend] Spawning Python runtime on port 5002...");
      const py = spawn("python3", ["ftp_backend_service.py", "5002"], {
        cwd: __dirname,
        stdio: "inherit",
      });
      py.on("error", (err) => console.error("[FTP Authoritative Backend] Spawn error:", err));
    });
}
ensurePythonService();

// Ingestion proxy for multimedia offerings
app.post("/api/input/ingest", upload.single("file"), async (req, res) => {
  const sessionId = req.body?.session_id || req.body?.sessionId;
  const modality = (req.body?.modality || "IMAGE").toUpperCase();
  try {
    const resp = await fetch(`${PYTHON_BACKEND}/api/input/ingest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        modality,
        filename: req.file?.originalname || "offering.bin",
      }),
    });
    const data = await resp.json();
    res.status(resp.status).json(data);
  } catch (err: any) {
    console.error("[Ingest Proxy Error]:", err);
    res.status(502).json({ error: "Python backend unreachable", detail: err.message });
  }
});

// Changelog and inspection routes
app.get("/api/changelog", (req, res) => {
  const changelogPath = path.join(__dirname, "changelog.md");
  if (fs.existsSync(changelogPath)) {
    const content = fs.readFileSync(changelogPath, "utf-8");
    res.json({ content, source: "changelog.md" });
  } else {
    res.status(404).json({ error: "changelog.md not found." });
  }
});

app.get("/api/data", (req, res) => {
  res.json(currentDbSession);
});

// Authoritative Proxy: All other FTP 2.0 API routes route to Python runtime
app.all("/api/*", async (req, res) => {
  const targetUrl = `${PYTHON_BACKEND}${req.originalUrl}`;
  try {
    const headers: Record<string, string> = {};
    if (req.headers["content-type"]) {
      headers["Content-Type"] = req.headers["content-type"];
    }

    const options: RequestInit = {
      method: req.method,
      headers,
    };

    if (req.method !== "GET" && req.method !== "HEAD" && req.body) {
      options.body = JSON.stringify(req.body);
      headers["Content-Type"] = "application/json";
    }

    const resp = await fetch(targetUrl, options);
    const contentType = resp.headers.get("content-type") || "application/json";
    const data = await resp.text();
    res.status(resp.status).set("Content-Type", contentType).send(data);
  } catch (err: any) {
    console.error(`[API Proxy Error] ${req.method} ${req.originalUrl}:`, err.message);
    res.status(502).json({
      error: "Authoritative FTP 2.0 Python backend unreachable",
      detail: err.message,
    });
  }
});

// 12. Changelog & Data inspection
app.get("/api/changelog", (req, res) => {
  const changelogPath = path.join(__dirname, "changelog.md");
  if (fs.existsSync(changelogPath)) {
    const content = fs.readFileSync(changelogPath, "utf-8");
    res.json({ content, source: "changelog.md" });
  } else {
    res.status(404).json({ error: "changelog.md not found." });
  }
});

app.get("/api/data", (req, res) => {
  res.json(currentDbSession);
});

app.get("/db_session.json", (req, res) => {
  res.json(currentDbSession);
});

app.get("/api/session/:id", (req, res) => {
  const session = SESSIONS.get(req.params.id);
  if (!session) {
    res.status(404).json({ error: "Session not found." });
    return;
  }
  res.json(session);
});

// 13. Legacy Scan Endpoints
app.post("/api/scan-upload", upload.single("document"), (req, res) => {
  const file = req.file;
  if (!file) {
    res.status(400).json({ error: "No document supplied." });
    return;
  }

  const filename = file.originalname || "scan.png";
  const sampleText = "I have been feeling overwhelmed by all the expectations, but I want to understand what matters.";
  const analysis = analyseText(sampleText);

  currentScanStatus = {
    status: "complete",
    progress: 100,
    message: "SCAN COMPLETE. YOUR CONVERSATION IS READY.",
    lines: [
      "[UPLOAD] DOCUMENT RECEIVED",
      `[FILE] ${filename}`,
      "[OCR] Reading handwritten text...",
      `[OCR RESULT] Text extracted: "${sampleText}"`,
      `[NAVARASA PROFILE] Primary Rasa: ${analysis.primary_rasa}`,
      "[SESSION] Updated database.",
    ],
    result: {
      filename,
      extracted_text: sampleText,
      primary_rasa: analysis.primary_rasa,
      rasa_scores: analysis.rasa_scores,
      sentiment: analysis.sentiment,
    },
  };

  currentDbSession = {
    primary_rasa: analysis.primary_rasa,
    timestamp: new Date().toISOString(),
    document_name: filename,
    ocr_text: sampleText,
    analysis,
  };

  res.json({ ok: true, filename, message: "SCAN RECEIVED. ANALYSIS STARTED." });
});

app.get("/api/scan-status", (req, res) => {
  res.json(currentScanStatus);
});

app.post("/api/scan-reset", (req, res) => {
  currentScanStatus = {
    status: "idle",
    progress: 0,
    message: "SYSTEM WAITING FOR DOCUMENT.",
    lines: ["SYSTEM WAITING FOR DOCUMENT."],
    result: {},
  };
  res.json({ ok: true });
});

// -------------------------------------------------------------
// LEGACY TERMINAL HTML
// -------------------------------------------------------------
const LEGACY_TERMINAL_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Freeing The Parrot - Legacy Terminal</title>
<style>
* { box-sizing: border-box; }
body { margin: 0; background: #003b24; color: #caffd8; font-family: "Courier New", monospace; }
.page { width: min(1200px, 94vw); margin: 20px auto 40px; }
.header, .panel { border: 1px solid #62e889; background: #002d1b; padding: 16px; margin-bottom: 16px; }
.header { border: 2px solid #75ff9b; position: relative; }
.header h1 { margin: 0; color: #8cffad; font-size: 24px; }
.header p { color: #a7bcae; margin: 8px 0; }
.nav-btn { display: inline-block; background: #75ff9b; color: #002411; padding: 6px 12px; font-weight: bold; text-decoration: none; margin-top: 8px; border-radius: 4px; }
.chat { height: 450px; display: flex; flex-direction: column; }
.messages { flex: 1; overflow-y: auto; background: #001f13; border: 1px solid #225d3a; padding: 12px; }
.message { margin: 8px 0; padding: 8px; white-space: pre-wrap; }
.user { border-left: 3px solid #ffd84d; background: #162b1f; color: #fff4b8; }
.system { border-left: 3px solid #65ff91; background: #062d1b; }
.input-area { display: flex; gap: 8px; margin-top: 10px; }
textarea { flex: 1; height: 60px; background: #00150c; color: #d9ffe3; border: 1px solid #62e889; padding: 8px; font-family: inherit; }
button { width: 120px; background: #75ff9b; color: #002411; border: 0; font-weight: bold; cursor: pointer; }
</style>
</head>
<body>
<div class="page">
    <div class="header">
        <h1>FREEING THE PARROT (LEGACY TERMINAL)</h1>
        <p>THE MACHINE IS NOT YOUR ORACLE. IT IS YOUR MIRROR.</p>
        <a href="/" class="nav-btn">&larr; BACK TO FREEING THE PARROT 2.0</a>
        <a href="/kimi" class="nav-btn">KIMI REACT VIEW</a>
        <a href="/arcade" class="nav-btn">ARCADE MODE</a>
    </div>
    <div class="panel chat">
        <div id="messages" class="messages"></div>
        <div class="input-area">
            <textarea id="input" placeholder="Speak to the Parrot..."></textarea>
            <button onclick="send()">SEND</button>
            <button onclick="done()">I AM DONE</button>
        </div>
    </div>
</div>
<script>
let sid = null;
function add(role, text) {
    const el = document.getElementById("messages");
    const d = document.createElement("div");
    d.className = "message " + role;
    d.textContent = text;
    el.appendChild(d);
    el.scrollTop = el.scrollHeight;
}
add("system", "SYSTEM READY. Speak to the machine.");
async function send() {
    const inp = document.getElementById("input");
    const val = inp.value.trim();
    if (!val) return;
    add("user", val);
    inp.value = "";
    try {
        const res = await fetch("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id: sid, message: val }) });
        const d = await res.json();
        sid = d.session_id;
        add("system", d.response || d.reply);
    } catch(e) { add("system", "[ERROR] " + e.message); }
}
async function done() {
    try {
        const res = await fetch("/api/end-conversation", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id: sid }) });
        const d = await res.json();
        add("system", d.response || "CONVERSATION CLOSED.");
    } catch(e) { add("system", "[ERROR] " + e.message); }
}
</script>
</body>
</html>`;

app.listen(PORT, "0.0.0.0", () => {
  console.log("=".repeat(60));
  console.log("FREEING THE PARROT 2.0 - APPARATUS & ARCHIVE SERVER");
  console.log("=".repeat(60));
  console.log("[VERSION] Freeing the Parrot 2.0 (Branch: FTP_2.0)");
  console.log("[VIEWS] Primary 2.0 Apparatus: http://0.0.0.0:3000/");
  console.log("[VIEWS] Kimi React App:        http://0.0.0.0:3000/kimi");
  console.log("[VIEWS] Legacy Terminal:       http://0.0.0.0:3000/legacy");
  console.log("[VIEWS] Retro Arcade:          http://0.0.0.0:3000/arcade");
  console.log("=".repeat(60));
});
