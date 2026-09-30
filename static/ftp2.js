/**
 * FTP 2.0 participant shell — entry, conversation, multimodal ingest.
 * POST /api/session/start on ENTER; POST /api/chat for text; POST /api/input/ingest for media.
 */

(function () {
    "use strict";

    let sessionId = null;
    let conversationClosed = false;
    let mediaRecorder = null;
    let audioChunks = [];
    let cameraStream = null;

    const screenEntry = document.getElementById("screen-entry");
    const screenConversation = document.getElementById("screen-conversation");
    const btnEnter = document.getElementById("btn-enter");
    const btnSend = document.getElementById("btn-send");
    const btnVoice = document.getElementById("btn-voice");
    const btnImage = document.getElementById("btn-image");
    const btnCamera = document.getElementById("btn-camera");
    const imageFileInput = document.getElementById("image-file-input");
    const messageInput = document.getElementById("message-input");
    const conversationEl = document.getElementById("conversation");
    const cameraOverlay = document.getElementById("camera-overlay");
    const cameraPreview = document.getElementById("camera-preview");
    const btnCameraCapture = document.getElementById("btn-camera-capture");
    const btnCameraCancel = document.getElementById("btn-camera-cancel");
    const modalityButtons = document.querySelectorAll(".ftp2-modality__btn");

    function setModalityActive(modality) {
        modalityButtons.forEach(function (btn) {
            btn.classList.toggle(
                "ftp2-modality__btn--active",
                btn.getAttribute("data-modality") === modality
            );
        });
    }

    function scrollConversationToEnd() {
        conversationEl.scrollTop = conversationEl.scrollHeight;
    }

    function appendMessage(role, text) {
        const block = document.createElement("article");
        const isUser = role === "user";
        const isError = role === "error";
        const isNotice = role === "notice";
        let modClass = "parrot";
        if (isUser) {
            modClass = "user";
        } else if (isError) {
            modClass = "error";
        } else if (isNotice) {
            modClass = "notice";
        }
        block.className = "ftp2-message ftp2-message--" + modClass;

        const label = document.createElement("div");
        label.className = "ftp2-message__label";
        if (isUser) {
            label.textContent = "You";
        } else if (isError) {
            label.textContent = "Notice";
        } else if (isNotice) {
            label.textContent = "Shared";
        } else {
            label.textContent = "Parrot";
        }

        const body = document.createElement("div");
        body.className = "ftp2-message__body";
        body.textContent = text;

        block.appendChild(label);
        block.appendChild(body);
        conversationEl.appendChild(block);
        scrollConversationToEnd();
    }

    function setComposerEnabled(enabled) {
        messageInput.disabled = !enabled;
        btnSend.disabled = !enabled;
        btnVoice.disabled = !enabled;
        btnImage.disabled = !enabled;
        btnCamera.disabled = !enabled;
    }

    async function beginSession() {
        btnEnter.disabled = true;
        btnEnter.textContent = "…";
        try {
            const response = await fetch("/api/session/start", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
            });
            const data = await response.json();
            if (!response.ok || !data.session_id) {
                throw new Error(data.error || "Could not start session.");
            }
            sessionId = data.session_id;
            screenEntry.classList.remove("ftp2-screen--active");
            screenEntry.hidden = true;
            screenConversation.hidden = false;
            screenConversation.classList.add("ftp2-screen--active");
            messageInput.focus();
        } catch (err) {
            btnEnter.disabled = false;
            btnEnter.textContent = "ENTER";
            alert(err.message || "Connection failed.");
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

        appendMessage("user", text);
        messageInput.value = "";
        setComposerEnabled(false);
        btnSend.textContent = "…";

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    session_id: sessionId,
                    message: text,
                }),
            });

            const data = await response.json();

            if (!response.ok || data.error) {
                appendMessage(
                    "error",
                    data.error || "The request could not be completed."
                );
                return;
            }

            if (data.session_id) {
                sessionId = data.session_id;
            }

            if (data.response) {
                appendMessage("parrot", data.response);
            }

            if (data.closed) {
                conversationClosed = true;
                setComposerEnabled(false);
                messageInput.placeholder = "This conversation has ended.";
            }
        } catch (err) {
            appendMessage("error", err.message || "Connection failed.");
        } finally {
            if (!conversationClosed) {
                setComposerEnabled(true);
                btnSend.textContent = "SEND";
                messageInput.focus();
            } else {
                btnSend.textContent = "SEND";
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
                btnVoice.textContent = "Voice";
                const blob = new Blob(audioChunks, { type: "audio/webm" });
                const durationMs = Date.now() - startedAt;
                try {
                    await ingestBlob("AUDIO", blob, "voice.webm", { duration_ms: durationMs });
                    appendMessage("notice", "You shared a voice recording.");
                } catch (err) {
                    appendMessage("error", err.message);
                }
            };
            mediaRecorder.start();
            btnVoice.textContent = "Stop";
            setModalityActive("voice");
        } catch (err) {
            appendMessage("error", err.message || "Microphone unavailable.");
        }
    }

    async function handleImageFile(file) {
        if (!file || conversationClosed) {
            return;
        }
        try {
            await ingestBlob("IMAGE", file, file.name || "image.jpg", {});
            appendMessage("notice", "You shared an image.");
        } catch (err) {
            appendMessage("error", err.message);
        }
        imageFileInput.value = "";
        setModalityActive("text");
    }

    async function openCamera() {
        if (conversationClosed || !sessionId) {
            return;
        }
        try {
            cameraStream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: "environment" },
            });
            cameraPreview.srcObject = cameraStream;
            cameraOverlay.hidden = false;
            setModalityActive("camera");
        } catch (err) {
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
                await ingestBlob("CAMERA", blob, "camera.jpg", {});
                appendMessage("notice", "You shared a camera image.");
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

    messageInput.addEventListener("keydown", function (event) {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            sendMessage();
        }
    });
})();
