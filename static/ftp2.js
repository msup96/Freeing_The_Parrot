/* FTP 2.0 reference visual layer backed by the existing Flask lifecycle. */
(function () {
    "use strict";

    const CARDS = [
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
    const BEHAVIOR_PRESENTATION = {
        understanding: ["understanding", "I am listening."],
        mirroring: ["mirroring", "I hear you."],
        absurd: ["absurd", "I was saying something."],
        memory_loss: ["memory_loss", "Where were we?"],
        roast: ["roast", "Are you sure?"],
        system_glitch: ["system_glitch", "..."],
        help_me: ["help_me", "Help me follow."],
        mixed: ["mixed", "I am still listening."],
        banana: ["banana", "..."],
        listening: ["listening", "I am listening."],
        idle: ["idle", ""],
        intervention: ["intervention", "..."]
    };
    const session = {
        id: null,
        startedAt: Date.now(),
        text: "",
        modalities: {},
        messages: [],
        card: null,
        trace: { turns: 0, pauses: 0, questions: 0, repeats: 0 },
        previousText: "",
        previousSubmitAt: null
    };
    let audioRecorder = null;
    let audioChunks = [];
    let cameraStream = null;
    let processing = false;

    const $ = (selector) => document.querySelector(selector);
    const screens = [1, 2, 3, 4, 6, 7, 8, 9];

    function go(number) {
        screens.forEach((value) => {
            const screen = $("#s" + value);
            if (screen) screen.classList.toggle("on", value === number);
        });
        if (number === 4) $("#say").focus();
        if (number === 6) buildCards();
        if (number === 7) reveal();
        if (number === 8) buildWall();
    }

    async function requestJson(url, options) {
        const response = await fetch(url, options);
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "The apparatus could not complete that action.");
        return data;
    }

    function formDataFor(modality, blob, filename, metadata) {
        const form = new FormData();
        form.append("session_id", session.id);
        form.append("modality", modality);
        form.append("file", blob, filename);
        if (metadata) form.append("metadata", JSON.stringify(metadata));
        return form;
    }

    async function ingest(modality, blob, filename, metadata) {
        await requestJson("/api/input/ingest", { method: "POST", body: formDataFor(modality, blob, filename, metadata) });
        session.modalities[modality] = true;
    }

    function slotMarkup(name, description, graphic) {
        return "<div class=\"mono\">" + name + "</div>" + graphic + "<div class=\"vt\">" + description + "</div><div class=\"row\" style=\"gap:8px\"></div>";
    }

    function setSlot(slot, state) {
        const row = slot.querySelector(".row");
        const description = slot.querySelector(".vt");
        slot.classList.remove("live", "got");
        row.innerHTML = "";
        if (state === "got") {
            slot.classList.add("got");
            description.innerHTML = '<span class="st">RECEIVED</span>';
            const undo = button("Undo", "dk");
            undo.onclick = () => { delete session.modalities[slot.dataset.modality]; setSlot(slot, "idle"); checkReady(); };
            row.appendChild(undo);
            return;
        }
        const action = button(slot.dataset.modality === "WRITE" ? "Keep" : slot.dataset.modality, "dk");
        action.onclick = () => activateSlot(slot);
        row.appendChild(action);
    }

    function button(label, style) {
        const element = document.createElement("button");
        element.type = "button";
        element.className = "act" + (style === "dk" ? " dk" : "");
        element.style.cssText = "padding:8px 16px;font-size:11px";
        element.textContent = label;
        return element;
    }

    function buildSlots() {
        const definitions = [
            ["WRITE", "Paper receives your words", '<textarea class="paperin" aria-label="Write" placeholder="Write here"></textarea>'],
            ["SPEAK", "Ceramic listens", '<div class="mat"><svg width="96" height="96" viewBox="0 0 96 96" aria-hidden="true"><circle cx="48" cy="48" r="38" fill="#E6D7B8"/><circle cx="48" cy="48" r="26" fill="none" stroke="#171411" stroke-dasharray="2 5" stroke-width="3"/><circle cx="48" cy="48" r="8" fill="#171411"/></svg></div>'],
            ["SHOW", "The tray takes an object", '<div class="mat"><svg width="96" height="96" viewBox="0 0 96 96" aria-hidden="true"><rect x="6" y="40" width="84" height="16" fill="#000"/><rect x="10" y="44" width="76" height="8" fill="#07110D" stroke="#C4A035"/><path d="M20 40V16h56v24" fill="#D8C49D" stroke="#171411"/></svg></div>'],
            ["LOOK", "The glass observes", '<div class="mat"><svg width="96" height="96" viewBox="0 0 96 96" aria-hidden="true"><rect x="8" y="16" width="80" height="64" fill="#102019" stroke="#C4A035" stroke-width="3"/><circle cx="48" cy="48" r="20" fill="#07110D" stroke="#2A6B5C" stroke-width="3"/><ellipse cx="41" cy="41" rx="6" ry="3" fill="#E6D7B8" opacity=".5"/></svg></div>'],
        ];
        const container = $("#slots");
        definitions.forEach(([name, description, graphic]) => {
            const slot = document.createElement("div");
            slot.className = "slot";
            slot.dataset.modality = name;
            slot.innerHTML = slotMarkup(name, description, graphic);
            container.appendChild(slot);
            setSlot(slot, "idle");
        });
    }

    async function activateSlot(slot) {
        const modality = slot.dataset.modality;
        const description = slot.querySelector(".vt");
        if (modality === "WRITE") {
            const text = slot.querySelector("textarea").value.trim();
            if (!text) { description.innerHTML = '<span class="err">Nothing written yet. Write a few words, then keep.</span>'; return; }
            session.text = text;
            session.modalities.WRITE = true;
            setSlot(slot, "got");
            checkReady();
            return;
        }
        slot.classList.add("live");
        description.textContent = modality === "SPEAK" ? "RECORDING" : "OPEN";
        try {
            if (modality === "SPEAK") await recordAudio(slot);
            if (modality === "SHOW") await chooseImage(slot);
            if (modality === "LOOK") await captureCamera(slot);
        } catch (error) {
            description.textContent = error.message || "Unavailable in this environment.";
            slot.classList.remove("live");
        }
    }

    function chooseImage(slot) {
        return new Promise((resolve, reject) => {
            const input = document.createElement("input");
            input.type = "file";
            input.accept = "image/*";
            input.onchange = async () => {
                const file = input.files && input.files[0];
                if (!file) return reject(new Error("No image selected."));
                try { await ingest("IMAGE", file, file.name || "image.jpg"); setSlot(slot, "got"); checkReady(); resolve(); }
                catch (error) { reject(error); }
            };
            input.click();
        });
    }

    function recordAudio(slot) {
        return new Promise(async (resolve, reject) => {
            if (!navigator.mediaDevices || !window.MediaRecorder) return reject(new Error("Microphone unavailable."));
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                audioChunks = [];
                const startedAt = Date.now();
                audioRecorder = new MediaRecorder(stream);
                audioRecorder.ondataavailable = (event) => { if (event.data.size) audioChunks.push(event.data); };
                audioRecorder.onstop = async () => {
                    stream.getTracks().forEach((track) => track.stop());
                    try { await ingest("AUDIO", new Blob(audioChunks, { type: "audio/webm" }), "voice.webm", { duration_ms: Date.now() - startedAt }); setSlot(slot, "got"); checkReady(); resolve(); }
                    catch (error) { reject(error); }
                };
                audioRecorder.start();
                const stop = button("Done", "");
                slot.querySelector(".row").appendChild(stop);
                stop.onclick = () => audioRecorder.stop();
            } catch (error) { reject(error); }
        });
    }

    async function captureCamera(slot) {
        if (!navigator.mediaDevices) throw new Error("Camera unavailable.");
        cameraStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
        const video = document.createElement("video");
        video.autoplay = true;
        video.playsInline = true;
        video.srcObject = cameraStream;
        slot.querySelector(".mat").replaceChildren(video);
        await new Promise((resolve) => setTimeout(resolve, 300));
        const canvas = document.createElement("canvas");
        canvas.width = video.videoWidth || 640;
        canvas.height = video.videoHeight || 480;
        canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
        const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", .92));
        cameraStream.getTracks().forEach((track) => track.stop());
        cameraStream = null;
        if (!blob) throw new Error("Capture failed.");
        await ingest("CAMERA", blob, "camera.jpg");
        setSlot(slot, "got");
        checkReady();
    }

    function checkReady() { $("#go3").disabled = !Object.values(session.modalities).some(Boolean); }

    function setParrotPresentation(behavior, phase) {
        const presentation = BEHAVIOR_PRESENTATION[behavior] || BEHAVIOR_PRESENTATION.listening;
        const parrot = $("#par");
        parrot.dataset.behavior = presentation[0];
        parrot.dataset.phase = phase || "settled";
        parrot.closest(".stage").dataset.behavior = presentation[0];
        $("#pst").textContent = presentation[1];
    }

    function observeMessage(text) {
        const normalized = text.trim().toLowerCase();
        const now = Date.now();
        session.trace.turns += 1;
        session.trace.questions += text.includes("?") ? 1 : 0;
        session.trace.repeats += normalized && normalized === session.previousText ? 1 : 0;
        session.trace.pauses += session.previousSubmitAt && now - session.previousSubmitAt > 4000 ? 1 : 0;
        session.previousText = normalized;
        session.previousSubmitAt = now;
        updateObservationTrace();
    }

    function updateObservationTrace() {
        Object.entries(session.trace).forEach(([name, count]) => {
            const mark = document.querySelector('[data-mark="' + name + '"]');
            if (mark) mark.style.setProperty("--mark-length", Math.min(12, 2 + count) + "ch");
        });
    }

    async function beginSession() {
        try {
            const data = await requestJson("/api/session/start", { method: "POST", headers: { "Content-Type": "application/json" } });
            session.id = data.session_id;
            session.startedAt = Date.now();
            go(2);
        } catch (error) { showError(error.message); }
    }

    async function beginProcessing() {
        if (processing) return;
        processing = true;
        go(3);
        try {
            if (session.text) {
                const result = await requestJson("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id: session.id, message: session.text }) });
                session.messages.push({ role: "user", text: session.text }, { role: "parrot", text: result.response || "" });
                observeMessage(session.text);
                setParrotPresentation(result.parrot_behavior, "responding");
            }
            go(4);
            if (session.messages.length) line(session.messages[session.messages.length - 1].text, "");
        } catch (error) { processing = false; showError(error.message); go(2); }
    }

    function showError(message) { const error = $("#flow-error"); error.textContent = message; error.hidden = false; }
    function line(text, className) { const element = document.createElement("div"); element.className = "pl " + (className || ""); element.textContent = text; $("#log").appendChild(element); while ($("#log").children.length > 6) $("#log").firstChild.remove(); }
    function slip(text) { const element = document.createElement("div"); element.className = "slip"; element.textContent = text; $("#log").appendChild(element); }

    async function say() {
        const input = $("#say");
        const text = input.value.trim();
        if (!text || !session.id) return;
        input.value = "";
        slip(text);
        $("#par").dataset.phase = "thinking";
        try {
            const result = await requestJson("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id: session.id, message: text }) });
            observeMessage(text);
            session.messages.push({ role: "user", text }, { role: "parrot", text: result.response || "" });
            setParrotPresentation(result.parrot_behavior, "responding");
            const glitch = ["system_glitch", "intervention"].includes(result.parrot_behavior);
            line(result.response || "", glitch ? "g" : "");
            if (result.closed) {
                $("#say").disabled = true;
                $("#send").disabled = true;
                $("#done").hidden = false;
            }
            if (session.messages.filter((message) => message.role === "user").length >= 2) $("#done").hidden = false;
        } catch (error) { $("#par").dataset.phase = "settled"; showError(error.message); }
    }

    async function finishConversation() {
        try {
            const result = await requestJson("/api/end-conversation", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id: session.id }) });
            if (result.message) line(result.message, "g");
            go(6);
        } catch (error) { showError(error.message); }
    }

    function buildCards() {
        const vitrine = $("#vit");
        if (vitrine.children.length) return;
        CARDS.forEach(([title, description], index) => {
            const card = document.createElement("button");
            card.type = "button";
            card.className = "card";
            card.innerHTML = "<b>CARD " + String(index + 1).padStart(2, "0") + "</b><span>" + title + "</span>";
            card.onclick = () => openCard(index, card);
            vitrine.appendChild(card);
        });
    }

    function openCard(index, card) {
        document.querySelectorAll(".card").forEach((element) => element.classList.remove("up"));
        card.classList.add("up");
        const box = $("#cardbox");
        box.innerHTML = "";
        const detail = document.createElement("div");
        detail.className = "big";
        detail.innerHTML = '<span class="mono">Card ' + String(index + 1).padStart(2, "0") + " of 27</span><h3>" + CARDS[index][0] + "</h3><p>" + CARDS[index][1] + "</p>";
        const resonate = button("Resonates", "");
        detail.appendChild(resonate);
        resonate.onclick = async () => {
            try {
                await requestJson("/api/session-lifecycle", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id: session.id, action: "card_selection", card_index: index + 1, card_text: CARDS[index][1] }) });
                session.card = index;
                go(7);
            } catch (error) { showError(error.message); }
        };
        box.appendChild(detail);
    }

    function record(text, tag) { return '<div class="rec"><span>' + escapeHtml(text) + '</span><span class="tag">' + tag + '</span></div>'; }
    function escapeHtml(value) { return String(value).replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[character])); }

    function reveal() {
        const container = $("#dt");
        const screen = $("#s7");
        screen.style.opacity = 0;
        setTimeout(() => {
            screen.style.opacity = 1;
            container.innerHTML = '<div class="stmt" id="st">You played your cards.<br>Now I play mine.</div>';
            setTimeout(() => {
                $("#st").classList.add("m", "gl");
                const ladder = document.createElement("div");
                ladder.className = "lad";
                const userMessages = session.messages.filter((message) => message.role === "user");
                const rows = [
                    ["What you gave", (session.text ? record('Written: "' + session.text + '"', "GIVEN") : "") + userMessages.map((message) => record('To the Parrot: "' + message.text + '"', "GIVEN")).join("") + (session.card !== null ? record("Card " + String(session.card + 1).padStart(2, "0") + " marked as resonating", "GIVEN") : "")],
                    ["What we received", record(Object.keys(session.modalities).length + " input slot(s) marked received", "OBSERVED") + record(userMessages.length + " message(s) to the Parrot", "OBSERVED")],
                    ["What we observed", record("Session length so far: " + Math.round((Date.now() - session.startedAt) / 1000) + " seconds", "OBSERVED") + record("Interaction count: " + (Object.keys(session.modalities).length + userMessages.length + (session.card === null ? 0 : 1)), "OBSERVED") + record(session.trace.pauses + " pauses between messages", "OBSERVED") + record(session.trace.questions + " questions", "OBSERVED") + record(session.trace.repeats + " repeated messages", "OBSERVED")],
                    ["What we derived", session.card === null ? '<div class="none">No card was marked.</div>' : record("Card " + String(session.card + 1).padStart(2, "0") + " is one you said resonates. That is all it shows.", "DERIVED")],
                    ["What we constructed", '<div class="none">The existing system records patterns and responses. It does not know what you felt.</div>'],
                    ["What we cannot know", record("Whether the card fits you or fits almost anyone.", "LIMIT") + record("What you felt. Only what you did.", "LIMIT") + record("Whether you were understood or interpreted.", "LIMIT")],
                ];
                rows.forEach(([heading, body], index) => { const rung = document.createElement("div"); rung.className = "rung"; rung.style.animationDelay = (index * .6) + "s"; rung.innerHTML = "<h4>" + heading.toUpperCase() + "</h4>" + (body || '<div class="none">Nothing.</div>'); ladder.appendChild(rung); });
                container.appendChild(ladder);
                const continueButton = button("Continue", "");
                continueButton.style.margin = "48px auto 0";
                continueButton.onclick = async () => {
                    try { await requestJson("/api/session-lifecycle", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id: session.id, action: "reveal" }) }); go(8); }
                    catch (error) { showError(error.message); }
                };
                container.appendChild(continueButton);
            }, 1400);
        }, 1200);
    }

    function buildWall() {
        const tiles = [];
        if (session.text) tiles.push(['"' + session.text + '"', "Original input", "GIVEN · WRITE"]);
        session.messages.filter((message) => message.role === "user").forEach((message) => tiles.push(['"' + message.text + '"', "To the Parrot", "GIVEN · CONVERSATION"]));
        if (session.card !== null) tiles.push([CARDS[session.card][0] + ": " + CARDS[session.card][1], "Card " + String(session.card + 1).padStart(2, "0"), "CHOSEN"]);
        tiles.push([Math.round((Date.now() - session.startedAt) / 1000) + " seconds, " + session.messages.length + " interactions", "Session trace", "OBSERVED"]);
        $("#tiles").innerHTML = tiles.map(([text, label, tag]) => '<div class="tile"><span class="tag">' + escapeHtml(tag) + '</span><div>' + escapeHtml(text) + '</div><span class="tag">' + escapeHtml(label) + '</span></div>').join("");
    }

    async function endSession(consentType) {
        $("#private").disabled = true;
        $("#wall").disabled = true;
        try {
            await requestJson("/api/session-lifecycle", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id: session.id, action: "consent", consent_type: consentType }) });
            await requestJson("/api/session-output", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id: session.id }) });
            go(9);
            const end = $("#s9");
            end.style.opacity = 1;
            setTimeout(async () => {
                try { await requestJson("/api/session-output-reset", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id: session.id, consent_type: consentType }) }); }
                catch (error) { showError(error.message); }
                setTimeout(() => { end.innerHTML = ""; end.style.opacity = 1; }, 3000);
            }, 1200);
        } catch (error) { $("#private").disabled = false; $("#wall").disabled = false; showError(error.message); }
    }

    $("#enter").onclick = beginSession;
    $("#go3").onclick = beginProcessing;
    $("#send").onclick = say;
    $("#say").onkeydown = (event) => { if (event.key === "Enter") { event.preventDefault(); say(); } };
    $("#done").onclick = finishConversation;
    $("#private").onclick = () => endSession("KEEP_PRIVATE");
    $("#wall").onclick = () => endSession("SHARE");
    buildSlots();
})();