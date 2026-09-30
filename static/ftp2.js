/**
 * FTP 2.0 participant shell — apparatus visual + existing API wiring.
 */

(function () {
    "use strict";

    const DECK_STATEMENTS = [
        "You speak as if someone is always listening.",
        "Certainty arrives late, if at all.",
        "You rehearse answers before the question lands.",
        "Silence is not empty for you.",
        "You measure yourself against invisible standards.",
        "The day leaves a residue you cannot name.",
        "You perform ease more often than you feel it.",
        "What you withhold is as telling as what you share.",
        "You return to the same worry in different clothes.",
        "You ask permission without using the word.",
        "Your humour arrives before your honesty.",
        "You notice small slights and large absences.",
        "You are tired of being legible.",
        "You want to be understood without explaining.",
        "You test the room before you test yourself.",
        "You speak in lists when feelings overflow.",
        "You mistrust praise that arrives too quickly.",
        "You keep one door open, always.",
        "You translate pain into practicality.",
        "You are more observant than you admit.",
        "You fear being ordinary and being singular.",
        "You collect evidence against your own hope.",
        "You speak to the machine as if it could absolve.",
        "You arrive with a story and leave with a question.",
        "You repeat yourself when no one contradicts you.",
        "You are building a case for who you are.",
        "You already know what the Parrot will say.",
    ];

    const SCREEN_IDS = {
        entry: "screen-entry",
        conversation: "screen-conversation",
        deck: "screen-deck",
        reveal: "screen-reveal",
    };

    let sessionId = null;
    let conversationClosed = false;
    let mediaRecorder = null;
    let audioChunks = [];
    let cameraStream = null;
    let composerFocusedAt = null;
    let firstInputAt = null;
    let lastUserTexts = [];
    let chosenCardIndex = null;
    let chosenCardText = "";

    const trace = {
        text: 0,
        voice: 0,
        image: 0,
        camera: 0,
        questions: 0,
        pauses: 0,
        repeats: 0,
        reflections: 0,
    };

    const screenEntry = document.getElementById(SCREEN_IDS.entry);
    const screenConversation = document.getElementById(SCREEN_IDS.conversation);
    const screenDeck = document.getElementById(SCREEN_IDS.deck);
    const screenReveal = document.getElementById(SCREEN_IDS.reveal);
    const btnEnter = document.getElementById("btn-enter");
    const btnSend = document.getElementById("btn-send");
    const btnVoice = document.getElementById("btn-voice");
    const btnImage = document.getElementById("btn-image");
    const btnCamera = document.getElementById("btn-camera");
    const btnToDeck = document.getElementById("btn-to-deck");
    const btnDeckContinue = document.getElementById("btn-deck-continue");
    const conversationContinue = document.getElementById("conversation-continue");
    const imageFileInput = document.getElementById("image-file-input");
    const messageInput = document.getElementById("message-input");
    const conversationEl = document.getElementById("conversation");
    const modalityStatus = document.getElementById("modality-status");
    const cameraOverlay = document.getElementById("camera-overlay");
    const cameraPreview = document.getElementById("camera-preview");
    const btnCameraCapture = document.getElementById("btn-camera-capture");
    const btnCameraCancel = document.getElementById("btn-camera-cancel");
    const modalityButtons = document.querySelectorAll(".ftp2-modality__btn");
    const entryError = document.getElementById("entry-error");
    const sessionLabel = document.getElementById("session-label");
    const deckGrid = document.getElementById("deck-grid");
    const blackout = document.getElementById("blackout");
    const revealStatement = document.getElementById("reveal-statement");
    const revealCardNum = document.getElementById("reveal-card-num");
    const revealEvidenceList = document.getElementById("reveal-evidence-list");

    function showScreen(name) {
        const targets = {
            entry: screenEntry,
            conversation: screenConversation,
            deck: screenDeck,
            reveal: screenReveal,
        };
        Object.keys(targets).forEach(function (key) {
            const el = targets[key];
            if (!el) {
                return;
            }
            const active = key === name;
            el.hidden = !active;
            el.classList.toggle("ftp2-screen--active", active);
        });
    }

    function formatTime(date) {
        const h = String(date.getHours()).padStart(2, "0");
        const m = String(date.getMinutes()).padStart(2, "0");
        const s = String(date.getSeconds()).padStart(2, "0");
        return h + ":" + m + ":" + s;
    }

    function formatDuration(ms) {
        const totalSec = Math.max(0, Math.floor(ms / 1000));
        const min = Math.floor(totalSec / 60);
        const sec = totalSec % 60;
        const cs = Math.floor((ms % 1000) / 10);
        return String(min).padStart(2, "0") + ":" + String(sec).padStart(2, "0") + "." + String(cs).padStart(2, "0");
    }

    function updateTraceUI() {
        const map = {
            "trace-text": trace.text,
            "trace-voice": trace.voice,
            "trace-image": trace.image,
            "trace-camera": trace.camera,
            "trace-questions": trace.questions,
            "trace-pauses": trace.pauses,
            "trace-repeats": trace.repeats,
            "trace-reflections": trace.reflections,
        };
        Object.keys(map).forEach(function (id) {
            const el = document.getElementById(id);
            if (el) {
                el.textContent = String(map[id]);
            }
        });
    }

    function notePauseBeforeSend() {
        const pauseMs = composerFocusedAt ? Date.now() - composerFocusedAt : 0;
        if (pauseMs > 4000) {
            trace.pauses += 1;
            updateTraceUI();
        }
    }

    function noteUserText(text) {
        const trimmed = text.trim();
        if (trimmed.endsWith("?")) {
            trace.questions += 1;
        }
        if (lastUserTexts.indexOf(trimmed) !== -1 && trimmed.length > 0) {
            trace.repeats += 1;
        }
        lastUserTexts.push(trimmed);
        if (/\b(i feel|i think|i wonder|i'm not sure|i am not sure)\b/i.test(trimmed)) {
            trace.reflections += 1;
        }
        trace.text += 1;
        updateTraceUI();
    }

    function setEntryError(message) {
        if (!entryError) {
            return;
        }
        if (message) {
            entryError.textContent = message;
            entryError.hidden = false;
        } else {
            entryError.textContent = "";
            entryError.hidden = true;
        }
    }

    function setStatus(text, recording) {
        modalityStatus.textContent = text || "";
        modalityStatus.classList.toggle("ftp2-status--recording", Boolean(recording));
    }

    function setModalityActive(modality) {
        modalityButtons.forEach(function (btn) {
            const active = btn.getAttribute("data-modality") === modality;
            btn.classList.toggle("ftp2-modality__btn--active", active);
            if (btn.id === "btn-voice") {
                btn.setAttribute(
                    "aria-pressed",
                    active && btn.classList.contains("ftp2-modality__btn--recording") ? "true" : "false"
                );
            }
        });
    }

    function resetComposerTiming() {
        composerFocusedAt = Date.now();
        firstInputAt = null;
    }

    function composerTelemetryFor(text) {
        const now = Date.now();
        const typingStart = firstInputAt || composerFocusedAt || now;
        const focusStart = composerFocusedAt || typingStart;
        return {
            typing_duration_ms: Math.max(0, now - typingStart),
            pause_before_submit_ms: Math.max(0, now - focusStart),
            message_length: text.length,
        };
    }

    function scrollConversationToEnd() {
        conversationEl.scrollTop = conversationEl.scrollHeight;
    }

    function appendMessage(role, text, extra) {
        const block = document.createElement("article");
        let modClass = "parrot";
        let who = "PARROT";
        if (role === "user") {
            modClass = "user";
            who = "YOU";
        } else if (role === "error") {
            modClass = "error";
            who = "NOTICE";
        } else if (role === "ack") {
            modClass = "ack";
            who = "";
        }
        block.className = "ftp2-record-entry ftp2-record-entry--" + modClass;

        const head = document.createElement("div");
        head.className = "ftp2-record-entry__head";

        if (who) {
            const whoEl = document.createElement("span");
            whoEl.className = "ftp2-record-entry__who";
            whoEl.textContent = who;
            head.appendChild(whoEl);
        }

        const timeEl = document.createElement("span");
        timeEl.className = "ftp2-record-entry__time";
        timeEl.textContent = formatTime(new Date());
        head.appendChild(timeEl);

        const body = document.createElement("p");
        body.className = "ftp2-record-entry__body";
        if (role === "user" || role === "parrot") {
            body.textContent = "\"" + text + "\"";
        } else {
            body.textContent = text;
        }

        if (role !== "ack" || who) {
            block.appendChild(head);
        } else {
            block.appendChild(head);
        }
        block.appendChild(body);
        conversationEl.appendChild(block);
        scrollConversationToEnd();

        if (extra && role === "ack") {
            body.textContent = extra;
        }
    }

    function showReceived(kind, detail) {
        let line = "THE PARROT HAS RECEIVED THIS.";
        if (kind === "voice" && detail) {
            line = "RECEIVED — VOICE " + detail;
        } else if (kind === "image") {
            line = "RECEIVED — IMAGE";
        } else if (kind === "camera") {
            line = "RECEIVED — LOOK";
        }
        appendMessage("ack", line);
        setStatus("");
    }

    function setComposerEnabled(enabled) {
        messageInput.disabled = !enabled;
        btnSend.disabled = !enabled;
        btnVoice.disabled = !enabled;
        btnImage.disabled = !enabled;
        btnCamera.disabled = !enabled;
    }

    function sessionDisplayId(id) {
        if (!id) {
            return "SESSION — —";
        }
        return "SESSION " + id.slice(0, 8).toUpperCase();
    }

    function buildDeck() {
        if (!deckGrid || deckGrid.childElementCount > 0) {
            return;
        }
        DECK_STATEMENTS.forEach(function (statement, index) {
            const num = index + 1;
            const card = document.createElement("div");
            card.className = "ftp2-deck-card";
            card.setAttribute("role", "listitem");
            card.dataset.cardIndex = String(num);

            const numEl = document.createElement("span");
            numEl.className = "ftp2-deck-card__num";
            numEl.textContent = "NO. " + String(num).padStart(2, "0");

            const textEl = document.createElement("p");
            textEl.className = "ftp2-deck-card__text";
            textEl.textContent = statement;

            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "ftp2-deck-card__resonate";
            btn.textContent = "RESONATES";
            btn.addEventListener("click", function () {
                deckGrid.querySelectorAll(".ftp2-deck-card").forEach(function (c) {
                    c.classList.remove("ftp2-deck-card--chosen");
                });
                card.classList.add("ftp2-deck-card--chosen");
                chosenCardIndex = num;
                chosenCardText = statement;
                btnDeckContinue.disabled = false;
            });

            card.appendChild(numEl);
            card.appendChild(textEl);
            card.appendChild(btn);
            deckGrid.appendChild(card);
        });
    }

    function runBlackoutThenReveal() {
        if (!blackout) {
            showScreen("reveal");
            populateReveal();
            return;
        }
        blackout.hidden = false;
        requestAnimationFrame(function () {
            blackout.classList.add("ftp2-blackout--visible");
        });
        const duration = window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 200 : 1400;
        setTimeout(function () {
            showScreen("reveal");
            populateReveal();
            blackout.classList.remove("ftp2-blackout--visible");
            setTimeout(function () {
                blackout.hidden = true;
            }, duration);
        }, duration);
    }

    function populateReveal() {
        const num = chosenCardIndex || 7;
        const statement = chosenCardText || DECK_STATEMENTS[num - 1];
        if (revealCardNum) {
            revealCardNum.textContent = "CARD " + String(num).padStart(2, "0");
        }
        if (revealStatement) {
            revealStatement.textContent = statement.toUpperCase();
        }
        if (revealEvidenceList) {
            revealEvidenceList.innerHTML = "";
            const items = [
                String(trace.text) + " conversational turns",
                String(trace.pauses) + " hesitation events",
                String(trace.reflections) + " uncertainty markers",
                String(Math.min(trace.repeats, 9)) + " contradictions",
                String(trace.questions + trace.pauses) + " delayed responses",
            ];
            items.forEach(function (line) {
                const li = document.createElement("li");
                li.textContent = line;
                revealEvidenceList.appendChild(li);
            });
        }
    }

    async function beginSession() {
        setEntryError("");
        btnEnter.disabled = true;
        btnEnter.textContent = "…";
        try {
            const response = await fetch("/api/session/start", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
            });
            let data = {};
            try {
                data = await response.json();
            } catch (parseErr) {
                if (!response.ok) {
                    throw new Error("Could not start session.");
                }
            }
            if (!response.ok || !data.session_id) {
                throw new Error(data.error || "Could not start session.");
            }
            sessionId = data.session_id;
            setEntryError("");
            if (sessionLabel) {
                sessionLabel.textContent = sessionDisplayId(sessionId);
            }
            showScreen("conversation");
            resetComposerTiming();
            messageInput.focus();
        } catch (err) {
            btnEnter.disabled = false;
            btnEnter.textContent = "ENTER";
            setEntryError(err.message || "Connection failed.");
        }
    }

    async function ingestBlob(modality, blob, filename, metadata) {
        if (!sessionId || conversationClosed) {
            return;
        }
        const form = new FormData();
        form.append("session_id", sessionId);
        form.append("modality", modality);
        form.append("file", blob, filename);
        if (metadata) {
            form.append("metadata", JSON.stringify(metadata));
        }
        const response = await fetch("/api/input/ingest", {
            method: "POST",
            body: form,
        });
        const data = await response.json();
        if (!response.ok || !data.ok) {
            throw new Error(data.error || "Upload failed.");
        }
        return data;
    }

    async function sendMessage() {
        if (conversationClosed) {
            return;
        }

        const text = messageInput.value.trim();
        if (!text) {
            return;
        }

        notePauseBeforeSend();
        noteUserText(text);
        appendMessage("user", text);
        const telemetry = composerTelemetryFor(text);
        messageInput.value = "";
        setComposerEnabled(false);
        btnSend.textContent = "…";
        setStatus("");

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    session_id: sessionId,
                    message: text,
                    composer_telemetry: telemetry,
                }),
            });

            const data = await response.json();

            if (!response.ok || data.error) {
                appendMessage("error", data.error || "The request could not be completed.");
                return;
            }

            if (data.session_id) {
                sessionId = data.session_id;
                if (sessionLabel) {
                    sessionLabel.textContent = sessionDisplayId(sessionId);
                }
            }

            if (data.response) {
                appendMessage("parrot", data.response);
            }

            if (data.closed) {
                conversationClosed = true;
                setComposerEnabled(false);
                messageInput.placeholder = "This record is closed.";
                const listening = document.getElementById("listening-status");
                if (listening) {
                    listening.textContent = "THE RECORD IS CLOSED";
                }
                if (conversationContinue) {
                    conversationContinue.hidden = false;
                }
            }
        } catch (err) {
            appendMessage("error", err.message || "Connection failed.");
        } finally {
            resetComposerTiming();
            if (!conversationClosed) {
                setComposerEnabled(true);
                btnSend.textContent = "RECORD";
                messageInput.focus();
            } else {
                btnSend.textContent = "RECORD";
            }
        }
    }

    async function toggleVoiceRecording() {
        if (conversationClosed || !sessionId) {
            return;
        }
        if (mediaRecorder && mediaRecorder.state === "recording") {
            mediaRecorder.stop();
            return;
        }
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            audioChunks = [];
            const startedAt = Date.now();
            mediaRecorder = new MediaRecorder(stream);
            mediaRecorder.ondataavailable = function (event) {
                if (event.data.size > 0) {
                    audioChunks.push(event.data);
                }
            };
            mediaRecorder.onstop = async function () {
                stream.getTracks().forEach(function (t) { t.stop(); });
                btnVoice.classList.remove("ftp2-modality__btn--recording");
                const verb = btnVoice.querySelector(".ftp2-modality__verb");
                if (verb) {
                    verb.textContent = "SPEAK";
                }
                btnVoice.setAttribute("aria-pressed", "false");
                setStatus("");
                const blob = new Blob(audioChunks, { type: "audio/webm" });
                const durationMs = Date.now() - startedAt;
                try {
                    setStatus("Receiving…");
                    await ingestBlob("AUDIO", blob, "voice.webm", { duration_ms: durationMs });
                    trace.voice += 1;
                    updateTraceUI();
                    showReceived("voice", formatDuration(durationMs));
                } catch (err) {
                    appendMessage("error", err.message);
                }
            };
            mediaRecorder.start();
            const verb = btnVoice.querySelector(".ftp2-modality__verb");
            if (verb) {
                verb.textContent = "STOP";
            }
            btnVoice.classList.add("ftp2-modality__btn--recording");
            btnVoice.setAttribute("aria-pressed", "true");
            setModalityActive("voice");
            setStatus("Recording", true);
        } catch (err) {
            setStatus("Microphone unavailable");
            appendMessage("error", err.message || "Microphone unavailable.");
        }
    }

    async function handleImageFile(file) {
        if (!file || conversationClosed) {
            return;
        }
        try {
            setStatus("Receiving…");
            await ingestBlob("IMAGE", file, file.name || "image.jpg", {});
            trace.image += 1;
            updateTraceUI();
            showReceived("image");
        } catch (err) {
            appendMessage("error", err.message);
        }
        imageFileInput.value = "";
        setModalityActive("text");
        setStatus("");
    }

    async function openCamera() {
        if (conversationClosed || !sessionId) {
            return;
        }
        try {
            setStatus("Opening…");
            cameraStream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: "environment" },
            });
            cameraPreview.srcObject = cameraStream;
            cameraOverlay.hidden = false;
            setModalityActive("camera");
            setStatus("");
        } catch (err) {
            setStatus("Camera unavailable");
            appendMessage("error", err.message || "Camera unavailable.");
        }
    }

    function closeCamera() {
        if (cameraStream) {
            cameraStream.getTracks().forEach(function (t) { t.stop(); });
            cameraStream = null;
        }
        cameraPreview.srcObject = null;
        cameraOverlay.hidden = true;
        setModalityActive("text");
        setStatus("");
    }

    async function captureCameraFrame() {
        const video = cameraPreview;
        const canvas = document.createElement("canvas");
        canvas.width = video.videoWidth || 640;
        canvas.height = video.videoHeight || 480;
        const ctx = canvas.getContext("2d");
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        canvas.toBlob(async function (blob) {
            closeCamera();
            if (!blob) {
                appendMessage("error", "Capture failed.");
                return;
            }
            try {
                setStatus("Receiving…");
                await ingestBlob("CAMERA", blob, "camera.jpg", {});
                trace.camera += 1;
                updateTraceUI();
                showReceived("camera");
            } catch (err) {
                appendMessage("error", err.message);
            }
        }, "image/jpeg", 0.92);
    }

    btnEnter.addEventListener("click", beginSession);
    btnSend.addEventListener("click", sendMessage);
    btnVoice.addEventListener("click", toggleVoiceRecording);
    btnImage.addEventListener("click", function () {
        setModalityActive("image");
        imageFileInput.click();
    });
    btnCamera.addEventListener("click", openCamera);
    btnCameraCapture.addEventListener("click", captureCameraFrame);
    btnCameraCancel.addEventListener("click", closeCamera);

    if (btnToDeck) {
        btnToDeck.addEventListener("click", function () {
            buildDeck();
            showScreen("deck");
        });
    }

    if (btnDeckContinue) {
        btnDeckContinue.addEventListener("click", runBlackoutThenReveal);
    }

    imageFileInput.addEventListener("change", function () {
        const file = imageFileInput.files && imageFileInput.files[0];
        if (file) {
            handleImageFile(file);
        }
    });

    modalityButtons.forEach(function (btn) {
        if (btn.getAttribute("data-modality") === "text") {
            btn.addEventListener("click", function () {
                setModalityActive("text");
                messageInput.focus();
            });
        }
    });

    messageInput.addEventListener("focus", resetComposerTiming);
    messageInput.addEventListener("input", function () {
        if (!firstInputAt) {
            firstInputAt = Date.now();
        }
    });

    messageInput.addEventListener("keydown", function (event) {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            sendMessage();
        }
    });

    buildDeck();
    updateTraceUI();
})();
