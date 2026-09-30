/**
 * FTP 2.0 participant shell — entry and conversation only.
 * Uses POST /api/chat with { session_id, message }.
 */

(function () {
    "use strict";

    let sessionId = null;
    let conversationClosed = false;

    const screenEntry = document.getElementById("screen-entry");
    const screenConversation = document.getElementById("screen-conversation");
    const btnEnter = document.getElementById("btn-enter");
    const btnSend = document.getElementById("btn-send");
    const messageInput = document.getElementById("message-input");
    const conversationEl = document.getElementById("conversation");

    function showConversation() {
        screenEntry.classList.remove("ftp2-screen--active");
        screenEntry.hidden = true;
        screenConversation.hidden = false;
        screenConversation.classList.add("ftp2-screen--active");
        messageInput.focus();
    }

    function scrollConversationToEnd() {
        conversationEl.scrollTop = conversationEl.scrollHeight;
    }

    function appendMessage(role, text) {
        const block = document.createElement("article");
        const isUser = role === "user";
        const isError = role === "error";
        block.className = "ftp2-message ftp2-message--" + (
            isUser ? "user" : isError ? "error" : "parrot"
        );

        const label = document.createElement("div");
        label.className = "ftp2-message__label";
        label.textContent = isUser ? "You" : isError ? "Notice" : "Parrot";

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

    btnEnter.addEventListener("click", showConversation);

    btnSend.addEventListener("click", sendMessage);

    messageInput.addEventListener("keydown", function (event) {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            sendMessage();
        }
    });
})();
