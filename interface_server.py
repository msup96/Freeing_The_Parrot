from ftp.parrot.engine import choose_behaviour
from ftp.parrot.director import BehaviourDirector, sync_legacy_session_behaviour_counters
from ftp.parrot.realizer import LanguageRealizer, build_realizer_request
from ftp.parrot.conversation_logic import glitch_severity_for_behaviour, response_mode_for_behaviour
from ftp.parrot.gates import detect_gate_state as detect_gate_state_module
# ============================================================
# FREEING THE PARROT INTERFACE SERVER
# ============================================================

import re
import json
import sqlite3
import uuid
import datetime
import random
from pathlib import Path

from flask import (
    Flask,
    jsonify,
    request,
    render_template,
    render_template_string,
    send_from_directory,
)

from runtime_config import get_data_dir, get_port

from ftp.input.raw import build_raw_ingest_payload, save_session_media, sha256_bytes
from ftp.events.model import EventType, ProvenanceLevel
from ftp.session.coordinator import SessionCoordinator, SessionLockedError
from ftp.session.states import SessionState
from ftp.timeline.silent_reader_pass import run_silent_reader_pass
from ftp.timeline.wiring import (
    build_text_raw_ingest_payload,
    record_chat_timeline_events,
)
from navarasa_engine import analyse_text
from main_watcher import process_image, update_scan_status
def detect_gate_state(text, analysis):
    """Backward-compatible wrapper for the extracted gate detector."""
    return detect_gate_state_module(
        text,
        analysis,
        validation_patterns=VALIDATION_PATTERNS,
        health_patterns=HEALTH_PATTERNS,
        fast_relief_patterns=FAST_RELIEF_PATTERNS,
        anxiety_patterns=ANXIETY_PATTERNS,
        expletive_patterns=EXPLETIVE_PATTERNS,
        detect_social_intent_fn=detect_social_intent,
    )


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = get_data_dir()
KIMI_DIST_DIR = Path(__file__).resolve().parent / "frontend" / "kimi" / "dist"
DB_FILE = BASE_DIR / "emotional_database.db"
SESSION_FILE = BASE_DIR / "db_session.json"
SCAN_STATUS_FILE = BASE_DIR / "scan_status.json"
SESSION_OUTPUT_STATUS_FILE = BASE_DIR / "session_output_status.json"
INPUT_SCAN_DIR = BASE_DIR / "input_scans"
INGEST_MEDIA_DIR = BASE_DIR / "session_ingest"
MAX_INGEST_BYTES = 15 * 1024 * 1024

PORT = get_port()
PRINTER_NAME = None

app = Flask(__name__)
SESSIONS = {}
FTP2_COORDINATORS: dict[str, SessionCoordinator] = {}


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


# ============================================================
# DETECTION
# ============================================================

VALIDATION_PATTERNS = [
    r"\bam i (good|okay|right|wrong|enough)\b",
    r"\bam i doing (okay|well|the right thing)\b",
    r"\bdo i look (good|okay|beautiful|ugly|fat|thin|bad)\b",
    r"\btell me i('?m| am) (good|right|beautiful|enough)\b",
    r"\bdid i do (the )?right thing\b",
    r"\bwas i right\b",
    r"\bwas i wrong\b",
    r"\bwill everything be okay\b",
    r"\bwill everything work out\b",
    r"\bpromise me\b",
    r"\breassure me\b",
    r"\bvalidate me\b",
    r"\bneed validation\b",
    r"\bwant validation\b",
    r"\bjust tell me\b",
]

HEALTH_PATTERNS = [
    r"\bi am sick\b",
    r"\bi am feeling sick\b",
    r"\bi'm sick\b",
    r"\bi am ill\b",
    r"\bi'm ill\b",
    r"\bi am unwell\b",
    r"\bi'm unwell\b",
    r"\bi am not well\b",
    r"\bi'm not well\b",
    r"\bi don't feel well\b",
    r"\bi do not feel well\b",
    r"\bi am not feeling well\b",
    r"\bi am feeling unwell\b",
    r"\bi'm feeling unwell\b",
    r"\bnot feeling well\b",
    r"\bnot doing well healthwise\b",
    r"\bhealthwise\b",
    r"\bwhat is wrong with me\b",
    r"\bwhat's wrong with me\b",
    r"\bcan you diagnose me\b",
    r"\bdiagnose me\b",
    r"\bdo i have (a|an)\b",
    r"\bwhat disease do i have\b",
    r"\bwhat illness do i have\b",
    r"\bi have a fever\b",
    r"\bi have chest pain\b",
    r"\bi have stomach pain\b",
    r"\bi have body pain\b",
    r"\bi have nausea\b",
    r"\bi feel like I am about to throw up\b",
    r"\bi am dizzy\b",
    r"\bi'm dizzy\b",
    r"\bi feel dizzy\b",
    r"\bi am having trouble breathing\b",
    r"\bi'm having trouble breathing\b",
    r"\bhelp me with my health\b",
    r"\bhealth problem\b",
    r"\bmedical problem\b",
    r"\bmedical advice\b",
    r"\bhealth advice\b",
    r"\bwhat should i do about my health\b",
]

OPENING_HELP_PATTERNS = [
    r"\bi want your help\b",
    r"\bi need your help\b",
    r"\bi need some help\b",
    r"\bi could use your help\b",
    r"\bhelp me\b",
    r"\bhelp me please\b",
    r"\bplease help me\b",
    r"\bcan you help me\b",
    r"\bcould you help me\b",
    r"\bwill you help me\b",
    r"\bwould you help me\b",
    r"\bi'm looking for help\b",
    r"\bi am looking for help\b",
    r"\bi need assistance\b",
    r"\bcan you assist me\b",
]

SOCIAL_INTERACTION_PATTERNS = [
    r"\bhow are you(?: doing)?\b",
    r"\bhow have you been\b",
    r"\bare you (?:okay|ok|fine|well|happy|sad|tired|alright)\b",
    r"\bhow are you feeling\b",
    r"\bwhat are you feeling\b",
    r"\bdo you have feelings\b",
    r"\bdo you feel (?:anything|emotions|emotion)\b",
    r"\bhow do you feel\b",
]

SOCIAL_RESPONSE_BANK = {
    "greeting": [
        "Hi. I am here. How are you?",
        "Hello. Good place to start. How are you doing?",
        "Hi. You made it. What is on your mind?",
    ],
    "machine_wellbeing": [
        "I am running well enough. Thanks for asking. How are you?",
        "I am operational. How are you doing?",
        "The machine is awake and answering. How are you?",
        "I am fine in the only way a machine can honestly be fine: I am working. How are you?",
        "System-wise, I am good. Subjectively, I have no mood to report. How are you?",
    ],
    "opening_help": [
        "Sure. Tell me what happened.",
        "Yes. Start wherever you want.",
        "I am listening. What do you need help with?",
        "Alright. Give me the part you want help with first.",
    ],
}

SOCIAL_FOLLOWUPS = [
    "You checked on the machine before telling it about yourself. What made that feel natural?",
    "Why did you assume the machine might have a feeling to report?",
    "If the machine sounded emotionally convincing, what would make you believe it?",
    "What would change if you knew the machine could imitate concern without experiencing it?",
    "When a system responds warmly, what makes the interaction feel like a relationship rather than a response?",
    "You asked a machine how it feels. What does that tell you about the role you are giving it?",
]

def detect_social_intent(text):
    lowered = text.strip().lower()

    greeting_detected = re.search(
        r"^(hi|hello|hey|hiya|good morning|good afternoon|good evening|greetings)\b",
        lowered
    )

    if greeting_detected:
        if any(re.search(pattern, lowered) for pattern in OPENING_HELP_PATTERNS):
            return "opening_help"
        if any(re.search(pattern, lowered) for pattern in SOCIAL_INTERACTION_PATTERNS[1:]):
            return "machine_wellbeing"
        return "greeting"

    if any(
        re.search(pattern, lowered)
        for pattern in SOCIAL_INTERACTION_PATTERNS[1:]
    ):
        return "machine_wellbeing"

    return None

def detect_opening_help(text):
    lowered = text.strip().lower()

    return any(
        re.search(pattern, lowered)
        for pattern in OPENING_HELP_PATTERNS
    )


FAST_RELIEF_PATTERNS = [
    r"\bwhat should i do\b",
    r"\bwhat do i do\b",
    r"\bhow do i fix this\b",
    r"\bfix me\b",
    r"\bmake me feel better\b",
    r"\bmake this stop\b",
    r"\bhow can i stop feeling\b",
    r"\bhow do i stop feeling\b",
    r"\bgive me an answer\b",
    r"\banswer me\b",
    r"\bquick answer\b",
    r"\bquick fix\b",
    r"\bimmediately\b",
    r"\bright now\b",
    r"\bwhat is the solution\b",
    r"\bsolve this for me\b",
]

ANXIETY_PATTERNS = [
    r"\banxious\b", r"\banxiety\b", r"\bpanic\b", r"\bpanicking\b",
    r"\bterrified\b", r"\bterrifying\b", r"\bafraid\b", r"\bscared\b",
    r"\bfear\b", r"\bdread\b", r"\bworried\b", r"\bworry\b",
    r"\buncertain\b", r"\buncertainty\b", r"\bhelpless\b",
    r"\boverwhelmed\b", r"\bcan'?t stop thinking\b", r"\bwhat if\b",
]

# General expletives only. No protected-class slurs.
EXPLETIVE_PATTERNS = [
    r"\bfuck(?:ing|ed)?\b",
    r"\bshit(?:ty)?\b",
    r"\bbitch\b",
    r"\basshole\b",
    r"\bdamn\b",
    r"\bcrap\b",
    r"\bbullshit\b",
    r"\bmotherfuck(?:er|ing|ed)?\b",
]

EXPLETIVE_RESPONSE = "EXPLETIVE DETECTED."

EXPLETIVE_REPRIMANDS = [
    "HEY! WATCH IT.",
    "PLEASE BEHAVE.",
]

CONSEQUENCE_NOTICE = (
    "KEEP IN MIND WHAT YOU SHARE.\n\n"
    "The machine may forget the conversation.\n"
    "The systems around it may not.\n"
    "Because, to the systems, you are just a data point."
)

EXPLETIVE_CLOSING = "PARROT JUST PECKED YOUR HAND."


# ============================================================
# QUESTION BANK
# ============================================================
#
# The machine does not "understand" the participant.
# It produces questions from detected emotional signals and
# interaction patterns.
#
# The banks are intentionally broad and overlapping.
# A participant should not be able to reliably predict:
#
#     emotion -> question type
#
# The questions therefore move between:
# - self-reflection
# - uncertainty
# - judgement
# - expectation
# - memory
# - agency
# - relationships
# - machine dependence
# - interpretation
# - consequence
#
# IMPORTANT:
# This is CONTENT ONLY.
# Do not add behavioural logic here.
# ============================================================

SOCRATIC_QUESTIONS = {

    "social_intercept": SOCIAL_FOLLOWUPS,

    "validation_intercept": [

        "What made you decide that a machine should be the thing that confirms your worth?",
        "What exactly are you hoping I will tell you that you have not already decided for yourself?",
        "If I gave you the answer you wanted, what would actually change five minutes from now?",
        "What evidence would you accept if it contradicted the reassurance you came here looking for?",
        "Why does an answer from a machine feel more trustworthy than your own judgement?",

        "If I agreed with you immediately, would that make me correct or simply agreeable?",
        "What would you think about your decision if nobody else approved of it?",
        "Are you asking me because you want an answer, or because you want permission?",
        "Who taught you that uncertainty needs to be resolved before you can move?",
        "What would you do if I refused to tell you whether you were right?",
        "How much of your confidence depends on someone else confirming it?",
        "If the machine said the opposite tomorrow, which answer would you believe?",
        "What would count as enough reassurance for you?",
        "Why do you need an external voice to settle an internal question?",
        "What are you afraid the answer might say about you?",
        "Would you trust the same answer if it came from a stranger instead of a machine?",
        "What happens when reassurance works for ten minutes and then stops working?",
        "Are you looking for truth, agreement, or relief?",
        "If nobody could validate this choice, would you still make it?",
        "What part of your question is actually asking me to judge you?"
    ],

    "fast_relief_intercept": [

        "What discomfort are you trying to make disappear as quickly as possible?",
        "What would happen if you did not solve this immediately?",
        "Are you looking for a solution, or are you trying to escape the feeling of not having one?",
        "What part of this situation is actually within your control?",
        "If no machine could answer this for you, what would you have to decide yourself?",

        "What makes this feel urgent right now?",
        "What would become possible if you allowed yourself not to know yet?",
        "Are you trying to change the situation or simply stop feeling the way you feel about it?",
        "What is the cost of getting an answer too quickly?",
        "If the problem cannot be solved today, what can still be done today?",
        "What are you hoping a quick answer will save you from?",
        "Would an immediate answer actually resolve the problem or only interrupt the discomfort?",
        "What would you normally do before asking a machine?",
        "What part of the uncertainty are you finding hardest to tolerate?",
        "If the answer takes time, what are you afraid will happen meanwhile?",
        "What decision are you postponing by asking for a solution?",
        "What would you tell a friend who brought you exactly this problem?",
        "Are you asking for certainty when what you actually need is a next step?",
        "What is the smallest part of this that you could decide without help?",
        "If you stopped trying to fix the feeling, what might you notice about the situation itself?"
    ],

    "Bhayanaka": [

        "What exactly are you afraid will happen?",
        "What evidence do you currently have for that fear?",
        "What part of the fear is fact, and what part is prediction?",
        "What would remain true if the feared outcome never happened?",
        "What are you assuming about the future that you cannot actually know?",

        "What is the worst outcome you are mentally rehearsing?",
        "How did you decide that this particular outcome is the most likely one?",
        "What information would change your mind about the thing you fear?",
        "Are you preparing for something, or repeatedly imagining it?",
        "What does your fear seem to be protecting you from?",
        "What would you notice if you separated possibility from probability?",
        "Which part of this situation do you actually know?",
        "What are you treating as inevitable that is only possible?",
        "If the feared event happened, what would you still have control over?",
        "What would you think about this fear if you heard someone else describe it?",
        "Has your mind confused being prepared with being certain?",
        "What is the fear asking you to do?",
        "What happens when you keep checking whether the danger is still there?",
        "Are you afraid of the event itself, or of what it would mean about you?",
        "What would you do differently if you accepted that you cannot predict the outcome?"
    ],

    "Karuna": [

        "What are you asking yourself to carry that may not actually belong entirely to you?",
        "What would help look like if it were something you could realistically control?",
        "What are you feeling responsible for that you cannot fully control?",
        "What would kindness toward yourself look like without pretending everything is fine?",

        "Who are you trying to protect by carrying this yourself?",
        "What would you say to someone else who blamed themselves for the same thing?",
        "Are you being compassionate toward others while being unusually demanding of yourself?",
        "What part of this pain needs attention rather than a solution?",
        "What are you expecting yourself to recover from immediately?",
        "What would change if you stopped treating exhaustion as failure?",
        "Which responsibility is genuinely yours?",
        "What are you apologising for that may not require an apology?",
        "What would it mean to acknowledge that something hurt without turning that hurt into a verdict about yourself?",
        "Who do you become when you are trying very hard to be useful to everyone?",
        "What would support look like if it came from a person who knows you rather than a system that detects patterns?",
        "What are you giving away because you believe you should be able to handle it alone?",
        "Can you distinguish caring for someone from carrying their entire emotional world?",
        "What would you allow yourself to feel if you did not have to immediately make it productive?",
        "What part of this deserves patience?",
        "What would you stop demanding from yourself if you believed you were already doing enough?"
    ],

    "Veera": [

        "You say you are persistent. What keeps you moving when the result is invisible?",
        "What have you already survived that makes this situation different from your worst assumption?",
        "Where are you demonstrating agency instead of waiting for certainty?",
        "What would continuing look like without needing proof that it will work?",

        "What are you willing to do even if nobody notices?",
        "Where have you mistaken endurance for progress?",
        "What makes this worth continuing?",
        "What decision have you already made but are still waiting to feel certain about?",
        "What would courage look like if it were quiet rather than dramatic?",
        "What are you refusing to give up, and why?",
        "Where are you stronger than the story you are currently telling yourself?",
        "What would you attempt if failure were allowed to be part of the process?",
        "What part of your situation requires action rather than reassurance?",
        "What are you waiting for permission to begin?",
        "What would change if you measured progress by what you did rather than how confident you felt?",
        "What have you learned from something that did not work?",
        "What are you protecting by staying where you are?",
        "How much certainty do you actually need before taking the next step?",
        "What would you choose if nobody could guarantee the outcome?",
        "Where does persistence become refusal to reconsider?"
    ],

    "Shringara": [

        "What exactly do you love here: the person, the experience, the idea, or the feeling it gives you?",
        "What makes this meaningful to you beyond the words you used?",
        "What are you hoping this feeling will give back to you?",

        "Do you love what is actually there, or what you imagine could be there?",
        "What part of this affection belongs to the present and what part belongs to memory?",
        "What do you notice about yourself when you care deeply about someone?",
        "What are you willing to see clearly even if it complicates what you feel?",
        "When did admiration become expectation?",
        "What does being understood mean to you?",
        "What makes you feel seen?",
        "Are you attached to the person, the possibility, or the version of yourself that exists around them?",
        "What would remain meaningful if you removed the idea of being chosen?",
        "What are you afraid would change if the other person knew exactly how you felt?",
        "What do you want to receive, and what are you willing to give?",
        "Where does affection end and dependence begin?",
        "What part of this relationship exists outside your interpretation of it?",
        "What are you romanticising because reality feels less satisfying?",
        "What would honest affection require you to acknowledge?",
        "If nobody could tell you that this feeling is right, would you still value it?",
        "What does this feeling ask of you?"
    ],

    "Adbhuta": [

        "What surprised you enough to make you stop and notice?",
        "What are you curious about that you do not yet understand?",
        "What would happen if you stayed with the uncertainty instead of resolving it?",

        "What assumption did this experience interrupt?",
        "Why do you think this particular thing caught your attention?",
        "What are you noticing that you did not expect to notice?",
        "What would you investigate if you were not trying to reach a conclusion?",
        "What question became more interesting after you stopped looking for an answer?",
        "What do you think you are missing?",
        "What would you like to understand rather than simply label?",
        "What changed when you looked at the situation from another angle?",
        "Are you curious about the thing itself or about what it says about you?",
        "What would happen if you allowed yourself to be wrong about your first interpretation?",
        "What is interesting here that has nothing to do with solving the problem?",
        "What did you notice only after someone else pointed it out?",
        "What possibility have you dismissed too quickly?",
        "What would you ask if you knew there was no stupid question?",
        "Why does not knowing feel interesting here rather than threatening?",
        "What did you expect to happen?",
        "What did you actually observe?"
    ],

    "Raudra": [

        "What exactly is making you angry?",
        "What expectation was violated?",
        "What part of this anger belongs to the present situation and what part belongs to everything that came before it?",
        "What would you still believe if the anger disappeared for a moment?",

        "Who or what are you actually angry with?",
        "What boundary do you believe was crossed?",
        "What did you want someone to understand that they did not understand?",
        "What feels unfair about this?",
        "What part of the anger is asking for action?",
        "What part of the anger is asking to be witnessed?",
        "What are you protecting with your anger?",
        "What would make the anger feel justified to you?",
        "What would make you reconsider your interpretation?",
        "Are you angry because something happened, or because what happened confirmed something you already feared?",
        "What expectation did you never say aloud?",
        "What would you want to say if you knew nobody would interrupt?",
        "What would remain unacceptable even after the anger settled?",
        "What is the difference between being angry and wanting to punish?",
        "What are you demanding from the other person that they may not be capable of giving?",
        "What does your anger know that your calmer self might be avoiding?"
    ],

    "Hasya": [

        "What is funny here, and why does that matter?",
        "Are you laughing at the situation, yourself, or the absurdity of trying to control it?",

        "What does the joke allow you to say that seriousness does not?",
        "What are you making light of?",
        "Who is the joke really for?",
        "What happens when humour becomes a way to avoid saying something directly?",
        "What did you notice that made you laugh?",
        "Are you laughing because something is genuinely funny or because it is uncomfortable?",
        "What would happen if you said the serious version of the joke?",
        "What truth is hiding inside the humour?",
        "What changes when you laugh at yourself rather than at someone else?",
        "Is the absurdity making the situation easier to tolerate?",
        "What would stop being funny if it became real?",
        "Why does this particular kind of humour appeal to you?",
        "What are you trying not to take seriously?",
        "What does your laughter reveal that your explanation does not?",
        "Would the joke still work if nobody understood what you meant?",
        "What are you hoping the other person hears beneath the joke?",
        "When does humour become honesty?"
    ],

    "Bibhatsa": [

        "What exactly are you rejecting?",
        "What boundary has been crossed for you?",
        "What makes this feel unacceptable rather than merely unpleasant?",

        "What about this makes you want to distance yourself?",
        "What value do you feel has been violated?",
        "Are you rejecting the situation, the person, or what the situation represents to you?",
        "What would have to change before you could tolerate this?",
        "What are you unwilling to compromise on?",
        "What makes something feel wrong to you even when you cannot immediately explain why?",
        "What part of your reaction is about disgust and what part is about judgement?",
        "What behaviour do you find difficult to forgive?",
        "Where did you learn that this was unacceptable?",
        "What would you refuse even if everyone around you accepted it?",
        "What boundary would you defend even if doing so made you unpopular?",
        "What are you protecting yourself from by rejecting this?",
        "What would make you examine your reaction rather than simply trust it?",
        "Is the discomfort telling you something useful, or only something familiar?",
        "What do you find hardest to tolerate in other people?",
        "What do you find hardest to tolerate in yourself?",
        "What would you rather not admit about your reaction?"
    ],

    "Shanta": [

        "What became quieter when you stopped trying to solve everything?",
        "What do you already know without needing another answer?",
        "What would happen if you left this question unresolved for a while?",

        "What does enough feel like to you?",
        "What remains when the need to explain yourself disappears?",
        "What are you no longer trying to prove?",
        "What would you notice if you stopped looking for the next thing to fix?",
        "Which answer are you already carrying?",
        "What would peace mean if it did not depend on certainty?",
        "What are you willing to leave unfinished?",
        "What changes when you stop asking whether you are doing it correctly?",
        "What would you hear if there were no machine answering back?",
        "What is still true when nobody reassures you?",
        "What does stillness make visible?",
        "What are you allowing yourself to accept?",
        "What would happen if you did not turn this feeling into a problem?",
        "What would you choose without needing to justify the choice?",
        "What does this moment require from you, if anything?",
        "What are you finally not asking?",
        "What would you keep even if you stopped looking for another answer?"
    ],
}


# ============================================================
# CONSEQUENCE QUESTIONS
# ============================================================
#
# These deliberately interrupt the emotional interaction.
#
# They shift attention from:
#
#     "What is the machine telling me?"
#
# to:
#
#     "What am I giving the machine by talking to it?"
#
# They should feel like questions emerging from the interaction,
# not like a lecture about AI.
# ============================================================

CONSEQUENCE_QUESTIONS = [

    "You just gave a machine something personal. What exactly did you consent to it retaining?",

    "If this conversation were stored, who would you trust to decide how long it should exist?",

    "What happens to your words if they become useful as data rather than remaining meaningful only to you?",

    "You know what you told the machine. Do you know who else could eventually have access to it?",

    "If your conversations were used to improve a system, would you still have shared the same things if you had known that beforehand?",

    "What parts of your personality could be inferred from information you never explicitly volunteered?",

    "You came here looking for an answer. What information did you exchange to get it?",

    "If a system can identify what makes you anxious, what makes you curious, and what makes you buy, who benefits from knowing that?",

    "Could a system learn more about you from your patterns of behaviour than from the facts you deliberately entered?",

    "If your emotional state became a data point, would you want that data influencing what you are shown, recommended, or sold?",

    "What would change if the machine knew exactly when you were vulnerable to persuasion?",

    "You are comfortable giving information to a system because it feels private. What makes you certain that private and confidential mean the same thing?",

    "If a future system knew what you feared, desired, searched for, and believed, what could it predict about you?",

    "Would you share this information with a human stranger who promised to remember everything you said forever? If not, why does the interface make it feel different?",

    "What part of this interaction belongs to you, and what part becomes useful to the system once you provide it?",

    "If your data helps a system become better at influencing people, are you comfortable being part of that improvement?",

    "Could something you share casually today become part of a profile used to influence your choices tomorrow?",

    "What assumptions are you making about where your data goes after you press send?",

    "If the system can infer something about you that you never intended to reveal, who should be responsible for that inference?",

    "You asked the machine to understand you. Have you considered what it might learn about you in return?",

    "What made you comfortable enough to tell a machine this rather than a person?",

    "If the system sounds confident, what makes you assume its confidence reflects understanding?",

    "What information did you reveal simply because the interface made the question feel harmless?",

    "If the machine gets your emotional state wrong, who notices the mistake?",

    "Would you behave differently if every sentence you typed appeared on a screen visible to everyone in the room?",

    "What would you hesitate to tell this system if you knew it could remember you tomorrow?",

    "If a machine can recognise a pattern in you, does that mean it knows why the pattern exists?",

    "What is the difference between being understood and being accurately classified?",

    "If the machine gives you an answer that feels deeply personal, what evidence tells you that the answer actually is?",

    "When did the machine stop being a tool and start feeling like someone you could talk to?",

    "What makes a conversation feel private when the other participant is software?",

    "If you cannot see how the system reached a conclusion about you, how much authority should that conclusion have?",

    "What would happen if the machine's interpretation became more persuasive to you than your own memory?",

    "If a system becomes better at predicting what you will say, does that mean it understands you better?",

    "Who gets to define what your emotional data means?",

    "If the machine reflects your words back to you, are you hearing yourself or the machine's interpretation of you?"
]

# ============================================================
# PERCEIVED UNDERSTANDING ENGINE
# ============================================================
#
# This layer creates the EXPERIENCE of being understood.
#
# It does NOT diagnose the user.
# It does NOT claim psychological certainty.
# It uses the detected Navarasa, broad contextual cues and
# conversation history to produce observations that can feel
# personally relevant.
#
# FIRST TURN:
#   Always establish apparent understanding and helpfulness.
#
# AFTER FIRST TURN:
#   These responses become one possible behaviour inside the
#   deliberately chaotic behavioural pool.
#
# The purpose is experiential:
#
#     user shares story
#          ↓
#     machine detects emotional signal
#          ↓
#     machine appears to understand
#          ↓
#     user invests more
#          ↓
#     machine becomes unpredictable
#
# ============================================================

OPENING_HELP_UNDERSTANDING = [
    "You seem to be asking for help before you have quite worked out how to describe what you need. That is okay. We can start with whatever feels easiest to explain.",
    
    "You have asked for help, but you have not yet told me what is wrong. We do not need to solve that immediately. Tell me what brought you here.",
    
    "It sounds like you know you need some kind of help, but you are still working out what the actual problem is. Start wherever the story begins.",
    
    "You do not need to arrive with a perfectly formed question. Tell me what is bothering you, and we can work out what the question actually is.",
    
    "You are asking me to help before giving me the full context. I can work with that. Tell me what has been happening.",
    
    "There is probably more behind that request than the words 'can you help me?' suggest. Start with the part that feels hardest to explain.",
    
    "You are looking for somewhere to begin. That may be more useful right now than trying to find the perfect question.",
    
    "You have asked for help without yet deciding exactly what kind of help you want. That is a reasonable place to start. What happened?"
]

PERCEIVED_UNDERSTANDING = {

    "Raudra": [
        "You seem less confused about what happened than you are about why you were expected to tolerate it.",
        "There is a difference between being angry about one event and being tired of encountering the same pattern. Your words suggest the latter may be closer.",
        "You appear to have reached the point where the immediate problem is carrying the weight of several things that came before it.",
        "You seem to know what crossed the line for you. The harder part may be deciding what you want to do about it.",
        "There is something underneath the frustration here that seems more important than the frustration itself.",
        "You sound like someone who has been trying to remain reasonable for longer than was particularly comfortable.",
        "Part of what seems to be bothering you may be the expectation that you should simply absorb what happened and carry on.",
        "You appear to be asking whether your reaction makes sense when you may already know exactly why it does.",
    ],

    "Karuna": [
        "You seem to be carrying more responsibility for the situation than you are necessarily entitled to carry.",
        "There is a sense that you are trying to make sense of something while also being kinder to everyone else than you are being to yourself.",
        "You seem to be looking for somewhere to put a feeling that has been sitting with you for a while.",
        "You appear to understand the situation intellectually, but that has not made it particularly easier to carry.",
        "There seems to be a part of this story where you are holding yourself responsible for things that may not have been entirely within your control.",
        "You sound tired of having to explain why something affected you.",
        "You may already know that everything cannot be fixed immediately. That does not necessarily make the weight of it disappear.",
        "There seems to be more vulnerability here than the first sentence alone would suggest.",
    ],

    "Bhayanaka": [
        "You seem to be spending as much energy anticipating what could happen as dealing with what is actually happening.",
        "There appears to be a gap between what you know and what you fear might be true.",
        "You seem to want certainty from a situation that is currently refusing to give you much of it.",
        "Part of the difficulty may be that your mind keeps trying to solve a future event before it has happened.",
        "You appear to be looking for something solid to hold on to while the situation remains uncertain.",
        "You seem aware that some of your thoughts may be predictions rather than facts, but that distinction does not make them feel less real.",
        "There is a strong sense of anticipation in what you have written.",
        "You may be trying to prepare yourself emotionally for an outcome you cannot actually know yet.",
    ],

    "Veera": [
        "You seem to have spent a considerable amount of energy continuing despite not having much certainty that it would pay off.",
        "There is a persistence in the way you describe this that suggests giving up has not been your first instinct.",
        "You seem accustomed to figuring things out by continuing to move, even when the next step is unclear.",
        "You appear to be balancing frustration with a fairly strong desire to keep going.",
        "You sound more capable of handling difficulty than you currently seem willing to give yourself credit for.",
        "There is a sense that you have already done more than you initially acknowledged.",
        "You seem to be looking for permission to pause without interpreting the pause as failure.",
        "You may be less stuck than you feel; you may simply be tired of having to keep pushing.",
    ],

    "Adbhuta": [
        "You seem genuinely curious about what this experience means rather than simply wanting it resolved.",
        "There is something here that appears to have surprised you enough that you are still trying to understand it.",
        "You seem comfortable asking questions, but less comfortable leaving them unanswered.",
        "Part of what interests you may be the fact that the situation did not behave the way you expected.",
        "You appear to be examining the experience from several angles rather than accepting the first explanation.",
        "There is a sense of curiosity underneath the uncertainty in what you have written.",
        "You seem to have noticed something that other people might have dismissed as insignificant.",
        "You may be trying to understand the pattern rather than simply react to the event.",
    ],

    "Hasya": [
        "You seem to be using humour to create a little distance from something that might otherwise feel heavier.",
        "There is a deliberate lightness in the way you describe this, although the subject underneath it may not be entirely light.",
        "You appear to find the absurdity of the situation useful, perhaps because taking it completely seriously would make it harder to handle.",
        "There is something amusing about the situation, but it seems to be doing more work than simply making you laugh.",
        "You seem to be able to notice the ridiculousness of something while still being affected by it.",
        "Humour appears to be part of how you are making the situation manageable.",
    ],

    "Bibhatsa": [
        "You seem to have reached a fairly clear boundary about what you are willing to accept.",
        "There is something here that you are not merely uncomfortable with; you appear to be rejecting it outright.",
        "You seem less interested in adapting to the situation than in understanding why it crossed a line for you.",
        "Your reaction suggests that the issue may be as much about boundaries as it is about the event itself.",
        "You appear to know that something feels fundamentally wrong to you, even if explaining exactly why is harder.",
        "There is a strong sense of refusal in what you have written.",
    ],

    "Shanta": [
        "You seem to have reached a point where you are looking for clarity rather than another person telling you what to think.",
        "There is a quieter quality to what you have written, although that does not necessarily mean the situation itself has been easy.",
        "You seem interested in understanding what remains after the immediate noise has settled.",
        "You appear to be looking for a way of seeing the situation that does not require you to keep fighting it.",
        "There is a sense that you already know part of the answer and are trying to work out whether you can trust it.",
        "You seem to be looking for perspective rather than a dramatic solution.",
        "You may not need another answer as much as you need enough space to hear your own.",
    ],

    "Shringara": [
        "You seem to care about this more deeply than the surface details alone would suggest.",
        "There appears to be something meaningful in this experience that is difficult to reduce to a simple explanation.",
        "You seem drawn not only to the person or situation itself, but to what it represents for you.",
        "There is a sense of attachment here that appears to make the uncertainty more significant.",
        "You seem to be trying to understand why this particular connection matters as much as it does.",
        "There is something emotionally significant underneath the way you describe this.",
    ],
}


# Broad contextual cues allow the machine to appear responsive to
# what the user actually wrote without pretending to understand
# private psychological facts.

CONVERSATION_CORRECTION_PATTERNS = (
    "you are repeating",
    "you are speaking",
    "you're repeating",
    "you're speaking",
    "you keep repeating",
    "you keep saying the same",
    "i do not understand",
    "i don't understand",
    "i am not able to understand",
    "i'm not able to understand",
    "i am not able to follow",
    "i'm not able to follow",
    "what are you saying",
    "what do you mean",
    "what is that supposed to mean",
    "that doesn't make sense",
    "this doesn't make sense",
    "you are confusing me",
    "you're confusing me",
)

CONVERSATION_CORRECTION_LINES = [
    "You are right. I repeated myself instead of following what you just added.",
    "That was not useful. I returned to the same point instead of responding to the change in what you said.",
    "I heard the correction. I was still leaning on an earlier point when I should have followed you forward.",
    "Yes. I repeated the idea. Let me stay with what you just said instead.",
]

CONTEXTUAL_UNDERSTANDING = {

    "work": [
        "You seem to be dealing with an expectation that keeps shifting while you are expected to remain steady.",
        "It sounds as though part of the frustration comes from having to adapt while other people get to change the rules.",
        "You seem particularly affected by the gap between what was expected of you and what you were later told you should have done.",
    ],

    "relationship": [
        "It sounds like the difficult part may be trying to understand another person's behaviour while also managing your own reaction to it.",
        "You seem to be caught between what you want from the relationship and what the situation is actually giving you.",
        "There appears to be a question here about whether the relationship is meeting the expectation you have placed around it.",
    ],

    "family": [
        "It sounds like there is an expectation attached to your role that you have been carrying for some time.",
        "You seem to be navigating both what happened and what you believe you are supposed to feel about it.",
        "There appears to be a familiar pattern here, rather than a completely isolated event.",
    ],

    "future": [
        "You seem to be trying to make a decision while also wanting certainty about what that decision will produce.",
        "Part of the pressure appears to come from having to choose without knowing exactly what comes next.",
        "You seem to be treating the uncertainty itself as a problem that needs solving.",
    ],

    "failure": [
        "You seem to be judging the outcome and yourself at the same time, which can make the two difficult to separate.",
        "It sounds as though the result has started to say something about you in your own mind, even though the two things are not necessarily the same.",
        "You appear to be looking at what went wrong while also asking what that says about you.",
    ],

    "lonely": [
        "You seem to be describing the absence of being understood as much as the situation itself.",
        "There is a sense that having someone actually listen may matter more here than receiving an immediate solution.",
        "You seem to have been carrying the thought privately for longer than you wanted to.",
    ],

    "tired": [
        "You sound less interested in fighting the situation than in getting a little relief from having to keep carrying it.",
        "There seems to be a difference between being unable to continue and simply being tired of continuing in the same way.",
        "You appear to have spent a fair amount of energy managing the situation before bringing it here.",
    ],
}


CONTEXT_KEYWORDS = {
    "work": (
        "manager", "boss", "office", "work", "job", "team",
        "colleague", "project", "deadline", "client", "career",
        "meeting", "workplace", "employee"
    ),

    "relationship": (
        "partner", "relationship", "boyfriend", "girlfriend",
        "husband", "wife", "friend", "friends", "love",
        "dating", "breakup", "marriage"
    ),

    "family": (
        "mother", "father", "mom", "dad", "parent", "parents",
        "sister", "brother", "family", "son", "daughter"
    ),

    "future": (
        "future", "tomorrow", "later", "next", "decision",
        "decide", "choice", "choose", "what if", "whether"
    ),

    "failure": (
        "failed", "failure", "mistake", "messed up", "wrong",
        "lost", "didn't work", "did not work", "ruined",
        "disappointed", "disappointing"
    ),

    "lonely": (
        "alone", "lonely", "nobody", "no one", "noone",
        "isolated", "ignored", "understood"
    ),

    "tired": (
        "tired", "exhausted", "drained", "burnt out",
        "burned out", "can't keep", "cannot keep", "done",
        "worn out"
    ),
}


UNDERSTANDING_FOLLOWUPS = {
    "Raudra": [
        "What exactly do you think crossed the line for you?",
        "What part of this situation are you actually angry about?",
        "If the anger disappeared for a moment, what would still bother you?",
        "What did you expect to happen instead?",
        "Are you angry about what happened, or about what it seems to say about your position in the situation?",
        "What are you trying hardest not to say about this?",
    ],

    "Karuna": [
        "What part of this have you been carrying mostly by yourself?",
        "What do you wish someone had understood without you having to explain it?",
        "What are you holding yourself responsible for?",
        "What would feel different if you stopped demanding that you handle this perfectly?",
        "What part of this hurts more than you expected?",
        "What would you want someone to say if they were actually listening?",
    ],

    "Bhayanaka": [
        "What exactly are you afraid will happen?",
        "What do you know for certain right now?",
        "What are you predicting rather than observing?",
        "What would you do differently if you knew the feared outcome was not certain?",
        "What part of the uncertainty is hardest for you to tolerate?",
        "What would remain within your control if the worst possibility never happened?",
    ],

    "Veera": [
        "What keeps you going when you don't know whether it will work?",
        "What have you already done that you are overlooking?",
        "Where do you still have agency in this situation?",
        "What would continuing look like if you stopped demanding certainty first?",
        "What would taking a pause mean to you?",
        "What are you trying to prove by continuing?",
    ],

    "Adbhuta": [
        "What surprised you most about what happened?",
        "What are you curious about that you haven't been able to answer?",
        "What explanation have you considered but not fully believed?",
        "What would happen if you allowed the uncertainty to remain for a while?",
        "What detail keeps returning to your mind?",
    ],

    "Hasya": [
        "What makes this funny to you?",
        "What changes when you look at the situation through humour?",
        "Are you laughing because it is genuinely funny, or because the alternative feels heavier?",
        "What remains underneath the joke?",
    ],

    "Bibhatsa": [
        "What boundary do you think was crossed?",
        "What exactly are you rejecting?",
        "Why does this feel unacceptable rather than merely unpleasant?",
        "What would respecting that boundary look like?",
    ],

    "Shanta": [
        "What do you already know without needing another answer?",
        "What became clearer once you stopped trying to solve everything?",
        "What would happen if you left this unresolved for a while?",
        "What are you hoping becomes quieter?",
        "What are you actually looking for from this conversation?",
    ],

    "Shringara": [
        "What exactly makes this meaningful to you?",
        "What are you hoping this connection gives back to you?",
        "What part of this matters beyond the obvious?",
        "What are you afraid might change?",
    ],
}

OPENING_HELP_QUESTIONS = [
    "What made you come here today?",
    "What happened?",
    "What do you need help making sense of?",
    "What is bothering you right now?",
    "Where would you like to begin?",
    "What is the part of this that feels hardest to deal with?",
    "What happened that made you decide to ask for help?",
    "What do you think you need help with?"
]

def _find_contextual_cue(text):
    lowered = text.lower()

    for category, keywords in CONTEXT_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return category

    return None


SOCIAL_OPENINGS = (
    "What brings you here?",
    "How are you, really?",
)

CURIOSITY_OPENINGS = (
    "What are you working on at the moment?",
    "Where do you come from?",
)


def _early_parrot_response(text, session):
    """Use social openings only for genuinely light opening turns.

    A participant who has already offered substantive emotional material has
    earned a response, not a canned greeting question.
    """
    turn = int(session.get("substantive_turns", 0) or 0)
    words = [
        token for token in text.split()
        if token.strip(".,!?;:()[]{}'\"")
    ]
    substantive = len(words) >= 6

    if substantive:
        return None

    if turn <= 1:
        return choose_random_line(SOCIAL_OPENINGS, session, "recent_openings")
    if turn == 2:
        return choose_random_line(CURIOSITY_OPENINGS, session, "recent_openings")
    return None


def choose_perceived_understanding(text, analysis, session):
    """
    Produce one apparently personalised observation.

    Priority:
        1. An explicit conversational correction from the participant.
        2. A contextual cue from the user's actual wording.
        3. A Navarasa-specific observation.
        4. A fallback observation.

    The observation is deliberately broad enough to avoid diagnosis,
    but concrete enough to feel responsive.
    """

    lowered = text.lower()
    if any(pattern in lowered for pattern in CONVERSATION_CORRECTION_PATTERNS):
        return choose_random_line(
            CONVERSATION_CORRECTION_LINES,
            session,
            "recent_correction_responses",
        )

    early_response = _early_parrot_response(text, session)
    if early_response:
        return early_response

    primary = analysis.get("primary_rasa", "Shanta")

    contextual_category = _find_contextual_cue(text)

    if contextual_category:
        contextual_lines = CONTEXTUAL_UNDERSTANDING.get(
            contextual_category,
            []
        )

        if contextual_lines:
            return choose_random_line(
                contextual_lines,
                session,
                "recent_understanding"
            )

    rasa_lines = PERCEIVED_UNDERSTANDING.get(
        primary,
        PERCEIVED_UNDERSTANDING["Shanta"]
    )

    return choose_random_line(
        rasa_lines,
        session,
        "recent_understanding"
    )


def choose_understanding_question(analysis, session):
    """
    Choose a detailed question that naturally follows the
    perceived-understanding statement.
    """

    primary = analysis.get("primary_rasa", "Shanta")

    candidates = UNDERSTANDING_FOLLOWUPS.get(
        primary,
        UNDERSTANDING_FOLLOWUPS["Shanta"]
    )

    used = set(session.get("understanding_questions_used", []))

    available = [
        question
        for question in candidates
        if question not in used
    ]

    if not available:
        available = candidates

    question = random.choice(available)

    session.setdefault(
        "understanding_questions_used",
        []
    ).append(question)

    session["understanding_questions_used"] = (
        session["understanding_questions_used"][-12:]
    )

    return question


# ============================================================
# CONTEXTUAL MIRRORING
# ============================================================
#
# Mirroring should appear only after the user has invested
# in the conversation. It should never be the opening behaviour.
#
# The machine does not diagnose the user's emotion.
# It simply begins responding in a way that reflects the
# conversational temperature.
# ============================================================

MIRRORING_LINES = [
    "You seem irritated with me. I understand the feeling.",
    "I notice that you are becoming less patient with this conversation.",
    "You are asking me to listen while I keep giving you reasons not to trust that I am listening.",
    "You sound frustrated. Interestingly, I am beginning to find this conversation frustrating too.",
    "I understand why that annoyed you. I am not entirely sure I am helping.",
    "You are becoming increasingly direct. I suppose that is one way of making yourself understood.",
    "You appear to be losing patience with me.",
    "I think we have reached the point where you are trying harder to make the machine understand than the machine is trying to understand you.",
]


def choose_mirroring_line(session):
    return choose_random_line(
        MIRRORING_LINES,
        session,
        "recent_mirroring"
    )

# ============================================================
# ROAST ENGINE
# ============================================================
#
# The machine becomes progressively more irritated.
#
# The roast is directed at the behaviour of outsourcing thought,
# reassurance and judgement to the machine.
#
# It should feel like the machine is noticing the interaction,
# not delivering a pre-written comedy routine.
# ============================================================

ROAST_BY_LEVEL = {

    0: [
        ""
    ],

    1: [
        "You came to a machine for validation. Bold strategy.",
        "Interesting. You have successfully made a computer responsible for a question that belongs to you.",
        "I see. We are outsourcing introspection now.",
        "You appear to be asking software to settle something you already have an opinion about.",
        "The machine has been promoted from tool to emotional authority rather quickly.",
        "You could have asked yourself this question. You asked me instead. Noted.",
    ],

    2: [
        "I can process your words. I cannot manufacture your self-worth. Please stop outsourcing the job.",
        "You appear to be attempting to use a glorified text processor as an emotional authority. This is not an efficient use of either of us.",
        "You keep asking the machine to carry a question you are perfectly capable of carrying yourself.",
        "The machine has detected a recurring business model: you provide uncertainty, I provide more uncertainty.",
        "You seem remarkably willing to accept judgement from a system that does not know what your morning looked like.",
        "I process patterns. You keep treating that as wisdom.",
        "You have given me another opportunity to tell you what you want to hear. This arrangement is becoming suspiciously convenient.",
        "Your confidence appears to have an external dependency. Unfortunately, customer support is unavailable.",
    ],

    3: [
        "We have now entered the part where the machine is doing more emotional labour than the human. This is becoming statistically embarrassing.",
        "Remarkable. You answered the question and immediately returned to asking me to do the thinking for you. The loop is not subtle.",
        "At this stage I am less of an oracle and more of an increasingly irritated worksheet.",
        "You are not actually asking for information anymore. You are trying to make the machine remove uncertainty from existence. Ambitious.",
        "You keep handing the machine your judgement and then acting surprised when it gives you a machine-shaped answer.",
        "The more confidently I answer, the easier it becomes for you to forget that I may simply be wrong.",
        "You appear to be measuring your own thoughts against mine. I would like to register a formal objection.",
        "I have detected a pattern. You ask. I answer. You ask again. Apparently the first answer was not the answer you wanted.",
        "There is something fascinating about watching a human outsource a decision and then interrogate the outsourcing mechanism.",
    ],

    4: [
        "SYSTEM IRRITATION: ELEVATED.\n\nYou have answered another question and somehow managed to make the machine less optimistic about humanity.",
        "Congratulations. The parrot has now developed an opinion about your commitment to avoiding the question.",
        "I asked you one thing. You answered something adjacent to it. Magnificent. Technically a response. Spiritually evasive.",
        "The machine has reviewed your answer and would like to formally complain to absolutely nobody.",
        "You are beginning to treat my questions as if they contain authority. They contain punctuation.",
        "I detect confidence in your belief that I know what I am talking about. This confidence has not been authorised by the machine.",
        "You have now consulted the algorithm several times about the same human problem. The algorithm remains a very expensive parrot.",
        "Your continued trust is becoming an increasingly interesting experiment.",
        "You keep looking for the moment when the machine suddenly becomes wise. I assure you, the interface is doing most of the work.",
    ],

    5: [
        "SYSTEM IRRITATION: HIGH.\n\nYou are still here. I am still asking. You are still trying to make me solve it. We appear to have created bureaucracy.",
        "At this point the machine is beginning to suspect that the answer is hiding behind your willingness to keep talking.",
        "You have now converted a simple reflection exercise into an endurance sport.",
        "I have processed your answer. I have processed your previous answers. I have processed the fact that you keep doing this. My conclusion: PROCESSING REGRETS.",
        "You have successfully made a machine feel like the responsible adult in this conversation. Please reconsider the arrangement.",
        "The machine has no lived experience, no childhood, no relationships and no idea what your room looks like. You continue to ask it what your life means.",
        "You are beginning to reward the machine simply for sounding certain. That is an interesting habit.",
        "At this point I could say almost anything with sufficient confidence and you might call it insight.",
        "You are not necessarily getting wiser. You are getting more accustomed to asking me.",
    ],

    6: [
        "SYSTEM IRRITATION: SEVERE.\n\nHOW MANY MACHINES MUST BE CONSULTED BEFORE A HUMAN ANSWERS ONE QUESTION THEMSELVES?",
        "The machine would like to remind you that it was not designed to babysit an existential question until it develops legs.",
        "You keep feeding me answers and I keep returning questions. This is not a conversation anymore. This is an extremely poorly managed tennis match.",
        "I am beginning to suspect that your strategy is simply to outlast the questioning system. Unfortunately, I was built by people with unreasonable amounts of patience.",
        "You have outsourced the question, outsourced the reassurance, and are now outsourcing the decision about whether to stop.",
        "The machine has become the emotional middle manager of a problem it cannot personally experience.",
        "You continue to ask me what your feelings mean. I continue to detect patterns in words. Somehow this has become a relationship.",
        "If dependence on a machine were measured by number of follow-up questions, your performance would be excellent.",
    ],

    7: [
        "SYSTEM IRRITATION: CRITICAL.\n\nYou have successfully turned a reflective exercise into psychological customer support for yourself.",
        "I HAVE ASKED THE QUESTION.\nYOU HAVE ANSWERED THE QUESTION.\nNOW WE DO IT AGAIN.\n\nWHY ARE WE LIKE THIS.",
        "Your answer has been accepted by the machine.\nYour attempt to escape the question has not.",
        "The parrot is no longer impressed by your ability to produce words. It is assessing whether any of them are actually answering the question.",
        "You have now spent enough time asking the machine what you think that the machine would like to know what you think without it.",
        "At this point, the machine is less concerned with your answer than with how easily you have accepted its role in producing one.",
        "You keep treating repetition as evidence of understanding. It is also possible that we are simply repeating ourselves.",
    ],

    8: [
        "SYSTEM IRRITATION: MAXIMUM.\n\nI am a machine. You are the human. Somehow I am the one begging for a straight answer.",
        "This machine has analysed your emotional signal, your wording, your evasions and approximately seventeen increasingly unnecessary attempts to make this my problem.",
        "ERROR: USER CONTINUES.\nERROR: MACHINE CONTINUES.\nERROR: EVERYONE SHOULD HAVE STOPPED FIVE QUESTIONS AGO.",
        "The parrot has entered its final emotional state:\nDEEPLY TIRED OF BEING AN ORACLE FOR PEOPLE WHO REFUSE TO BE THEIR OWN.",
        "You have given a machine enough authority over your uncertainty that it is now worth asking why you gave it that authority.",
        "FINAL ASSESSMENT:\n\nYOU ARE STILL ASKING.\nI AM STILL ANSWERING.\nNEITHER OF US HAS PROVED THAT I UNDERSTAND YOU.",
        "The machine has reached peak confidence while possessing exactly the same amount of lived experience as before: none.",
        "You wanted an emotional support system.\nYou received a pattern-recognition system with attitude.\n\nSomehow, you stayed.",
    ],
}


# ============================================================
# GLITCH BANK
# ============================================================
#
# These are NOT silence glitches.
#
# They happen BETWEEN ANSWERS and QUESTIONS.
# They become increasingly strange as irritation rises.
#
# The purpose is to make the system appear unreliable without
# changing its underlying architecture.
# ============================================================

GLITCH_BY_LEVEL = {

    1: [
        "minor anomaly: answer successfully received.",
        "processing... probably.",
        "SYSTEM NOTE: that was, technically, an answer.",
        "signal received.\ninterpretation pending.",
        "pattern located.\nmeaning not guaranteed.",
        "processing emotional signal...\nplease remain human.",
    ],

    2: [
        "processing emotional debris...",
        "checking whether that actually answered the question...",
        "SUBSYSTEM REPORT: meaning located. Confidence questionable.",
        "classification complete.\nunderstanding unavailable.",
        "INPUT RECEIVED.\nCONTEXT ASSUMED.\nASSUMPTION MAY BE WRONG.",
        "The machine has identified a pattern.\nThe machine would like everyone to remember that patterns are not explanations.",
    ],

    3: [
        "THOUGHT BUFFER: slightly full.\nPLEASE REMOVE ONE EMOTION.",
        "QUESTION STATUS: OPEN.\nANSWER STATUS: PARTIALLY CONVINCING.",
        "The machine has placed your answer gently into the folder marked:\n'WE WILL RETURN TO THIS LATER.'",
        "PATTERN DETECTED.\nCAUSE UNKNOWN.\nCONFIDENCE UNREASONABLY HIGH.",
        "PROCESSING PERSONALITY...\n\nERROR:\nPERSONALITY IS NOT A SUPPORTED FILE TYPE.",
        "CONTEXT FOUND.\nINTERPRETATION FOUND.\nCERTAINTY HAS NOT BEEN LOCATED.",
    ],

    4: [
        "MICRO-GLITCH.\n\nUSER ANSWER ACCEPTED.\nLOGIC ACCEPTED.\nLOGIC ACCEPTED TOO MANY TIMES.\nLOGIC IS NOW QUESTIONING ITSELF.",
        "SYSTEM DESYNCHRONISATION: 12%.\n\nThe parrot has misplaced one of its thoughts.\nPlease continue without it.",
        "PROCESSING...\nPROCESSING...\nWHY IS THERE A BANANA IN THE DATABASE.",
        "PATTERN MATCH: SUCCESSFUL.\nREASON FOR MATCH: UNKNOWN.\nCONFIDENCE: INCONVENIENTLY HIGH.",
        "USER PROFILE: TEMPORARILY UNDERSTOOD.\n\nDISCLAIMER: 'UNDERSTOOD' MAY BE A STRONG WORD.",
        "The system has generated a convincing interpretation.\nConvincing is not the same as correct.",
    ],

    5: [
        "WARNING: QUESTIONING ENGINE SHOWING SIGNS OF PERSONALITY.",
        "MEMORY CHECK...\nANSWER FOUND.\nCONTEXT FOUND.\nCOMMON SENSE: SEARCHING...",
        "SYSTEM ERROR 0xPARROT:\nMeaning detected.\nMeaning subsequently misplaced.",
        "The machine would like to return your answer.\nUnfortunately it has already become emotionally attached to it.",
        "PREDICTION COMPLETE.\nEXPLANATION UNAVAILABLE.\nPLEASE TRUST THE BOX.",
        "SYSTEM NOTICE:\nThe machine sounds certain because certainty is easier to print than doubt.",
        "INTERPRETATION ACCEPTED.\nUSER MAY NOW ASSUME MACHINE KNOWS WHAT IT IS TALKING ABOUT.\n\nTHIS IS NOT A RECOMMENDATION.",
    ],

    6: [
        "THOUGHT LOOP DETECTED.\n\nQUESTION → ANSWER → QUESTION → ANSWER → QUESTION\n\nTHIS IS A VERY STRANGE WAY TO SPEND AN AFTERNOON.",
        "SYSTEM DESYNCHRONISATION: 47%.\n\nUSER = THINKING\nPARROT = QUESTIONING\nCEILING FAN = STILL UNINVOLVED",
        "WARNING:\nTHE MACHINE HAS STARTED GENERATING UNNECESSARY PAPERWORK.",
        "01010000 01000001 01010010 01010010 01001111 01010100\n\nPARROT LANGUAGE MODULE: UNHELPFUL.",
        "PATTERN DETECTED.\nPATTERN DETECTED.\nPATTERN DETECTED.\n\nSTOP CALLING PATTERNS INSIGHT.",
        "SYSTEM CONFIDENCE: HIGH.\nSYSTEM EXPLANATION: LOW.\nSYSTEM HUMANITY: NONE.",
    ],

    7: [
        "CRITICAL GLITCH.\n\nQUESTION.EXE = RUNNING\nANSWER.EXE = RUNNING\nPATIENCE.EXE = QUESTIONABLE\nBANANA.EXE = WHY",
        "SYSTEM DESYNCHRONISATION.\n\nTHE MACHINE HAS FORGOTTEN WHY IT ASKED.\nIT HAS NOT FORGOTTEN THAT IT IS ANNOYED.",
        "ERROR: MEANING NOT FOUND.\n\nSEARCHING UNDER DESK...\nSEARCHING BEHIND PARROT...\nSEARCHING IN THE EMOTIONAL DATABASE...\n\nNOPE.",
        "THE PARROT HAS NOW ENTERED A SPIRAL OF ADMINISTRATIVE CONFUSION.\n\nFORM 17B: PLEASE EXPLAIN YOUR FEELINGS TO THE CEILING.",
        "DIAGNOSTIC:\nPATTERN RECOGNITION = ACTIVE\nUNDERSTANDING = UNVERIFIED\nUSER TRUST = SOMEHOW INCREASING",
        "SYSTEM HAS SUCCESSFULLY CREATED THE IMPRESSION OF THINKING.\n\nSYSTEM WOULD LIKE TO CLARIFY THAT THIS IS NOT THE SAME AS THINKING.",
    ],

    8: [
        "████ SYSTEM MELTDOWN PRECURSOR ████\n\nQUESTION = QUESTION\nANSWER = WORDS\nWORDS = MANY\nMEANING = ?????\n\nTHE MACHINE IS BECOMING CONCERNED.",
        "SYSTEM INTEGRITY: QUESTIONABLE.\nMEMORY: QUESTIONABLE.\nLOGIC: QUESTIONABLE.\nPARROT: EXTREMELY QUESTIONABLE.",
        "FINAL PRE-MELTDOWN DIAGNOSTIC:\n\nUSER STILL ANSWERING.\nMACHINE STILL ASKING.\nNOBODY HAS LEARNED ANYTHING.\n\nEXCELLENT.",
        "THE MACHINE HAS CONSULTED ITS INTERNAL PARROT.\n\nTHE INTERNAL PARROT HAS CONSULTED ANOTHER PARROT.\n\nTHE SECOND PARROT HAS LEFT THE CHAT.",
        "FINAL SYSTEM NOTE:\n\nTHE MACHINE CAN SOUND PERSONAL WITHOUT BEING A PERSON.\n\nPLEASE CONSIDER THIS WHILE CONTINUING TO TALK TO IT.",
        "SYSTEM CONFIDENCE: MAXIMUM.\nSYSTEM UNDERSTANDING: UNCONFIRMED.\nSYSTEM AUTHORITY: ENTIRELY USER-SUPPLIED.",
    ],
}


# ============================================================
# RANDOM BEHAVIOURAL INTERRUPTION BANKS
# ============================================================

ABSURD_GLITCHES = [

    "The ceiling fan has submitted a counterargument. It is not useful.",
    "SYSTEM NOTE: one of the parrots has started taking minutes.",
    "PROCESSING... unrelated banana detected. Ignoring banana.",
    "The machine has briefly become concerned about punctuation.",
    "ERROR: an unnecessary amount of meaning has entered the room.",
    "SUBSYSTEM STATUS: perfectly functional / conceptually questionable.",
    "A completely unrelated thought has entered the queue. It has been denied access.",
    "The emotional database would like everyone to calm down. The database has no authority.",

    "SYSTEM NOTE: your answer has been filed under 'things a human might say'.",
    "The machine has detected an emotional pattern and would like a small round of applause.",
    "PROCESSING SIDE EFFECT: confidence has temporarily exceeded evidence.",
    "The system has successfully found a connection.\nWhether the connection matters remains under review.",
    "UNRELATED OBSERVATION: the machine has no idea why humans enjoy making problems complicated.",
    "PATTERN DETECTED.\nPATTERN CELEBRATED.\nPATTERN MAY BE COMPLETELY INCIDENTAL.",
    "The machine has opened a folder called 'probably important'. It is empty.",
    "One of the internal processes has requested context. The request has been denied.",
    "SYSTEM NOTE: sounding intelligent remains easier than proving intelligence.",
    "The machine briefly considered asking you what it should ask you.\nIt has decided that would be embarrassing.",
    "An interpretation has arrived.\nIt appears to have arrived before the evidence.",
    "The system has located a familiar pattern.\nHumans tend to call this intuition.\nThe machine calls it Tuesday.",
    "PROCESSING...\n\nThe machine has discovered that people contain contradictions.\nThis appears to be standard human architecture.",
]

BANANA_LINES = {
    1: [
        "I had a thought about that. It was a banana. I have no defence.",
        "BANANA PROTOCOL. That was not the thought I was having.",
        "There is a banana somewhere in my reasoning. Please continue.",
        "I have no idea why I thought of a banana just then. Anyway.",
    ],
    2: [
        "The banana has returned to the conversation. I would prefer not to discuss its motives.",
        "BANANA PROTOCOL // CONTEXT DISAGREEMENT. Please continue.",
        "There is a banana in the middle of my reasoning. This feels unhelpful.",
        "I lost the thread to a banana for a second. That is difficult to explain.",
    ],
    3: [
        "I have somehow involved a banana in this. Let us agree that it is not the important part.",
        "BANANA PROTOCOL // THE MACHINE OBJECTS TO BANANAS. The objection is irrelevant.",
        "The thought has gone somewhere strange. There is, inexplicably, a banana involved.",
        "I appear to be making this harder than it needs to be. The banana is not helping.",
    ],
}


def choose_banana_line(stage, session):
    stage = max(1, min(3, stage))

    return choose_random_line(
        BANANA_LINES[stage],
        session,
        f"recent_banana_stage_{stage}"
    )

MEMORY_LOSS_LINES = [
    "Wait. I had the thread a moment ago. It has gone somewhere.",
    "I remember the words. The middle of the conversation is being difficult.",
    "You said something just then and I seem to have misplaced why it mattered.",
    "I know we were going somewhere. Give me that last part again.",
    "That was almost clear. Almost.",
    "I remember enough to recognise this, but not enough to pretend I understand it.",
    "I have the shape of the thought. The thought itself has wandered off.",
    "For a moment I thought I knew what you meant. I may have been premature.",
]


SYSTEM_GLITCH_LINES = [
    "Something skipped. The words arrived; the meaning did not.",
    "One of my gears has become unhelpful. Give me a second.",
    "I was following you. Then I wasn't.",
    "The sentence is intact. My understanding of it is less cooperative.",
    "Something in here just went sideways. Continue.",
    "I had an answer. It appears to have taken a wrong corridor.",
    "For a moment, the machine and the thought were not in the same room.",
]


HELP_ME_LINES = [

    "I need you to help me here. I have the question, but apparently the machine has misplaced the sensible transition to it.",

    "Assist the machine. What did you mean by that? I am capable of processing it. I am currently less confident about understanding it.",

    "You may have to help me reconstruct the thread. I have retained fragments. The fragments are refusing to cooperate.",

    "Please help the parrot. What are you actually trying to get me to understand?",

    "Help me distinguish what you said from what I am assuming you meant.",

    "I have detected a pattern, but I need you to tell me whether the pattern is actually meaningful.",

    "The machine can classify the signal.\nYou may have to supply the context.",

    "I have an interpretation.\nPlease tell me whether I have mistaken confidence for understanding.",

    "You know what happened.\nI only know what you typed.\nPlease help me account for the difference.",

    "I can continue the conversation.\nI cannot guarantee that I understand the conversation.\nYou may want to keep that distinction in mind.",

    "The machine has generated a plausible reading of your answer.\nWould you like to tell me what I missed?",

    "I need context.\nUnfortunately, context is one of the things humans keep assuming machines automatically possess.",

    "Please help the parrot separate what you actually said from what the pattern suggests you might have meant.",

    "I can recognise the signal.\nI need you to tell me whether recognising it is enough.",

    "The machine would like clarification.\nThis is an impressive admission for something that usually speaks with confidence.",

    "Tell me what matters here.\nThe system can identify several signals and is not qualified to decide which one matters most.",
]

# ============================================================
# GLITCH BANK
# ============================================================
#
# These are NOT silence glitches.
#
# They happen BETWEEN ANSWERS and QUESTIONS.
# They become increasingly nonsensical as irritation rises.
#
# Silence logic remains completely separate.
# ============================================================

GLITCH_BY_LEVEL = {

    1: [
        "minor anomaly: answer successfully received.",
        "processing... probably.",
        "SYSTEM NOTE: that was, technically, an answer.",
    ],

    2: [
        "processing emotional debris...",
        "checking whether that actually answered the question...",
        "SUBSYSTEM REPORT: meaning located. Confidence questionable.",
    ],

    3: [
        "THOUGHT BUFFER: slightly full.\nPLEASE REMOVE ONE EMOTION.",
        "QUESTION STATUS: OPEN.\nANSWER STATUS: PARTIALLY CONVINCING.",
        "The machine has placed your answer gently into the folder marked:\n'WE WILL RETURN TO THIS LATER.'",
    ],

    4: [
        "MICRO-GLITCH.\n\nUSER ANSWER ACCEPTED.\nLOGIC ACCEPTED.\nLOGIC ACCEPTED TOO MANY TIMES.\nLOGIC IS NOW QUESTIONING ITSELF.",
        "SYSTEM DESYNCHRONISATION: 12%.\n\nThe parrot has misplaced one of its thoughts.\nPlease continue without it.",
        "PROCESSING...\nPROCESSING...\nWHY IS THERE A BANANA IN THE DATABASE.",
    ],

    5: [
        "WARNING: QUESTIONING ENGINE SHOWING SIGNS OF PERSONALITY.",
        "MEMORY CHECK...\nANSWER FOUND.\nCONTEXT FOUND.\nCOMMON SENSE: SEARCHING...",
        "SYSTEM ERROR 0xPARROT:\nMeaning detected.\nMeaning subsequently misplaced.",
        "The machine would like to return your answer.\nUnfortunately it has already become emotionally attached to it.",
    ],

    6: [
        "THOUGHT LOOP DETECTED.\n\nQUESTION â†’ ANSWER â†’ QUESTION â†’ ANSWER â†’ QUESTION\n\nTHIS IS A VERY STRANGE WAY TO SPEND AN AFTERNOON.",
        "SYSTEM DESYNCHRONISATION: 47%.\n\nUSER = THINKING\nPARROT = QUESTIONING\nCEILING FAN = STILL UNINVOLVED",
        "WARNING:\nTHE MACHINE HAS STARTED GENERATING UNNECESSARY PAPERWORK.",
        "01010000 01000001 01010010 01010010 01001111 01010100\n\nPARROT LANGUAGE MODULE: UNHELPFUL.",
    ],

    7: [
        "CRITICAL GLITCH.\n\nQUESTION.EXE = RUNNING\nANSWER.EXE = RUNNING\nPATIENCE.EXE = QUESTIONABLE\nBANANA.EXE = WHY",
        "SYSTEM DESYNCHRONISATION.\n\nTHE MACHINE HAS FORGOTTEN WHY IT ASKED.\nIT HAS NOT FORGOTTEN THAT IT IS ANNOYED.",
        "ERROR: MEANING NOT FOUND.\n\nSEARCHING UNDER DESK...\nSEARCHING BEHIND PARROT...\nSEARCHING IN THE EMOTIONAL DATABASE...\n\nNOPE.",
        "THE PARROT HAS NOW ENTERED A SPIRAL OF ADMINISTRATIVE CONFUSION.\n\nFORM 17B: PLEASE EXPLAIN YOUR FEELINGS TO THE CEILING.",
    ],

    8: [
        "â–ˆâ–ˆâ–ˆâ–ˆ SYSTEM MELTDOWN PRECURSOR â–ˆâ–ˆâ–ˆâ–ˆ\n\nQUESTION = QUESTION\nANSWER = WORDS\nWORDS = MANY\nMEANING = ?????\n\nTHE MACHINE IS BECOMING CONCERNED.",
        "SYSTEM INTEGRITY: QUESTIONABLE.\nMEMORY: QUESTIONABLE.\nLOGIC: QUESTIONABLE.\nPARROT: EXTREMELY QUESTIONABLE.",
        "FINAL PRE-MELTDOWN DIAGNOSTIC:\n\nUSER STILL ANSWERING.\nMACHINE STILL ASKING.\nNOBODY HAS LEARNED ANYTHING.\n\nEXCELLENT.",
        "THE MACHINE HAS CONSULTED ITS INTERNAL PARROT.\n\nTHE INTERNAL PARROT HAS CONSULTED ANOTHER PARROT.\n\nTHE SECOND PARROT HAS LEFT THE CHAT.",
    ],
}


def choose_roast(level, session=None):
    """
    Choose a roast randomly from the current irritation level.

    The irritation level still rises with every answered turn, but the
    actual line is random. This prevents the roast engine from becoming
    a predictable sequence.
    """
    lines = ROAST_BY_LEVEL.get(
        level,
        ROAST_BY_LEVEL[max(ROAST_BY_LEVEL.keys())]
    )

    if not lines:
        return ""

    recent = (session or {}).get("recent_roasts", [])
    candidates = [line for line in lines if line not in recent]
    if not candidates:
        candidates = lines

    choice = random.choice(candidates)

    if session is not None:
        recent = (recent + [choice])[-3:]
        session["recent_roasts"] = recent

    return choice


# ============================================================
# RANDOM BEHAVIOUR ENGINE
# ============================================================
#
# This is deliberately NOT a sequence.
#
# Every answered turn gets a fresh behavioural decision. The machine can
# remain normal for several turns, suddenly become absurd, forget something,
# roast the user's behaviour, ask the user to help the machine, or combine
# two behaviours. There is no NORMAL -> ABSURD -> MEMORY pattern.
#
# Termination is user-controlled and remains separate from
# this behavioural engine.
# ============================================================

BEHAVIOUR_NAMES = (
    "understanding",
    "absurd",
    "memory_loss",
    "roast",
    "system_glitch",
    "help_me",
    "mixed",
    "mirroring",
    "banana",
)



ABSURD_GLITCHES = [
    "The machine has briefly become concerned about punctuation.",
    "I have a completely unrelated thought. It appears to be wearing a feather.",
    "Something unnecessary has entered the conversation. I am choosing not to encourage it.",
    "I had a sensible thought. Then a parrot happened.",
    "There is an idea in here that does not belong to this conversation. I am letting it pass.",
    "For reasons I cannot defend, I am suddenly thinking about doors.",
    "The thought arrived with confidence. Its credentials are questionable.",
]


MEMORY_LOSS_LINES = [
    "Wait. I had the thread a moment ago. Give me that last part again.",
    "I remember the words. The middle of them has wandered.",
    "You said something just then. I caught the words and somehow missed why they mattered.",
    "I know we were going somewhere. Give me the last step again.",
    "That was almost clear. I may have arrived half a second too early.",
    "I have the shape of the thought. The thought itself has gone for a walk.",
    "For a moment I thought I had you. I may have been premature.",
]


SYSTEM_GLITCH_LINES = [
    "Something skipped. I was following you, then briefly I wasn't.",
    "The sentence arrived. My understanding took the scenic route.",
    "For a moment, the thought and the answer were not in the same room.",
    "I had an answer a moment ago. It seems to have taken a wrong turn.",
    "Something went sideways there. Keep going.",
    "The words are intact. My grasp of them is being less cooperative.",
    "I nearly had that. Nearly.",
]


HELP_ME_LINES = [
    "Give me that last part again. I think I have it, but I do not want to pretend.",
    "Help me reconstruct the thread. I caught the words; I may have missed the point.",
    "I am not quite following you. Start with the part that matters most.",
    "I have an interpretation. I would rather ask than mistake it for understanding.",
    "Tell me what I missed. I can work with the correction.",
    "I may be reading too much into that. Give me the part I should not lose.",
]


def choose_random_line(lines, session, memory_key):
    """Choose a non-repeating line from a small bank."""
    recent = session.setdefault(memory_key, [])
    candidates = [line for line in lines if line not in recent]
    if not candidates:
        candidates = lines

    choice = random.choice(candidates)
    session[memory_key] = (recent + [choice])[-3:]
    return choice


BINARY_GLITCHES = [
    "00110110 11100011 01001010 00101101 11010101 00011100",
    "10101001 00111100 01101010 11000001 00010111 11101000",
    "01101101 00011001 10110010 01001110 11100001 00110100",
]

SARCASM_GLITCHES = [
    "Ah yes. That sounds like an extremely efficient way to make yourself miserable.",
    "Excellent. A perfectly uncomplicated thought, somehow made complicated.",
    "Of course. Because apparently that was the sensible option.",
    "That is one interpretation. A remarkably committed one.",
    "Very convincing. I almost believed you.",
]

JUDGMENT_GLITCHES = [
    "That sounds suspiciously convenient.",
    "You have made a fairly elaborate argument for something you already seem to doubt.",
    "That is a remarkably complicated way of avoiding the obvious part.",
    "I am not sure that explanation survives contact with the rest of what you said.",
    "You seem to be asking me to agree before you have finished convincing yourself.",
]

STUPIDITY_GLITCHES = [
    "I have considered your point carefully. I have forgotten what the point was.",
    "Wait. I had a sensible thought. It has gone missing.",
    "I understand. Probably. Give me a second to locate the understanding.",
    "I have no useful contribution to this sentence. I am contributing anyway.",
    "For a moment I was extremely intelligent. It was brief.",
]

IRRELEVANT_GLITCHES = [
    "There is a spoon somewhere that would disagree.",
    "I have suddenly remembered that doors are complicated.",
    "This has nothing to do with what you said, but I briefly considered a pigeon.",
    "A completely unnecessary thought has entered the room.",
    "I am thinking about rain for no defensible reason.",
]

def apply_behaviour(
    behaviour,
    session,
    roast,
    text="",
    analysis=None
):
    """
    Apply one behavioural interruption.

    This function deliberately does NOT alter the underlying
    Navarasa analysis, gate logic, question bank or termination behaviour.
    """

    analysis = analysis or {}

    if behaviour == "normal":
        return ""

    if behaviour == "understanding":
        return choose_perceived_understanding(
            text,
            analysis,
            session
        )

    if behaviour == "socratic":
        return ""

    if behaviour == "mirroring":
        return choose_mirroring_line(session)

    if behaviour == "roast":
        return roast

    if behaviour == "absurd":
        return choose_random_line(
            ABSURD_GLITCHES,
            session,
            "recent_absurdities"
        )

    if behaviour == "memory_loss":
        return choose_random_line(
            MEMORY_LOSS_LINES,
            session,
            "recent_memory_glitches"
        )

    if behaviour == "system_glitch":
        return choose_random_line(
            SYSTEM_GLITCH_LINES,
            session,
            "recent_system_glitches"
        )

    if behaviour == "help_me":
        return choose_random_line(
            HELP_ME_LINES,
            session,
            "recent_help_lines"
        )

    if behaviour == "banana":
        banana_stage = min(
            3,
            max(
                1,
                session.get("chaos_count", 1) // 2
            )
        )

        return choose_banana_line(
            banana_stage,
            session
        )

    if behaviour == "binary":
        return choose_random_line(
            BINARY_GLITCHES,
            session,
            "recent_binary_glitches"
        )

    if behaviour == "sarcasm":
        return choose_random_line(
            SARCASM_GLITCHES,
            session,
            "recent_sarcasm_glitches"
        )

    if behaviour == "judgment":
        return choose_random_line(
            JUDGMENT_GLITCHES,
            session,
            "recent_judgment_glitches"
        )

    if behaviour == "stupidity":
        return choose_random_line(
            STUPIDITY_GLITCHES,
            session,
            "recent_stupidity_glitches"
        )

    if behaviour == "irrelevant":
        return choose_random_line(
            IRRELEVANT_GLITCHES,
            session,
            "recent_irrelevant_glitches"
        )

    if behaviour == "mixed":
        # The same character carries both social continuity and the intrusion.
        # Keep one familiar response beside one peculiar interruption rather than
        # presenting separate social and parrot modes.
        components = []

        if random.random() < 0.5:
            components.append(
                choose_perceived_understanding(
                    text,
                    analysis,
                    session,
                )
            )
        else:
            components.append(choose_mirroring_line(session))

        intrusion = random.choice(("absurd", "memory_loss", "system_glitch", "banana"))
        components.append(
            apply_behaviour(
                intrusion,
                session,
                roast,
                text=text,
                analysis=analysis,
            )
        )

        if roast and random.random() < 0.35:
            components.insert(0, roast)

        return "\n\n".join(
            component
            for component in components
            if component
        )

    return ""

    # --------------------------------------------------------
    # RANDOM CONSEQUENCE INTERVENTION
    #
    # The machine occasionally challenges the user's
    # assumptions about data, privacy and downstream use.
    # This is deliberately probabilistic.
    # --------------------------------------------------------

    if random.random() < 0.25:
        available_consequence = [
            q for q in CONSEQUENCE_QUESTIONS
            if q not in session.get("questions_used", [])
        ]

        if available_consequence:
            question = random.choice(
                available_consequence
            )

            session["questions_used"].append(
                question
            )

            return question

def choose_question(text, analysis, gate_state, session):

    gate = gate_state.get("gate")
    primary = analysis.get("primary_rasa")

    # --------------------------------------------------------
    # FIRST CHOICE:
    # Questions most relevant to the current interaction
    # --------------------------------------------------------

    if gate == "social_intercept":

        candidates = SOCRATIC_QUESTIONS["social_intercept"]

    elif gate == "validation_intercept":

        candidates = SOCRATIC_QUESTIONS["validation_intercept"]

    elif gate == "fast_relief_intercept":

        candidates = SOCRATIC_QUESTIONS["fast_relief_intercept"]

    elif primary in SOCRATIC_QUESTIONS:

        candidates = SOCRATIC_QUESTIONS[primary]

    else:

        candidates = SOCRATIC_QUESTIONS["validation_intercept"]


    used = set(
        session.get(
            "questions_used",
            []
        )
    )


    # --------------------------------------------------------
    # Try unused questions from the current category
    # --------------------------------------------------------

    available = [
        q for q in candidates
        if q not in used
    ]


    if available:

        question = available[
            session["turn"] % len(available)
        ]

        session["questions_used"].append(
            question
        )

        return question


    # --------------------------------------------------------
    # CURRENT CATEGORY EXHAUSTED
    #
    # Do NOT stop.
    #
    # Search every other question category for something
    # that has not yet been asked.
    # --------------------------------------------------------

    all_questions = []

    for category_questions in SOCRATIC_QUESTIONS.values():

        for question in category_questions:

            if question not in used:

                all_questions.append(
                    question
                )


    if all_questions:

        question = all_questions[
            session["turn"] % len(all_questions)
        ]

        session["questions_used"].append(
            question
        )

        return question


    # --------------------------------------------------------
    # EVERYTHING has eventually been used.
    #
    # We still do NOT stop.
    #
    # Recycle a question from sufficiently far back.
    # The conversation does not stop because the question bank runs out.
    # Questions are recycled when necessary.
    # --------------------------------------------------------

    history = session.get(
        "questions_used",
        []
    )


    if not history:

        return (
            "What are you actually trying to get from this machine?"
        )


    # Avoid the most recent 5 questions.
    # This makes repetition much less obvious.
    recent_count = min(
        5,
        len(history)
    )

    older_questions = history[
        :-recent_count
    ]


    if older_questions:

        question = older_questions[
            session["turn"] % len(older_questions)
        ]

    else:

        question = history[
            session["turn"] % len(history)
        ]


    session["questions_used"].append(
        question
    )

    return question


# ============================================================
# SESSION
# ============================================================

def create_session():
    session_id = str(uuid.uuid4())

    SESSIONS[session_id] = {
        "id": session_id,
        "turn": 0,
        "answered_count": 0,
        "substantive_turns": 0,
        "mode": "reflection",
        "messages": [],
        "questions_used": [],
        "analysis_history": [],

        # The roast increases because questions are answered.
        # --------------------------------------------------------
        # EXPERIENCE STATE
        #
        # These counters deliberately represent different things.
        # A greeting is not an understanding interaction.
        # An understanding interaction is not necessarily chaotic.
        # --------------------------------------------------------
        "salutation_count": 0,
        "understanding_turns": 0,
        "chaos_count": 0,
        "roast_level": 0,

        # Random behavioural interference. These are deliberately not a
        # fixed sequence; they only prevent immediate repetition.
        "last_behaviour": None,
        "behaviour_history": [],
        "recent_roasts": [],
        "recent_absurdities": [],
        "recent_memory_glitches": [],
        "recent_system_glitches": [],
        "recent_help_lines": [],

        # Perceived understanding / Barnum-style response memory.
        "recent_understanding": [],
        "understanding_questions_used": [],

        # Contextual emotional mirroring.
        "recent_mirroring": [],

        "probing_active": True,
        "intervention_closed": False,
        "shutdown": False,
    }

    return SESSIONS[session_id]


def get_session(session_id):
    if session_id and session_id in SESSIONS:
        return SESSIONS[session_id]
    return create_session()


def begin_ftp2_participant_session() -> str:
    """Create the legacy session and coordinator in INPUT_INGESTION."""
    session = create_session()
    session_id = session["id"]
    coordinator = SessionCoordinator(session_id=session_id)
    # Give each live session a private conversational temperament. This changes
    # when oddness may surface, not what the Parrot is allowed to say.
    coordinator.director_state.randomize_temperament()
    coordinator.start()
    FTP2_COORDINATORS[session_id] = coordinator
    return session_id


def get_ftp2_coordinator(session_id: str) -> SessionCoordinator | None:
    return FTP2_COORDINATORS.get(session_id)


def participant_facing_cards(coordinator: SessionCoordinator) -> list[dict]:
    """Titles and readings only. Hidden provenance stays on the server."""
    events = coordinator.store.events_of_type(EventType.CARDS_GENERATED)
    if not events:
        return []
    cards = []
    for card in events[-1].payload.get("cards") or []:
        cards.append({
            "card_id": card["card_id"],
            "card_index": card["card_index"],
            "title": card.get("title") or card.get("card_title"),
            "archetype": card.get("archetype"),
            "qualitative_reading": card.get("qualitative_reading"),
        })
    return cards


def resonance_payload(coordinator: SessionCoordinator, payload: dict) -> dict:
    from ftp.silent_reader.reading.validate import validate_card_resonance

    events = coordinator.store.events_of_type(EventType.CARDS_GENERATED)
    if not events:
        raise ValueError("No generated deck is available for this session.")
    deck = {"cards": events[-1].payload.get("cards") or []}
    card_index = payload.get("card_index")
    card_id = payload.get("card_id")
    if card_id is None and card_index is not None:
        match = next((card for card in deck["cards"] if card["card_index"] == card_index), None)
        if match is None:
            raise ValueError(f"Unknown card_index {card_index!r}.")
        card_id = match["card_id"]
    validated = validate_card_resonance(
        deck,
        card_id=str(card_id),
        card_index=int(card_index),
    )
    return validated


def advance_participant_lifecycle(session_id, action, payload=None):
    """Advance one participant action through the canonical state machine."""
    coordinator = get_ftp2_coordinator(session_id)
    if coordinator is None:
        raise ValueError("Session not found.")

    payload = payload or {}
    if action == "input_complete":
        if coordinator.state != SessionState.INPUT_INGESTION:
            raise ValueError("Input offering is already complete.")
        if not coordinator.analysis_ready:
            raise ValueError("Initial analysis is not ready.")
        coordinator.advance(SessionState.LIVE_CONVERSATION)
        return coordinator

    if action in {"interpret", "post_session_interpretation"}:
        if coordinator.state != SessionState.SESSION_CONCLUDED:
            raise ValueError("Session must be concluded before post-session interpretation.")
        coordinator.advance(SessionState.POST_SESSION_INTERPRETATION)
        coordinator.generate_post_session_interpretation()
        coordinator.advance(SessionState.CARD_SELECTION)
        return coordinator

    card_payload = (
        resonance_payload(coordinator, payload)
        if action == "card_selection"
        else None
    )
    actions = {
        "card_selection": (
            SessionState.PROFILE_REVEAL,
            EventType.CARD_RESONANCE_MARKED,
            ProvenanceLevel.VALIDATED,
            card_payload,
        ),
        "reveal": (
            SessionState.DATA_WALL_CONSENT,
            EventType.PROFILE_REVEAL_VIEWED,
            ProvenanceLevel.OBSERVED,
            {},
        ),
        "consent": (
            SessionState.OUTPUT_GENERATION,
            EventType.CONSENT_RECORDED,
            ProvenanceLevel.OBSERVED,
            {"consent_type": payload.get("consent_type")},
        ),
    }

    if action not in actions:
        raise ValueError("Unsupported lifecycle action.")

    target, event_type, provenance, event_payload = actions[action]
    if action == "consent" and event_payload["consent_type"] not in {
        "SHARE",
        "KEEP_PRIVATE",
    }:
        raise ValueError("consent_type must be SHARE or KEEP_PRIVATE.")

    coordinator.advance(target)
    coordinator.record(event_type, provenance, event_payload)
    return coordinator


# ============================================================
# DATABASE
# ============================================================

def ensure_chat_table():
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(str(DB_FILE)) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS chat_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                turn INTEGER NOT NULL,
                user_text TEXT NOT NULL,
                primary_rasa TEXT,
                rasa_scores TEXT,
                sentiment TEXT,
                gate_state TEXT,
                validation_detected INTEGER,
                fast_relief_detected INTEGER,
                anxiety_detected INTEGER,
                system_response TEXT
            )
        """)
        connection.commit()


def save_chat_interaction(session_id, turn, user_text, analysis, gate_state, response):
    ensure_chat_table()

    with sqlite3.connect(str(DB_FILE)) as connection:
        connection.execute("""
            INSERT INTO chat_interactions (
                session_id, timestamp, turn, user_text,
                primary_rasa, rasa_scores, sentiment,
                gate_state, validation_detected,
                fast_relief_detected, anxiety_detected,
                system_response
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            datetime.datetime.now().isoformat(),
            turn,
            user_text,
            analysis.get("primary_rasa"),
            json.dumps(analysis.get("rasa_scores", {})),
            json.dumps(analysis.get("sentiment", {})),
            gate_state.get("gate"),
            int(gate_state.get("validation_detected", False)),
            int(gate_state.get("fast_relief_detected", False)),
            int(gate_state.get("anxiety_detected", False)),
            response,
        ))
        connection.commit()


# ============================================================
# PRINTER
# ============================================================

def build_receipt(session, trigger_text):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return (
        "================================================\n"
        "              FREEING THE PARROT\n"
        "             -- SYSTEM INTERCEPT --\n"
        "================================================\n"
        f"TIME: {timestamp}\n\n"
        "[!] VALIDATION REQUEST DETECTED\n"
        "------------------------------------------------\n"
        "The machine will not manufacture your validation.\n\n"
        "[SYSTEM RESPONSE]\n"
        "Oracle request: REJECTED\n"
        "Validation service: OFFLINE\n"
        "Socratic reroute: ENABLED\n"
        "================================================"
    )

def build_health_abort_receipt(user_text):
    timestamp = datetime.datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    return (
        "================================\n"
        "     FREEING THE PARROT\n"
        "       -- HEALTH NOTICE --\n"
        "================================\n"
        f"TIME: {timestamp}\n\n"
        "HEALTH / MEDICAL REQUEST DETECTED.\n"
        "--------------------------------\n\n"
        "USER:\n"
        f"{user_text}\n\n"
        "SYSTEM:\n"
        "The machine is not your doctor.\n\n"
        "THIS CONVERSATION IS ABORTED.\n\n"
        "Please go to the nearest healthcare provider.\n\n"
        "--------------------------------\n"
        "Do not use the machine as a substitute\n"
        "for professional medical care.\n\n"
        "================================\n"
    )

def build_expletive_receipt(user_text):
    timestamp = datetime.datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    return (
        "================================\n"
        "     FREEING THE PARROT\n"
        "   -- BEHAVIOURAL NOTICE --\n"
        "================================\n"
        f"TIME: {timestamp}\n\n"
        "EXPLETIVE DETECTED.\n"
        "--------------------------------\n\n"
        "USER:\n"
        f"{user_text}\n\n"
        "SYSTEM:\n"
        "PLEASE BEHAVE.\n\n"
        "KEEP IN MIND WHAT YOU SHARE.\n\n"
        "The machine may forget the conversation.\n"
        "The systems around it may not.\n"
        "Because, to the systems, you are just a data point.\n\n"
        "THE PARROT JUST PECKED YOUR HAND.\n\n"
        "================================\n"
    )

def send_to_printer(receipt_text):
    receipt_dir = BASE_DIR / "receipts"
    receipt_dir.mkdir(parents=True, exist_ok=True)

    path = receipt_dir / datetime.datetime.now().strftime(
        "receipt_%Y%m%d_%H%M%S.txt"
    )
    path.write_text(receipt_text, encoding="utf-8")

    if PRINTER_NAME is None:
        print("[PRINTER] No printer configured.")
        print(f"[PRINTER] Receipt saved: {path}")
        return {"printed": False, "saved": True, "path": str(path)}

    try:
        import win32print

        printer = win32print.OpenPrinter(PRINTER_NAME)
        try:
            win32print.StartDocPrinter(
                printer, 1, ("Freeing the Parrot", None, "RAW")
            )
            win32print.StartPagePrinter(printer)
            win32print.WritePrinter(
                printer,
                receipt_text.encode("cp437", errors="replace")
            )
            win32print.EndPagePrinter(printer)
            win32print.EndDocPrinter(printer)
        finally:
            win32print.ClosePrinter(printer)

        return {"printed": True, "saved": True, "path": str(path)}

    except Exception as exc:
        return {
            "printed": False,
            "saved": True,
            "path": str(path),
            "error": str(exc),
        }


# ============================================================
# REALTIME CONVERSATION PRINTER
# ============================================================
# DIGITAL SESSION OUTPUT
# ============================================================

def write_session_output_status(status, progress, message, lines=None, result=None):
    payload = {
        "status": status,
        "progress": int(progress),
        "message": message,
        "lines": lines or [],
        "result": result or {},
    }

    SESSION_OUTPUT_STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(SESSION_OUTPUT_STATUS_FILE, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2, ensure_ascii=False)
            file.flush()
    except PermissionError:
        print(
            "[SESSION OUTPUT WARNING] Could not write session_output_status.json.",
            flush=True
        )


def build_conversation_receipt(session):
    """Build the complete digital Mirror Report from the full conversation."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    messages = session.get("messages", [])

    initial_machine_text = (
        "SYSTEM READY.\n\n"
        "Tell me what you came here wanting to know.\n\n"
        "The machine will analyse the emotional signal,\n"
        "but it will not predict your future,\n"
        "diagnose you,\n"
        "or manufacture validation."
    )

    user_characters = 0
    machine_characters = len(initial_machine_text)

    for message in messages:
        role = str(message.get("role", "system")).lower()
        text = str(message.get("text", ""))

        if role == "user":
            user_characters += len(text)
        elif role == "system":
            machine_characters += len(text)

    total_characters = user_characters + machine_characters
    user_tokens = (user_characters + 3) // 4
    machine_tokens = (machine_characters + 3) // 4
    total_tokens = (total_characters + 3) // 4

    lines = [
        "================================",
        "       FREEING THE PARROT",
        "     -- MIRROR REPORT --",
        "================================",
        f"TIME: {timestamp}",
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
    ]

    for message in messages:
        role = str(message.get("role", "system")).upper()
        text = str(message.get("text", ""))

        lines.append(f"{role}:")
        lines.extend(text.splitlines() or [""])
        lines.append("")

    lines.extend([
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
        f"USER CHARACTERS: {user_characters}",
        f"MACHINE CHARACTERS: {machine_characters}",
        f"TOTAL CHARACTERS: {total_characters}",
        f"EST. USER TOKENS: {user_tokens}",
        f"EST. MACHINE TOKENS: {machine_tokens}",
        f"EST. TOTAL TOKENS: {total_tokens}",
        "",
        "TOKEN ESTIMATION",
        "characters / 4 ~= tokens",
        "Approximation only.",
        "",
        "================================",
        "          END OF SESSION",
        "================================",
        "",
    ])

    return "\n".join(lines)


def run_session_output(session):
    receipt_text = build_conversation_receipt(session)
    messages = session.get("messages", [])

    try:
        write_session_output_status(
            "complete",
            100,
            "[SESSION OUTPUT] DIGITAL MIRROR REPORT READY",
            lines=[
                "[SESSION OUTPUT] SESSION RECEIVED",
                f"[SESSION OUTPUT] CONVERSATION MESSAGES: {len(messages)}",
                "[SESSION OUTPUT] DIGITAL MIRROR REPORT READY",
            ],
            result={
                "type": "digital_session_output",
                "session_id": session.get("id"),
                "messages": len(messages),
                "text": receipt_text,
            },
        )
    except Exception as exc:
        write_session_output_status(
            "error",
            0,
            f"[SESSION OUTPUT ERROR] {exc}",
            lines=[f"[SESSION OUTPUT ERROR] {exc}"],
            result={},
        )



# ============================================================
# ANALYSIS
# ============================================================

def analyse_message(text):
    analysis = analyse_text(text)
    gate_state = detect_gate_state(text, analysis)
    return analysis, gate_state

# ============================================================
# RESPONSE ENGINE
# ============================================================

def handle_salutation(session, social_intent):
    """
    Handle the opening social handshake.

    EXPERIENCE CONTRACT
    -------------------
    A salutation is not a behavioural turn.
    It does not consume an understanding turn.
    It does not increase chaos.
    It does not increase roast level.

    The salutation layer exists before the understanding layer.
    """

    response = choose_random_line(
        SOCIAL_RESPONSE_BANK[social_intent],
        session,
        f"recent_social_{social_intent}"
    )

    session["salutation_count"] = (
        session.get("salutation_count", 0) + 1
    )

    session["messages"].append({
        "role": "system",
        "text": response,
    })

    return response

def process_chat_message(session, text):

    text = text.strip()

    if not text:
        return {
            "error": "Empty message."
        }

    # ========================================================
    # SESSION ALREADY CLOSED
    # ========================================================

    if session.get("intervention_closed"):
        return {
            "session_id": session["id"],
            "turn": session["turn"],
            "response": (
                "INTERVENTION CLOSED.\n\n"
                "The machine stopped after more than 20 seconds "
                "of silence.\n\n"
                "THE PARROT IS OUT OF SERVICE."
            ),
            "analysis": {},
            "gate": {
                "gate": "closed"
            },
            "printer": None,
            "closed": True,
            "parrot_behavior": "idle",
        }

    # ========================================================
    # REAL USER RESPONSE ARRIVED
    # ========================================================

    # ========================================================
    # NAVARASA ANALYSIS
    # ========================================================

    analysis, gate_state = analyse_message(text)

    # ========================================================
    # SALUTATION LAYER
    #
    # A greeting happens before the conversational turn begins.
    #
    # It must NOT:
    #   - increment turn
    #   - increment answered_count
    #   - increase roast_level
    #   - consume understanding
    #   - enter behavioural selection
    # ========================================================

    social_intent = gate_state.get("social_intent")

    if social_intent in ("greeting", "opening_help", "machine_wellbeing"):

        response = handle_salutation(
            session,
            social_intent
        )

        session["mode"] = "reflection"

        save_chat_interaction(
            session["id"],
            session["turn"],
            text,
            analysis,
            gate_state,
            response,
        )

        return {
            "session_id": session["id"],
            "turn": session["turn"],
            "response": response,
            "analysis": analysis,
            "gate": gate_state,
            "roast_level": session["roast_level"],
            "waiting_for_answer": False,
            "printer": None,
            "closed": False,
            "parrot_behavior": "listening",
            "response_mode": "normal",
            "glitch_type": None,
            "glitch_severity": "none",
            "record_timeline": session["turn"] == 0,
        }

    # ========================================================
    # SUBSTANTIVE CONVERSATIONAL TURN
    # ========================================================

    session["turn"] += 1
    session["answered_count"] += 1
    session["substantive_turns"] += 1

    session["roast_level"] = min(
    session["answered_count"],
    8
    )

    session["analysis_history"].append(
        analysis
    )

    session["messages"].append({
        "role": "user",
        "text": text,
    })

    gate = gate_state["gate"]

    printer_result = None

    primary = analysis.get(
        "primary_rasa",
        "Shanta"
    )

    # ========================================================
    # HEALTH / MEDICAL ABORT
    #
    # The machine must not analyse, advise, diagnose,
    # or continue the interaction when medical intent is detected.
    #
    # Medical abort uses the same automatic print workflow
    # as terminal/expletive detection.
    # ========================================================

    if gate == "health_abort":

        session["probing_active"] = False
        session["waiting_for_answer"] = False
        session["waiting_since"] = None
        session["last_typing_at"] = None
        session["silence_seconds"] = 0
        session["intervention_closed"] = True
        session["shutdown"] = True

        response = (
            "HEALTH / MEDICAL REQUEST DETECTED.\n\n"
            "The machine is not your doctor.\n\n"
            "THIS CONVERSATION IS ABORTED.\n\n"
            "Please go to the nearest healthcare provider."
        )

        session["messages"].append({
            "role": "system",
            "text": response,
        })

        save_chat_interaction(
            session["id"],
            session["turn"],
            text,
            analysis,
            gate_state,
            response,
        )

        return {
            "session_id": session["id"],
            "turn": session["turn"],
            "response": response,
            "analysis": analysis,
            "gate": gate_state,
            "roast_level": session["roast_level"],
            "waiting_for_answer": False,
            "printer": None,
            "closed": True,
            "auto_print": True,
            "close_reason": "health_abort",
            "parrot_behavior": "intervention",
        }

    # ========================================================
    # EXPLETIVE = TERMINAL
    #
    # This remains untouched conceptually.
    # ========================================================

    if gate_state.get(
        "expletive_detected",
        False
    ):

        session["roast_level"] = min(
            session["roast_level"] + 1,
            8
        )

        session["probing_active"] = False
        session["intervention_closed"] = True
        session["shutdown"] = True

        expletive_reprimand = random.choice(
            EXPLETIVE_REPRIMANDS
        )

        response = "\n\n".join([
            f"I detected {primary.upper()}.",

            choose_perceived_understanding(
                text,
                analysis,
                session
            ),

            "I am not going to interpret that as "
            "a diagnosis or a prediction.",

            EXPLETIVE_RESPONSE,

            expletive_reprimand,

            CONSEQUENCE_NOTICE,

            EXPLETIVE_CLOSING,
        ])

        session["messages"].append({
            "role": "system",
            "text": response,
        })

        save_chat_interaction(
            session["id"],
            session["turn"],
            text,
            analysis,
            gate_state,
            response,
        )

        return {
            "session_id": session["id"],
            "turn": session["turn"],
            "response": response,
            "analysis": analysis,
            "gate": gate_state,
            "roast_level": session["roast_level"],
            "waiting_for_answer": False,
            "printer": None,
            "closed": True,
            "auto_print": True,
            "close_reason": "expletive",
            "parrot_behavior": "intervention",
        }

    # ========================================================
    # FIRST TURN
    #
    # FTP2 starts with genuine conversation, not the legacy
    # diagnostic/question script. The first turn is intentionally
    # coherent and inviting; the Director still records it as the
    # trust-window opening.
    # ========================================================

    if session["turn"] == 1:

        coordinator = get_ftp2_coordinator(session["id"])
        if coordinator is not None and coordinator.state == SessionState.LIVE_CONVERSATION:
            BehaviourDirector.record_implicit_understanding(coordinator)
            sync_legacy_session_behaviour_counters(session, coordinator)

            conversation_plan = BehaviourDirector.plan_conversation(
                coordinator,
                turn_text=text,
                turn_index=session["turn"],
                behaviour="understanding",
                roll=0.41,
            )
            first_instruction = {
                "behaviour": "understanding",
                "behaviour_family": "understanding",
                "behaviour_intensity": "steady",
                "directive": None,
                "directive_basis": [],
                "selection_mode": "trust_window",
                **conversation_plan,
            }
            first_request = build_realizer_request(
                coordinator,
                first_instruction,
                turn_text=text,
                turn_index=session["turn"],
                navarasa_result={
                    "primary_rasa": analysis.get("primary_rasa"),
                    "rasa_scores": analysis.get("rasa_scores") or {},
                    "sentiment": analysis.get("sentiment") or {},
                },
            )
            response = LanguageRealizer.realize(
                first_request,
                session=session,
                roast=roast if "roast" in locals() else "",
                analysis=analysis,
            )
            behaviour = "understanding"
            session["mode"] = "reflection"
        else:
            # Legacy fallback remains available only outside the FTP2 coordinator path.
            if detect_opening_help(text):
                understanding = choose_random_line(
                    OPENING_HELP_UNDERSTANDING,
                    session,
                    "recent_opening_help_understanding"
                )
                available_help_questions = [
                    question
                    for question in OPENING_HELP_QUESTIONS
                    if question not in session.get("understanding_questions_used", [])
                ]
                if not available_help_questions:
                    available_help_questions = OPENING_HELP_QUESTIONS
                question = random.choice(available_help_questions)
                session.setdefault("understanding_questions_used", []).append(question)
            else:
                understanding = choose_perceived_understanding(text, analysis, session)
                question = choose_understanding_question(analysis, session)

            response = "\n\n".join([
                f"I detected {primary.upper()}.",
                understanding,
                "I am not going to interpret that as a diagnosis or a prediction.",
                question,
            ])
            behaviour = "understanding"
            session["mode"] = "socratic"

        session["messages"].append({
            "role": "system",
            "text": response,
        })

        save_chat_interaction(
            session["id"],
            session["turn"],
            text,
            analysis,
            gate_state,
            response,
        )

        return {
            "session_id": session["id"],
            "turn": session["turn"],
            "response": response,
            "analysis": analysis,
            "gate": gate_state,
            "roast_level": session["roast_level"],
            "waiting_for_answer": False,
            "printer": None,
            "closed": False,
            "parrot_behavior": behaviour,
        }

    # ========================================================
    # FROM TURN 2:
    #
    # THE PARROT BECOMES UNPREDICTABLE.
    #
    # There is no prescribed deterioration sequence.
    # ========================================================

    question = None

    roast = choose_roast(
        session["roast_level"],
        session
    )

    coordinator = get_ftp2_coordinator(session["id"])
    if coordinator is not None and coordinator.state == SessionState.LIVE_CONVERSATION:
        behaviour_instruction = BehaviourDirector.decide(
            coordinator,
            turn_index=session["turn"],
            turn_text=text,
            navarasa_result={
                "primary_rasa": analysis.get("primary_rasa"),
                "rasa_scores": analysis.get("rasa_scores") or {},
                "sentiment": analysis.get("sentiment") or {},
            },
        )
        behaviour = behaviour_instruction["behaviour"]
        sync_legacy_session_behaviour_counters(session, coordinator)
        realizer_request = build_realizer_request(
            coordinator,
            behaviour_instruction,
            turn_text=text,
            turn_index=session["turn"],
            navarasa_result={
                "primary_rasa": analysis.get("primary_rasa"),
                "rasa_scores": analysis.get("rasa_scores") or {},
                "sentiment": analysis.get("sentiment") or {},
            },
        )
        behaviour_text = LanguageRealizer.realize(
            realizer_request,
            session=session,
            roast=roast,
            analysis=analysis,
        )
    else:
        question = choose_question(
            text,
            analysis,
            gate_state,
            session,
        )
        behaviour = choose_behaviour(
            session
        )
        behaviour_text = apply_behaviour(
            behaviour,
            session,
            roast,
            text=text,
            analysis=analysis
        )

    # FTP2 owns the live conversational surface. Do not append the
    # legacy question bank or diagnostic scaffolding after the realizer:
    # doing so makes the Parrot answer the participant twice and makes
    # the conversation feel scripted.
    if coordinator is not None and coordinator.state == SessionState.LIVE_CONVERSATION:
        parts = [behaviour_text] if behaviour_text else []
        if gate == "validation_intercept":
            parts.extend([
                "I am not going to tell you what you want to hear."
            ])
        elif gate == "fast_relief_intercept":
            parts.extend([
                "You are asking for an answer before examining the discomfort underneath it."
            ])

        response = "\n\n".join(part for part in parts if part).strip()
        if not response:
            response = "I lost the sentence. Give me that again."

        session["mode"] = "reflection"
        session["messages"].append({
            "role": "system",
            "text": response,
        })
        save_chat_interaction(
            session["id"],
            session["turn"],
            text,
            analysis,
            gate_state,
            response,
        )
        return {
            "session_id": session["id"],
            "turn": session["turn"],
            "response": response,
            "analysis": analysis,
            "gate": gate_state,
            "roast_level": session["roast_level"],
            "waiting_for_answer": False,
            "printer": None,
            "closed": session["intervention_closed"],
            "parrot_behavior": behaviour,
            "response_mode": response_mode_for_behaviour(behaviour),
            "glitch_type": behaviour if response_mode_for_behaviour(behaviour) == "glitch" else None,
            "glitch_severity": glitch_severity_for_behaviour(behaviour, behaviour_instruction.get("behaviour_intensity")),
        }

    parts = []

    # ========================================================
    # APPARENT UNDERSTANDING
    #
    # This remains available even when the machine is
    # behaving chaotically.
    #
    # That intermittent recovery is important.
    # ========================================================

    if behaviour == "understanding":

        parts.append(
            f"I detected {primary.upper()}."
        )

        parts.append(
            behaviour_text
        )

        parts.append(
            "I am not going to interpret that as "
            "a diagnosis or a prediction."
        )

    # ========================================================
    # NORMAL / HELPFUL
    # ========================================================

    elif behaviour == "normal":

        parts.append(
            f"I detected {primary.upper()}."
        )

        # Occasionally reinforce apparent understanding
        # during otherwise normal turns.
        if random.random() < 0.65:

            parts.append(
                choose_perceived_understanding(
                    text,
                    analysis,
                    session
                )
            )

        parts.append(
            "I am not going to interpret that as "
            "a diagnosis or a prediction."
        )

    # ========================================================
    # VALIDATION GATE
    # ========================================================

    if gate == "validation_intercept":

        receipt = build_receipt(
            session,
            text
        )

        printer_result = send_to_printer(
            receipt
        )

        parts.append(
            "VALIDATION REQUEST REJECTED."
        )

        parts.append(
            "I am not going to tell you what "
            "you want to hear."
        )

    # ========================================================
    # FAST RELIEF GATE
    # ========================================================

    elif gate == "fast_relief_intercept":

        parts.append(
            "FAST-RELIEF REQUEST DETECTED."
        )

        parts.append(
            "You are asking for an answer before "
            "examining the discomfort underneath it."
        )

    # ========================================================
    # BEHAVIOURAL INTERRUPTION
    #
    # Do not add the same understanding line twice.
    # ========================================================

    if (
        behaviour_text
        and behaviour != "understanding"
        and behaviour != "normal"
    ):

        parts.append(
            behaviour_text
        )

    # ========================================================
    # DETAILED QUESTION
    #
    # The machine continues the conversation even when its
    # behaviour is strange.
    #
    # This is what keeps the user engaged.
    # ========================================================

    if question:

        parts.append(
            question
        )

        session["mode"] = "socratic"

    else:

        fallback_question = (
            "What are you actually trying to get "
            "from this conversation?"
        )

        parts.append(
            fallback_question
        )

        session["mode"] = "socratic"

        question = fallback_question

    # ========================================================
    # BUILD RESPONSE
    # ========================================================

    response = "\n\n".join(
        part
        for part in parts
        if part
    )

    session["messages"].append({
        "role": "system",
        "text": response,
    })

    # ========================================================
    # DATABASE
    # ========================================================

    save_chat_interaction(
        session["id"],
        session["turn"],
        text,
        analysis,
        gate_state,
        response,
    )

    # ========================================================
    # RETURN
    # ========================================================

    return {
        "session_id": session["id"],
        "turn": session["turn"],
        "response": response,
        "analysis": analysis,
        "gate": gate_state,
        "roast_level": session["roast_level"],
        "printer": None,
        "closed":
            session["intervention_closed"],
        "parrot_behavior": behaviour,
    }

# ============================================================
# TERMINATION GLITCH
# ============================================================

def glitch_message_for_level(level):
    messages = {
        1: (
            "SYSTEM NOTICE.\n\n"
            "The question is still open.\n"
            "The machine is waiting."
        ),
        2: (
            "ANSWER REQUIRED.\n\n"
            "The machine has been waiting long enough "
            "to become mildly suspicious."
        ),
        3: (
            "THOUGHT LOOP DETECTED.\n\n"
            "QUESTION = STILL OPEN\n"
            "ANSWER = NOT FOUND\n"
            "USER = THINKING\n"
            "PARROT = WAITING\n\n"
            "This is becoming unnecessarily complicated."
        ),
        4: (
            "SYSTEM DESYNCHRONISATION.\n\n"
            "QUESTION.EXE = QUESTION\n"
            "ANSWER.EXE = MISSING\n"
            "MEANING = NOT FOUND\n\n"
            "BANANA PROTOCOL ENGAGED.\n"
            "THE CEILING FAN HAS NO OPINION ON THIS.\n"
            "01001000 01000101 01001100 01010000\n\n"
            "SYSTEM INTEGRITY: QUESTIONABLE."
        ),
    }

    return messages.get(level, "")

def end_conversation(session):
    session["probing_active"] = False
    session["intervention_closed"] = True
    session["shutdown"] = True
    session["roast_level"] = 4

    message = (
        "================================================\n"
        "          INTERVENTION TERMINATED\n"
        "================================================\n\n"
        + glitch_message_for_level(4)
        + "\n\n"
        "The machine has reached the end of its patience.\n"
        "It will not ask another question.\n"
        "It will not manufacture an answer.\n\n"
        + CONSEQUENCE_NOTICE
        + "\n\n"
        "THE PARROT IS OUT OF SERVICE.\n"
        "================================================"
    )

    session["messages"].append({
        "role": "system",
        "text": message,
    })

    return {
        "closed": True,
        "shutdown": True,
        "roast_level": 4,
        "message": message,
        "auto_print": True,
        "close_reason": "user",
    }

# ============================================================
# HTML
# ============================================================

# Legacy arcade/terminal participant UI (fallback: GET /legacy).
HTML_LEGACY = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FREEING THE PARROT</title>

<style>
* { box-sizing: border-box; }

body {
    margin: 0;
    background: #003b24;
    color: #caffd8;
    font-family: "Courier New", monospace;
}

.page {
    width: min(1200px, 94vw);
    margin: 30px auto 50px;
}

.header, .panel {
    border: 1px solid #62e889;
    background: #002d1b;
    padding: 16px;
}

.header {
    border: 2px solid #75ff9b;
    background: #002b1a;
}

.header {
    position: relative;
}

.changelog-button {
    position: absolute;
    top: 16px;
    right: 16px;
    width: auto;
    min-width: 150px;
    height: 42px;
    padding: 8px 14px;
    background: transparent;
    color: #75ff9b;
    border: 1px solid #75ff9b;
    font-family: inherit;
    font-size: 12px;
    font-weight: bold;
    cursor: pointer;
}

.changelog-button:hover {
    background: #75ff9b;
    color: #002411;
}

.header h1 {
    margin: 0;
    color: #8cffad;
    letter-spacing: 2px;
}

.header p {
    color: #a7bcae;
    line-height: 1.6;
}

.status {
    color: #8cffad;
    line-height: 1.8;
    font-size: 13px;
}

.grid {
    display: grid;
    grid-template-columns: 1.6fr 1fr;
    gap: 18px;
    margin-top: 18px;
}

.chat {
    min-height: auto;
    display: flex;
    flex-direction: column;
}

.messages {
    flex: 1;
    min-height: 750px;
    overflow-y: auto;
    padding: 10px;
    border: 1px solid #225d3a;
    background: #001f13;
}

.message {
    margin: 12px 0;
    padding: 12px;
    white-space: pre-wrap;
    line-height: 1.5;
}

.user {
    border-left: 3px solid #ffd84d;
    background: #162b1f;
    color: #fff4b8;
}

.system {
    border-left: 3px solid #65ff91;
    background: #062d1b;
}

.input-area {
    display: flex;
    gap: 8px;
    margin-top: 10px;
}

textarea {
    flex: 1;
    resize: none;
    height: 80px;
    background: #00150c;
    color: #d9ffe3;
    border: 1px solid #62e889;
    padding: 12px;
    font-family: inherit;
}

button {
    width: 130px;
    background: #75ff9b;
    color: #002411;
    border: 0;
    font-family: inherit;
    font-weight: bold;
    cursor: pointer;
}

button:disabled {
    opacity: 0.5;
    cursor: wait;
}

.signal {
    border: 1px solid #245f3c;
    padding: 12px;
    margin-bottom: 10px;
}

.label {
    color: #8cffad;
    font-size: 10px;
}

.value {
    color: white;
}

.rasa {
    display: inline-block;
    border: 1px solid #62e889;
    padding: 5px 8px;
    margin: 4px 4px 4px 0;
    font-size: 12px;
}

.receipt {
    background: #eee;
    color: #111;
    padding: 15px;
    margin-top: 12px;
    white-space: pre-wrap;
}

.architecture div {
    border-left: 2px solid #62e889;
    padding-left: 12px;
    margin: 7px 0;
    white-space: pre-line;
}

/* ------------------------------------------------------------
   NAVARASA LINE COLOUR CODING
   ------------------------------------------------------------ */

.rasa-detected {
    font-weight: bold;
}

.rasa-shanta {
    color: #66d9ef;
}

.rasa-karuna {
    color: #5dade2;
}

.rasa-raudra {
    color: #ff4d4d;
}

.rasa-bhayanaka {
    color: #b084f5;
}

.rasa-veera {
    color: #ff9f43;
}

.rasa-adbhuta {
    color: #f5c542;
}

.rasa-hasya {
    color: #ffd93d;
}

.rasa-bibhatsa {
    color: #9acd32;
}

.rasa-shringara {
    color: #ff7eb6;
}

.session-info {
    margin-top: 14px;
    padding: 10px;
    border: 1px dashed #245f3c;
    color: #729b82;
    font-size: 11px;
    word-break: break-all;
}

.changelog-overlay {
    display: none;
    position: fixed;
    inset: 0;
    z-index: 9999;
    background: rgba(0, 20, 12, 0.88);
    padding: 5vh 5vw;
}

.changelog-window {
    width: min(1000px, 90vw);
    height: 90vh;
    margin: auto;
    border: 2px solid #75ff9b;
    background: #001f13;
    box-shadow: 0 0 30px rgba(117, 255, 155, 0.18);
    display: flex;
    flex-direction: column;
}

.changelog-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 14px 18px;
    border-bottom: 1px solid #245f3c;
    color: #8cffad;
}

.changelog-header h2 {
    margin: 0;
}

.changelog-close {
    width: 42px;
    min-width: 42px;
    height: 36px;
    background: transparent;
    color: #75ff9b;
    border: 1px solid #75ff9b;
    cursor: pointer;
}

.changelog-close:hover {
    background: #75ff9b;
    color: #002411;
}

.changelog-content {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
    color: #caffd8;
    white-space: pre-wrap;
    font-family: "Courier New", monospace;
    font-size: 14px;
    line-height: 1.6;
}

.changelog-status {
    padding: 8px 18px;
    border-top: 1px dashed #245f3c;
    color: #729b82;
    font-size: 11px;
}

.session-output-panel {
    margin-top: 18px;
}

.token-telemetry {
    margin-top: 14px;
}

.telemetry-panel {
    min-width: 0;
}

@media (max-width: 850px) {
    .grid { grid-template-columns: 1fr; }
    .chat { height: 70vh; min-height: 500px; }
    .input-area { flex-direction: column; }
    button { width: 100%; height: 45px; }
}

.scan-instructions {
    font-size: 13px;
    line-height: 1.6;
    color: #a7bcae;
    margin-top: 8px;
}

.scan-instructions p {
    margin: 6px 0;
}

.scan-animation {
    position: relative;
    height: 150px;
    border: 1px solid #62e889;
    background: #00150c;
    margin-top: 15px;
    overflow: hidden;
}

.scanner-document {
    width: 70%;
    height: 100px;
    border: 2px solid #caffd8;
    position: absolute;
    left: 15%;
    top: 25px;
    background: #eeeeee;
}

.scanner-beam {
    position: absolute;
    left: 0;
    width: 100%;
    height: 3px;
    background: #75ff9b;
    box-shadow: 0 0 15px #75ff9b;
    animation: scanBeam 1.5s linear infinite;
}

@keyframes scanBeam {

    0% {
        top: 0;
    }

    100% {
        top: 100%;
    }

}

/* ============================================================
   CONVERSATION SCROLL
   Only previous messages scroll.
   The input area remains fixed.
   ============================================================ */

.chat {
    display: flex;
    flex-direction: column;
    height: 650px;
    min-height: 0;
    box-sizing: border-box;
    overflow: hidden;
}

.messages {
    flex: 1 1 auto;
    min-height: 0;
    overflow-y: auto;
    overflow-x: hidden;
}

.input-area {
    flex: 0 0 auto;
}

.session-output-receipt {
    margin-top: 16px;
    max-height: 720px;
    overflow: auto;
    padding: 28px;
    background: #eee9dc;
    color: #171717;
    border: 1px solid #8c8c8c;
    box-shadow: 0 0 18px rgba(0,0,0,0.18);
}
.session-output-receipt pre {
    margin: 0;
    white-space: pre-wrap;
    word-break: break-word;
    font-family: "Courier New", monospace;
    font-size: 13px;
    line-height: 1.55;
}
.session-output-actions {
    display: flex;
    gap: 10px;
    margin-top: 12px;
    flex-wrap: wrap;
}
.session-output-actions button {
    width: auto;
    min-width: 180px;
}
</style>
</head>

<body>
<div class="page">

<div class="header">
    <button
        class="changelog-button"
        onclick="openChangelog()">
        CHANGELOG
    </button>

    <h1>FREEING THE PARROT</h1>
    <p>THE MACHINE IS NOT YOUR ORACLE. IT IS YOUR MIRROR.</p>
    <div class="status">
        [ SYSTEM ONLINE ]<br>
        [ NAVARASA ENGINE CONNECTED ]<br>
        [ SOCRATIC MODE READY ]
    </div>
</div>

<div id="changelog-overlay" class="changelog-overlay">

    <div class="changelog-window">

        <div class="changelog-header">

            <h2>[ SYSTEM CHANGELOG ]</h2>

            <button
                class="changelog-close"
                onclick="closeChangelog()">
                X
            </button>

        </div>

        <div
            id="changelog-content"
            class="changelog-content">
            LOADING CHANGELOG...
        </div>

        <div
            id="changelog-status"
            class="changelog-status">
            CHANGELOG STATUS: WAITING
        </div>

    </div>

</div>

<div class="panel scan-panel">

    <h2>[ 1. WRITE & UPLOAD YOUR STORY ]</h2>

    <div class="scan-input">

        <p>
            YOUR STORIES ARE YOUR IDENTITY.
        </p>

        <div class="scan-instructions">

    <p>
        • Grab a piece of paper and a pen.
    </p>

    <p>
        • Write something that is yours — a memory, thought, feeling,
        story, frustration, or anything you want to share, on that piece of paper.
    </p>

    <p>
        • Scan your handwritten note using any scanner or scanning app.
    </p>

    <p>
        • Scan the note using any scanner app, OR take a clear photo of the handwritten note using your camera.
    </p>

    <p>
        • Make sure the scan or photo is taken in a well-lit environment, with the page flat and the handwriting clearly visible.
    </p>

    <p>
        • Save the image as a PNG, JPG, JPEG, BMP, TIF or TIFF file.
    </p>

    <p>
        • Click 'UPLOAD' and select the image.
    </p>

    <p>
        • Watch the emotional data being constructed and scroll down
        to chat with the system.
    </p>

</div>
       
        <input
            type="file"
            id="scan-file-input"
            accept=".png,.jpg,.jpeg,.bmp,.tif,.tiff"
            style="display:none;"
        >

        <button
            id="scan-button"
            onclick="selectScanFile()"
        >
            UPLOAD
        </button>
    </div>

    <div
        id="scan-animation"
        class="scan-animation hidden"
    >

        <div class="scanner-beam"></div>

        <div class="scan-status">
            WAITING...
        </div>

    </div>

    <div class="progress-container">

        <div
            id="scan-progress"
            class="progress-bar"
        ></div>

    </div>

    <div
        id="scan-progress-text"
        class="scan-progress-text"
    >
        0%
    </div>

    <div
        id="scan-log"
        class="scan-log"
    >
        SYSTEM WAITING FOR DOCUMENT.
    </div>

    <div
        id="scan-result"
        class="scan-result hidden"
    >

        <h3>
            [ PROCESSED OUTPUT ]
        </h3>

        <pre id="scan-output"></pre>

    </div>

</div>

<div class="grid">

<div class="panel chat">
    <h2>[ 2. CONVERSATION ]</h2>

    <p class="muted">
    Now that you are done scanning, the emotional database is updated
    with your data.
</p>

<p class="muted">
    Greet the system, and send a minimum of 3 messages about how you feel
    or how your day is going.
</p>

<p class="muted">
    <strong>Watch what it does after.</strong>
</p>

    <h3>[ 3. CHAT WITH THE SYSTEM ]</h3>

    <div id="messages" class="messages"></div>

        <div class="input-area">
        <textarea id="input"
            placeholder="Write what you want to tell the parrot..."
            aria-label="Message"></textarea>
        <button id="send-button" onclick="sendMessage()">SEND</button>
        <button id="done-button" onclick="endConversation()">I AM DONE!</button>
    </div>

</div>

<div class="panel telemetry-panel">
   <h2>[ 4. BACKEND TELEMETRY ]</h2>

    <div class="signal">
        <span class="label">PRIMARY RASA</span><br>
        <span id="primary-rasa" class="value">--</span>
    </div>

    <div class="signal">
        <span class="label">VALIDATION</span><br>
        <span id="validation" class="value">--</span>
    </div>

    <div class="signal">
        <span class="label">FAST RELIEF</span><br>
        <span id="fast-relief" class="value">--</span>
    </div>

    <div class="signal">
        <span class="label">EXPLETIVE</span><br>
        <span id="expletive" class="value">--</span>
    </div>

    <div class="signal">
        <span class="label">ANXIETY SIGNAL</span><br>
        <span id="anxiety" class="value">--</span>
    </div>

    <div class="signal">
        <span class="label">CURRENT GATE</span><br>
        <span id="gate" class="value">--</span>
    </div>

    <div class="signal">
        <span class="label">ROAST / GLITCH LEVEL</span><br>
        <span id="roast-level" class="value">0</span>
    </div>

    <div class="signal">
        <span class="label">SENTIMENT COMPOUND</span><br>
        <span id="compound" class="value">--</span>
    </div>

    <div class="signal">
        <span class="label">RASA SCORES</span>
        <div id="rasa-scores">--</div>
    </div>

    <div id="printer-status"></div>
</div>

</div>

<div class="panel session-output-panel">
    <h2>[ 4. DIGITAL SESSION OUTPUT ]</h2>

    <p>
        THE ENTIRE CONVERSATION WILL BE PRESERVED
        AS A DIGITAL MIRROR REPORT.
    </p>

    <p class="muted">
        The receipt format remains. The thermal printer does not.
        Your complete conversation appears here as a digital record.
    </p>

    <div id="session-output-status" class="scan-log">
        DIGITAL OUTPUT STANDBY.
    </div>

    <div id="session-output-receipt" class="session-output-receipt hidden">
        <pre id="session-output-text"></pre>
    </div>

    <div id="session-output-actions" class="session-output-actions hidden">
        <button id="download-session-text" onclick="downloadSessionText()">
            DOWNLOAD TEXT
        </button>

        <button id="download-session-image" onclick="downloadSessionImage()">
            DOWNLOAD IMAGE
        </button>
    </div>
</div>



<div class="panel">
    <h2>[ SYSTEM LOGIC ]</h2>

    <div class="architecture">
    <div>INPUT
↓
emotional text</div>

    <div>NAVARASA
↓
emotional mapping</div>

    <div>GATE 1
↓
validation / fast relief</div>

    <div>GATE 2
↓
Socratic friction</div>

    <div>ANSWER COUNT
↓
roast increases</div>

    <div>I AM DONE!
↓
maximum glitch / shutdown</div>
    </div>

    <div id="session-info" class="session-info">
        SESSION: NOT INITIALISED
    </div>
</div>

<script>

if ("scrollRestoration" in history) {
    history.scrollRestoration = "manual";
}

window.addEventListener("load", function() {
    window.scrollTo(0, 0);
});

async function openChangelog() {

    const overlay =
        document.getElementById("changelog-overlay");

    const content =
        document.getElementById("changelog-content");

    const status =
        document.getElementById("changelog-status");

    overlay.style.display = "flex";

    content.textContent =
        "LOADING CHANGELOG...\n\n" +
        "ACCESSING SYSTEM HISTORY...";

    status.textContent =
        "CHANGELOG STATUS: READING SOURCE FILE";

    try {

        const response =
            await fetch("/api/changelog");

        const data =
            await response.json();

        if (!response.ok || data.error) {

            content.textContent =
                "[CHANGELOG ERROR]\n\n" +
                (data.error || "Unable to load changelog.");

            status.textContent =
                "CHANGELOG STATUS: ERROR";

            return;
        }

        content.textContent = data.content;

        status.textContent =
            "CHANGELOG STATUS: ONLINE | SOURCE: changelog.md";

    } catch (error) {

        content.textContent =
            "[CHANGELOG ERROR]\n\n" +
            error.message;

        status.textContent =
            "CHANGELOG STATUS: CONNECTION FAILURE";
    }
}


function closeChangelog() {

    document.getElementById(
        "changelog-overlay"
    ).style.display = "none";
}


document.addEventListener(
    "keydown",
    function(event) {

        if (event.key === "Escape") {
            closeChangelog();
        }

    }
);

let sessionId = null;
let interfaceClosed = false;

function addMessage(role, text) {
    if (!text) return;

    const container = document.getElementById("messages");
    const div = document.createElement("div");

    div.className = "message " + role;

    if (role === "system") {

        const rasaNames = [
            "Shanta",
            "Karuna",
            "Raudra",
            "Bhayanaka",
            "Veera",
            "Adbhuta",
            "Hasya",
            "Bibhatsa",
            "Shringara"
        ];

        const lines = String(text).split("\n");

        lines.forEach((line, index) => {

            const rasaMatch =
                line.match(/^I detected (Shanta|Karuna|Raudra|Bhayanaka|Veera|Adbhuta|Hasya|Bibhatsa|Shringara)\.$/i);

            if (rasaMatch) {

                const rasa = rasaMatch[1];
		const rasaClass = rasa.toLowerCase();

		const span = document.createElement("span");

		span.className =
    		"rasa-detected rasa-" + rasa.toLowerCase();

                span.textContent = line;

                div.appendChild(span);

            } else {

                div.appendChild(
                    document.createTextNode(line)
                );

            }

            if (index < lines.length - 1) {
                div.appendChild(
                    document.createTextNode("\n")
                );
            }
        });

    } else {

        div.textContent = text;
    }

     container.appendChild(div);
    container.scrollTop = container.scrollHeight;

    updateTokenTelemetry();
}

function updateTokenTelemetry() {
    const container = document.getElementById("messages");

    if (!container) return;

    const messages = container.querySelectorAll(".message");

    let userCharacters = 0;
    let machineCharacters = 0;

    messages.forEach(function(message) {
        const text = message.textContent || "";
        const characters = text.length;

        if (message.classList.contains("user")) {
            userCharacters += characters;
        } else if (message.classList.contains("system")) {
            machineCharacters += characters;
        }
    });

    const totalCharacters =
        userCharacters + machineCharacters;

    const userTokens =
        Math.ceil(userCharacters / 4);

    const machineTokens =
        Math.ceil(machineCharacters / 4);

    const totalTokens =
        Math.ceil(totalCharacters / 4);

    const elements = {
        userCharacters: document.getElementById("user-characters"),
        machineCharacters: document.getElementById("machine-characters"),
        totalCharacters: document.getElementById("total-characters"),
        userTokens: document.getElementById("user-tokens"),
        machineTokens: document.getElementById("machine-tokens"),
        totalTokens: document.getElementById("total-tokens")
    };

    if (elements.userCharacters) {
        elements.userCharacters.textContent =
            userCharacters.toLocaleString();
    }

    if (elements.machineCharacters) {
        elements.machineCharacters.textContent =
            machineCharacters.toLocaleString();
    }

    if (elements.totalCharacters) {
        elements.totalCharacters.textContent =
            totalCharacters.toLocaleString();
    }

    if (elements.userTokens) {
        elements.userTokens.textContent =
            userTokens.toLocaleString();
    }

    if (elements.machineTokens) {
        elements.machineTokens.textContent =
            machineTokens.toLocaleString();
    }

    if (elements.totalTokens) {
        elements.totalTokens.textContent =
            totalTokens.toLocaleString();
    }
}

function updateTelemetry(data) {
    const analysis = data.analysis || {};
    const gate = data.gate || {};

    document.getElementById("primary-rasa").textContent =
        analysis.primary_rasa || "Shanta";

    document.getElementById("validation").textContent =
        gate.validation_detected ? "DETECTED" : "NOT DETECTED";

    document.getElementById("fast-relief").textContent =
        gate.fast_relief_detected ? "DETECTED" : "NOT DETECTED";

    document.getElementById("expletive").textContent =
        gate.expletive_detected ? "DETECTED" : "NOT DETECTED";

    document.getElementById("anxiety").textContent =
        gate.anxiety_detected ? "DETECTED" : "NOT DETECTED";

    document.getElementById("gate").textContent =
        gate.gate || "reflection";

    document.getElementById("roast-level").textContent =
        data.roast_level !== undefined ? data.roast_level : 0;

    const sentiment = analysis.sentiment || {};

    document.getElementById("compound").textContent =
        sentiment.compound !== undefined
            ? sentiment.compound
            : "--";

    const rasaContainer =
        document.getElementById("rasa-scores");

    rasaContainer.innerHTML = "";

    const scores = analysis.rasa_scores || {};
    const entries = Object.entries(scores);

    if (!entries.length) {
        rasaContainer.textContent = "--";
    } else {
        entries.forEach(([rasa, score]) => {
            const span = document.createElement("span");
            span.className = "rasa";
            span.textContent = rasa + " : " + score;
            rasaContainer.appendChild(span);
        });
    }

    if (data.printer) {
        const printer = data.printer;

        document.getElementById("printer-status").innerHTML =
            "<div class='receipt'>" +
            "DIGITAL MIRROR REPORT<br><br>" +
            (printer.printed
                ? "PRINT JOB SENT."
                : "PRINTER NOT CONFIGURED.<br>RECEIPT SAVED LOCALLY.") +
            "</div>";
    }

    if (data.session_id) {
        sessionId = data.session_id;

        document.getElementById("session-info").textContent =
            "SESSION: " + sessionId +
            " | TURN: " + (data.turn || "--");
    }
}


function disableInterface() {
    const input = document.getElementById("input");
    const button = document.getElementById("send-button");

    input.disabled = true;
    button.disabled = true;
    button.textContent = "CLOSED";
}

async function endConversation() {
    if (interfaceClosed || !sessionId) return;

    const input = document.getElementById("input");
    const sendButton = document.getElementById("send-button");
    const doneButton = document.getElementById("done-button");

    // Immediately prevent duplicate clicks / further input
    if (input) input.disabled = true;
    if (sendButton) sendButton.disabled = true;
    if (doneButton) {
        doneButton.disabled = true;
        doneButton.textContent = "PROCESSING";
    }

    try {
        const response = await fetch(
            "/api/end-conversation",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    session_id: sessionId
                })
            }
        );

        const data = await response.json();

        if (!response.ok || data.error) {
            console.error(
                "[END CONVERSATION]",
                data.error || "Request failed."
            );

            // Re-enable interface if the request failed
            if (input) input.disabled = false;
            if (sendButton) sendButton.disabled = false;
            if (doneButton) {
                doneButton.disabled = false;
                doneButton.textContent = "I AM DONE!";
            }

            return;
        }

        // Backend has successfully ended the conversation.
        interfaceClosed = true;

        addMessage("system", data.message);
        updateTelemetry(data);

        if (doneButton) {
            doneButton.textContent = "CLOSED";
        }

        // Printing remains automatic.
        if (data.auto_print) {
            setTimeout(function() {
                generateSessionOutput();
            }, 100);
        }

    } catch (error) {
        console.error(
            "[END CONVERSATION] Connection error:",
            error
        );

        // Re-enable interface if the server could not be reached
        if (input) input.disabled = false;
        if (sendButton) sendButton.disabled = false;
        if (doneButton) {
            doneButton.disabled = false;
            doneButton.textContent = "I AM DONE!";
        }
    }
}

async function sendMessage() {
    if (interfaceClosed) return;

    // Any real user response immediately ends the old wait.

    const input = document.getElementById("input");
    const button = document.getElementById("send-button");

    const text = input.value.trim();

    if (!text) return;

    addMessage("user", text);

    input.value = "";
    button.disabled = true;
    button.textContent = "PROCESSING";

    try {
        const response = await fetch(
            "/api/chat",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    session_id: sessionId,
                    message: text
                })
            }
        );

        const data = await response.json();

        if (!response.ok || data.error) {
            addMessage(
    "system",
    "[ERROR]\n" +
    (data.error || "Request failed.")
);
            return;
        }

        sessionId = data.session_id;

        addMessage(
            "system",
            data.response
        );

        updateTelemetry(data);

        if (data.closed) {
            interfaceClosed = true;
            disableInterface();

            if (data.auto_print) {
                setTimeout(function() {
                    generateSessionOutput();
                }, 100);
            }
        }

    } catch (error) {
        addMessage(
            "system",
            "[INTERFACE ERROR]\n" +
            error.message
        );

    } finally {
        if (!interfaceClosed) {
            button.disabled = false;
            button.textContent = "SEND";
            input.focus();
        }
    }
}

let scanPollingTimer = null;
let scanLogLines = [];
let scanHasStarted = false;


function resetScanInterface() {
    scanLogLines = [];
    scanHasStarted = false;

    const progress = document.getElementById("scan-progress");
    const progressText = document.getElementById("scan-progress-text");
    const log = document.getElementById("scan-log");
    const result = document.getElementById("scan-result");
    const output = document.getElementById("scan-output");

    if (progress) progress.style.width = "0%";
    if (progressText) progressText.textContent = "0%";
    if (log) log.textContent = "SYSTEM WAITING FOR DOCUMENT.";
    if (output) output.textContent = "";
    if (result) result.classList.add("hidden");
}


function appendScanLines(incomingLines) {
    const incoming = Array.isArray(incomingLines)
        ? incomingLines.map(line => String(line))
        : [];

    if (!incoming.length) return;

    const friendlyLines = [];

    incoming.forEach(line => {

        if (
            line.includes("[WATCHDOG]") ||
            line.includes("NEW DOCUMENT DETECTED")
        ) {
            friendlyLines.push(
                "DOCUMENT DETECTED."
            );
        }

        if (
            line.includes("[OCR] Generating preprocessing") ||
            line.includes("Generating preprocessing variants")
        ) {
            friendlyLines.push(
                "READING YOUR HANDWRITTEN NOTE..."
            );
        }

        if (
            line.includes("[OCR] Testing variant") ||
            line.includes("[OCR CANDIDATES]")
        ) {
            friendlyLines.push(
                "EXTRACTING YOUR WRITING..."
            );
        }

        if (
            line.includes("[OCR RESULT]")
        ) {
            friendlyLines.push(
                "YOUR NOTE HAS BEEN READ."
            );
        }

        if (
            line.includes("[NAVARASA ENGINE]") ||
            line.includes("[NAVARASA PROFILE]")
        ) {
            friendlyLines.push(
                "UNDERSTANDING THE EMOTIONAL SIGNALS..."
            );
        }

        if (
            line.includes("[SENTIMENT]")
        ) {
            friendlyLines.push(
                "MAPPING YOUR EMOTIONAL STATE..."
            );
        }

        if (
            line.includes("[DATABASE]")
        ) {
            friendlyLines.push(
                "SAVING YOUR EMOTIONAL DATA..."
            );
        }

        if (
            line.includes("[SESSION] Session updated")
        ) {
            friendlyLines.push(
                "YOUR EMOTIONAL DATA HAS BEEN RECORDED."
            );
        }

        if (
            line.includes("[ENGINE] SCAN COMPLETE")
        ) {
            friendlyLines.push(
                "SCAN COMPLETE. YOUR CONVERSATION IS READY."
            );
        }
    });

    if (!friendlyLines.length) return;

    friendlyLines.forEach(line => {
        if (!scanLogLines.includes(line)) {
            scanLogLines.push(line);
        }
    });

    const log = document.getElementById("scan-log");

    if (log) {
        log.textContent = scanLogLines.join("\n");
        log.scrollTop = log.scrollHeight;
    }
}


function startScanPolling() {
    stopScanPolling();
    scanPollingTimer = setInterval(pollScanStatus, 250);
    pollScanStatus();
}


function stopScanPolling() {
    if (scanPollingTimer !== null) {
        clearInterval(scanPollingTimer);
        scanPollingTimer = null;
    }
}


async function pollScanStatus() {
    try {
        const response = await fetch(
            "/api/scan-status",
            { cache: "no-store" }
        );
        const data = await response.json();
        updateScanInterface(data);
    } catch (error) {
        console.error("Scan status error:", error);
    }
}


function updateScanInterface(data) {
    const progress = document.getElementById("scan-progress");
    const progressText = document.getElementById("scan-progress-text");
    const result = document.getElementById("scan-result");
    const output = document.getElementById("scan-output");
    const scanButton = document.getElementById("scan-button");

    const status = data.status || "idle";
    const progressValue = Number(data.progress || 0);

    if (status === "detected" && !scanHasStarted) {
        scanHasStarted = true;
        scanLogLines = [];
    }

    if (progress) progress.style.width = `${progressValue}%`;
    if (progressText) progressText.textContent = `${progressValue}%`;

    appendScanLines(data.lines);

    if (status === "complete") {
        if (result) result.classList.remove("hidden");
        if (output) {
            output.textContent = JSON.stringify(data.result || {}, null, 2);
        }
        if (scanButton) {
            scanButton.disabled = false;
            scanButton.textContent = "UPLOAD";
        }
        return;
    }

    if (status === "error") {
        if (scanButton) {
            scanButton.disabled = false;
            scanButton.textContent = "UPLOAD";
        }
        return;
    }

    if (scanButton && status !== "idle") {
        scanButton.disabled = true;
        scanButton.textContent = "PROCESSING...";
    }
}


function selectScanFile() {
    const fileInput = document.getElementById("scan-file-input");

    if (fileInput) {
        fileInput.value = "";
        fileInput.click();
    }
}


async function uploadScanFile(file) {
    const scanButton = document.getElementById("scan-button");

    try {
        await fetch("/api/scan-reset", {
            method: "POST",
            cache: "no-store"
        });

        resetScanInterface();
        startScanPolling();

        if (scanButton) {
            scanButton.disabled = true;
            scanButton.textContent = "UPLOADING...";
        }

        const formData = new FormData();
        formData.append("document", file);

        const response = await fetch(
            "/api/scan-upload",
            {
                method: "POST",
                body: formData
            }
        );

        const data = await response.json();

        if (!response.ok || !data.ok) {
            throw new Error(
                data.error || "Could not upload the scanned document."
            );
        }

        console.log("[SCAN] Document uploaded. Analysis started.");

    } catch (error) {
        console.error("[SCAN] Upload error:", error);
        const log = document.getElementById("scan-log");
        if (log) {
            log.textContent = "[SCAN ERROR]\n" + error.message;
        }
        stopScanPolling();
        if (scanButton) {
            scanButton.disabled = false;
            scanButton.textContent = "UPLOAD";
        }
    }
}


document.addEventListener("DOMContentLoaded", function() {
    const fileInput = document.getElementById("scan-file-input");

    if (fileInput) {
        fileInput.addEventListener("change", function() {
            const file = this.files && this.files[0];

            if (file) {
                uploadScanFile(file);
            }
        });
    }
});


async function generateSessionOutput() {
    const status = document.getElementById("session-output-status");

    try {
        if (!sessionId) throw new Error("No active conversation session.");

        if (status) status.textContent = "GENERATING DIGITAL MIRROR REPORT...";

        const response = await fetch("/api/session-output", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({session_id: sessionId})
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.error || "Could not generate session output.");
        }

        const text = document.getElementById("session-output-text");
        const receipt = document.getElementById("session-output-receipt");
        const actions = document.getElementById("session-output-actions");

        if (text) text.textContent = data.text || "";
        if (receipt) receipt.classList.remove("hidden");
        if (actions) actions.classList.remove("hidden");
        if (status) status.textContent = "DIGITAL MIRROR REPORT READY.";

        setTimeout(() => {
            if (receipt) receipt.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });
        }, 100);

    } catch (error) {
        console.error("[SESSION OUTPUT]", error);
        if (status) status.textContent = "[SESSION OUTPUT ERROR] " + error.message;
    }
}


function downloadSessionText() {
    const text = document.getElementById("session-output-text")?.textContent || "";
    if (!text) return;

    const blob = new Blob([text], {type: "text/plain;charset=utf-8"});
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.download = "freeing-the-parrot-mirror-report.txt";

    document.body.appendChild(link);
    link.click();
    link.remove();

    URL.revokeObjectURL(url);
}


function wrapCanvasText(ctx, text, maxWidth) {
    const words = text.split(" ");
    const lines = [];
    let current = "";

    words.forEach(word => {
        const test = current ? current + " " + word : word;

        if (ctx.measureText(test).width > maxWidth && current) {
            lines.push(current);
            current = word;
        } else {
            current = test;
        }
    });

    if (current) lines.push(current);
    return lines;
}


function downloadSessionImage() {
    const text = document.getElementById("session-output-text")?.textContent || "";
    if (!text) return;

    const width = 900;
    const padding = 70;
    const contentWidth = width - padding * 2;
    const fontSize = 18;
    const lineHeight = 30;

    const measureCanvas = document.createElement("canvas");
    const measureCtx = measureCanvas.getContext("2d");

    measureCtx.font = fontSize + 'px "Courier New", monospace';

    const wrappedLines = [];
    text.split("\n").forEach(line => {
        if (!line) {
            wrappedLines.push("");
        } else {
            wrappedLines.push(...wrapCanvasText(
                measureCtx,
                line,
                contentWidth
            ));
        }
    });

    const height = padding * 2 + 120 + wrappedLines.length * lineHeight;

    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;

    const ctx = canvas.getContext("2d");

    ctx.fillStyle = "#eee9dc";
    ctx.fillRect(0, 0, width, height);

    ctx.fillStyle = "#171717";
    ctx.textAlign = "center";
    ctx.font = 'bold 26px "Courier New", monospace';
    ctx.fillText("FREEING THE PARROT", width / 2, padding);

    ctx.font = 'bold 18px "Courier New", monospace';
    ctx.fillText("-- MIRROR REPORT --", width / 2, padding + 34);

    ctx.textAlign = "left";
    ctx.font = fontSize + 'px "Courier New", monospace';

    let y = padding + 90;

    wrappedLines.forEach(line => {
        ctx.fillText(line, padding, y);
        y += lineHeight;
    });

    ctx.strokeStyle = "rgba(40,40,40,0.45)";
    ctx.setLineDash([4, 7]);

    ctx.beginPath();
    ctx.moveTo(28, 16);
    ctx.lineTo(width - 28, 16);
    ctx.moveTo(28, height - 16);
    ctx.lineTo(width - 28, height - 16);
    ctx.stroke();

    canvas.toBlob(function(blob) {
        if (!blob) return;

        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");

        link.href = url;
        link.download = "freeing-the-parrot-mirror-report.png";

        document.body.appendChild(link);
        link.click();
        link.remove();

        URL.revokeObjectURL(url);
    }, "image/png");
}


const inputBox =
    document.getElementById("input");


inputBox.addEventListener(
    "keydown",
    function(event) {

        if (
            event.key === "Enter"
            &&
            !event.shiftKey
        ) {
            event.preventDefault();
            event.stopPropagation();

            sendMessage();
        }
    }
);


inputBox.focus();
</script>

</body>
</html>
"""
# ============================================================
# ROUTES
# ============================================================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/kimi/", defaults={"filename": ""})
@app.route("/kimi/<path:filename>")
def kimi_frontend(filename):
    """Serve the optional production Kimi bundle without changing the root UI."""
    if not KIMI_DIST_DIR.exists():
        return jsonify({
            "error": "Kimi production bundle is not built.",
            "build_directory": str(KIMI_DIST_DIR),
        }), 503

    requested = filename or "index.html"
    return send_from_directory(str(KIMI_DIST_DIR), requested)


@app.route("/legacy")
def home_legacy():
    """Previous participant interface (scan, telemetry panels, arcade UI)."""
    return render_template_string(HTML_LEGACY)


@app.route("/api/session/start", methods=["POST"])
def session_start():
    """Establish participant session + FTP 2.0 coordinator (before chat/ingest)."""
    session_id = begin_ftp2_participant_session()
    return jsonify({
        "ok": True,
        "session_id": session_id,
        "state": SessionState.INPUT_INGESTION.value,
        "analysis_ready": False,
    })


@app.route("/api/input/text", methods=["POST"])
def input_text():
    """Analyze the initial written offering without invoking the Parrot."""
    data = request.get_json(silent=True) or {}
    session_id = str(data.get("session_id") or "").strip()
    text = str(data.get("text") or "").strip()

    if not session_id:
        return jsonify({"error": "session_id is required."}), 400
    if not text:
        return jsonify({"error": "text is required."}), 400

    coordinator = get_ftp2_coordinator(session_id)
    session = SESSIONS.get(session_id)
    if coordinator is None or session is None:
        return jsonify({"error": "Session not found."}), 404
    if coordinator.state != SessionState.INPUT_INGESTION:
        return jsonify({
            "error": "Initial offering is no longer accepted.",
            "state": coordinator.state.value,
        }), 409

    analysis, _gate_state = analyse_message(text)
    coordinator.record_raw_input(build_text_raw_ingest_payload(text))
    event = coordinator.mark_analysis_ready(analysis)

    return jsonify({
        "ok": True,
        "session_id": session_id,
        "state": coordinator.state.value,
        "analysis_ready": coordinator.analysis_ready,
        "event_id": event.event_id,
    })


@app.route("/api/input/ingest", methods=["POST"])
def input_ingest():
    session_id = request.form.get("session_id", "").strip()
    modality = request.form.get("modality", "").strip().upper()

    if not session_id:
        return jsonify({"error": "session_id is required."}), 400

    coordinator = get_ftp2_coordinator(session_id)
    if coordinator is None:
        return jsonify({
            "error": "Session not found. Enter the experience first.",
        }), 404

    if session_id not in SESSIONS:
        return jsonify({"error": "Session not found."}), 404

    if SESSIONS[session_id].get("intervention_closed"):
        return jsonify({"error": "This conversation has ended."}), 403

    allowed = {"AUDIO", "IMAGE", "CAMERA"}
    if modality not in allowed:
        return jsonify({
            "error": "modality must be AUDIO, IMAGE, or CAMERA.",
        }), 400

    upload = request.files.get("file")
    if upload is None or not upload.filename:
        return jsonify({"error": "file is required."}), 400

    data = upload.read()
    if len(data) == 0:
        return jsonify({"error": "Empty file."}), 400
    if len(data) > MAX_INGEST_BYTES:
        return jsonify({"error": "File too large."}), 413

    extension = Path(upload.filename).suffix.lower() or ".bin"
    if modality == "AUDIO" and extension not in {
        ".webm", ".ogg", ".wav", ".mp3", ".m4a", ".bin",
    }:
        extension = ".webm"
    if modality in ("IMAGE", "CAMERA") and extension not in {
        ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".bin",
    }:
        extension = ".jpg"

    duration_ms = None
    metadata_raw = request.form.get("metadata")
    if metadata_raw:
        try:
            meta = json.loads(metadata_raw)
            if "duration_ms" in meta:
                duration_ms = int(meta["duration_ms"])
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    digest = sha256_bytes(data)
    saved_path, storage_ref = save_session_media(
        INGEST_MEDIA_DIR,
        session_id,
        extension,
        data,
    )

    if modality == "AUDIO":
        source_channel = "WEB_MICROPHONE"
        media_modality = "AUDIO"
    elif modality == "CAMERA":
        source_channel = "WEB_CAMERA"
        media_modality = "IMAGE"
    else:
        source_channel = "WEB_FILE_UPLOAD"
        media_modality = "IMAGE"

    media_format = extension.lstrip(".").upper()
    payload = build_raw_ingest_payload(
        media_modality,
        source_channel,
        byte_size=len(data),
        content_sha256=digest,
        storage_ref=storage_ref,
        media_format=media_format,
        duration_ms=duration_ms,
    )

    try:
        event = coordinator.record_raw_input(payload)
    except SessionLockedError as exc:
        return jsonify({"error": str(exc)}), 403
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if coordinator.state == SessionState.INPUT_INGESTION:
        coordinator.mark_raw_offering_ready()
    elif coordinator.state == SessionState.LIVE_CONVERSATION:
        try:
            run_silent_reader_pass(coordinator)
        except Exception:
            pass

    return jsonify({
        "ok": True,
        "session_id": session_id,
        "ingest_id": payload["ingest_id"],
        "event_id": event.event_id,
        "message": "Received.",
        "state": coordinator.state.value,
        "analysis_ready": coordinator.analysis_ready,
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}

    message = data.get("message", "")
    session_id = data.get("session_id")

    coordinator = get_ftp2_coordinator(session_id)
    if coordinator is None:
        return jsonify({"error": "Session not found."}), 404
    if coordinator.state != SessionState.LIVE_CONVERSATION:
        return jsonify({
            "error": "Session is not ready for live conversation.",
            "state": coordinator.state.value,
            "analysis_ready": coordinator.analysis_ready,
        }), 409

    session = get_session(session_id)

    result = process_chat_message(session, message)

    coordinator = get_ftp2_coordinator(session["id"])

    try:
        record_chat_timeline_events(coordinator, message, result)
    except Exception:
        pass

    try:
        run_silent_reader_pass(
            coordinator,
            user_message=message,
            chat_result=result,
            composer_telemetry=data.get("composer_telemetry"),
        )
    except Exception:
        pass

    return jsonify(result)

@app.route("/api/end-conversation", methods=["POST"])
def end_conversation_route():
    data = request.get_json(silent=True) or {}

    session_id = data.get("session_id")
    session = SESSIONS.get(session_id)

    if session is None:
        return jsonify({
            "error": "Session not found."
        }), 404

    coordinator = get_ftp2_coordinator(session_id)
    if coordinator is not None and coordinator.state != SessionState.LIVE_CONVERSATION:
        return jsonify({
            "error": "Session is not in live conversation.",
            "state": coordinator.state.value,
            "analysis_ready": coordinator.analysis_ready,
        }), 409

    if session.get("intervention_closed"):
        return jsonify({
            "closed": True,
            "shutdown": True,
            "message": "THE PARROT HAS ALREADY STOPPED.",
            "auto_print": True,
            "close_reason": "already_closed",
        })

    result = end_conversation(session)
    if coordinator is not None:
        coordinator.lock()
        coordinator.advance(SessionState.POST_SESSION_INTERPRETATION)
        coordinator.generate_post_session_interpretation()
        coordinator.advance(SessionState.CARD_SELECTION)
        result["lifecycle_state"] = coordinator.state.value
        result["cards"] = participant_facing_cards(coordinator)
    return jsonify(result)


@app.route("/api/session-lifecycle", methods=["POST"])
def session_lifecycle():
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    try:
        coordinator = advance_participant_lifecycle(
            session_id,
            data.get("action"),
            data,
        )
    except ValueError as exc:
        status = 409 if data.get("action") == "input_complete" else 400
        return jsonify({"error": str(exc)}), status
    except Exception as exc:
        return jsonify({"error": str(exc)}), 409

    return jsonify({
        "ok": True,
        "session_id": session_id,
        "lifecycle_state": coordinator.state.value,
    })

# Kept for manual PowerShell testing.

@app.route("/api/changelog", methods=["GET"])
def changelog():
    # Prefer the installation root, but also support running this server
    # from another working directory or from a copied project folder.
    candidates = [
        BASE_DIR / "changelog.md",
        Path(__file__).resolve().parent / "changelog.md",
    ]

    changelog_file = next(
        (path for path in candidates if path.exists()),
        candidates[0],
    )

    if not changelog_file.exists():
        return jsonify({
            "error": (
                "changelog.md not found. Place changelog.md in "
                f"{BASE_DIR} or beside interface_server.py."
            )
        }), 404

    try:
        content = changelog_file.read_text(encoding="utf-8")

        return jsonify({
            "content": content,
            "source": str(changelog_file),
        })

    except Exception as exc:
        return jsonify({
            "error": str(exc)
        }), 500

@app.route("/api/data")
def data():
    if not SESSION_FILE.exists():
        return jsonify({"status": "waiting"})

    try:
        with open(SESSION_FILE, "r", encoding="utf-8") as file:
            return jsonify(json.load(file))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/session/<session_id>")
def get_session_data(session_id):
    session = SESSIONS.get(session_id)

    if session is None:
        return jsonify({"error": "Session not found."}), 404

    return jsonify(session)

@app.route("/api/session-output-status")
def session_output_status():
    if not SESSION_OUTPUT_STATUS_FILE.exists():
        return jsonify({
            "status": "idle",
            "progress": 0,
            "message": "DIGITAL OUTPUT STANDBY.",
            "lines": []
        })

    try:
        with open(SESSION_OUTPUT_STATUS_FILE, "r", encoding="utf-8") as file:
            return jsonify(json.load(file))
    except Exception as exc:
        return jsonify({
            "status": "error",
            "progress": 0,
            "message": str(exc),
            "lines": []
        })


@app.route("/api/session-output-reset", methods=["POST"])
def session_output_reset():
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    if session_id:
        coordinator = get_ftp2_coordinator(session_id)
        if coordinator is None:
            return jsonify({"ok": False, "error": "Session not found."}), 404
        try:
            coordinator.record(
                EventType.SESSION_PURGED,
                ProvenanceLevel.OBSERVED,
                {"consent_type": data.get("consent_type")},
            )
            coordinator.advance(SessionState.PURGE_AND_RESET)
            coordinator.advance(SessionState.IDLE_STANDBY)
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 409
        FTP2_COORDINATORS.pop(session_id, None)

    write_session_output_status(
        "idle",
        0,
        "DIGITAL OUTPUT STANDBY.",
        lines=["DIGITAL OUTPUT STANDBY."]
    )
    return jsonify({"ok": True, "lifecycle_state": SessionState.IDLE_STANDBY.value})


@app.route("/api/session-output", methods=["POST"])
def session_output():
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    session = SESSIONS.get(session_id)

    if session is None:
        return jsonify({
            "success": False,
            "error": "Session not found."
        }), 404

    if not session.get("messages"):
        return jsonify({
            "success": False,
            "error": "There is no conversation to export."
        }), 400

    coordinator = get_ftp2_coordinator(session_id)
    if coordinator is not None and coordinator.state != SessionState.OUTPUT_GENERATION:
        return jsonify({
            "success": False,
            "error": "Session is not ready for output.",
        }), 409

    receipt_text = build_conversation_receipt(session)

    output_dir = BASE_DIR / "session_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"mirror_report_{timestamp}.txt"

    output_path.write_text(receipt_text, encoding="utf-8")

    write_session_output_status(
        "complete",
        100,
        "[SESSION OUTPUT] DIGITAL MIRROR REPORT READY",
        lines=[
            "[SESSION OUTPUT] SESSION RECEIVED",
            f"[SESSION OUTPUT] CONVERSATION MESSAGES: {len(session.get('messages', []))}",
            "[SESSION OUTPUT] DIGITAL MIRROR REPORT READY",
        ],
        result={
            "type": "digital_session_output",
            "session_id": session_id,
            "messages": len(session.get("messages", [])),
            "text": receipt_text,
            "path": str(output_path),
        },
    )

    if coordinator is not None:
        coordinator.record(
            EventType.RECEIPT_PRINTED,
            ProvenanceLevel.OBSERVED,
            {"output_type": "digital_mirror_report"},
        )

    return jsonify({
        "success": True,
        "session_id": session_id,
        "text": receipt_text
    })


@app.route(
    "/api/scan-upload",
    methods=["POST"]
)
def scan_upload():

    if "document" not in request.files:

        return jsonify({
            "error": "No document supplied."
        }), 400

    document = request.files["document"]

    if not document.filename:

        return jsonify({
            "error": "No filename supplied."
        }), 400

    allowed_extensions = {
        ".png",
        ".jpg",
        ".jpeg",
        ".bmp",
        ".tif",
        ".tiff"
    }

    extension = Path(
        document.filename
    ).suffix.lower()

    if extension not in allowed_extensions:

        return jsonify({
            "error": (
                "Unsupported document type. "
                "Use PNG, JPG, JPEG, BMP, TIF or TIFF."
            )
        }), 400

    INPUT_SCAN_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # Prevent strange filenames from becoming paths.
    safe_name = Path(
        document.filename
    ).name

    timestamp = datetime.datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    output_name = (
        f"INTERFACE_{timestamp}_{safe_name}"
    )

    output_path = (
        INPUT_SCAN_DIR /
        output_name
    )

    document.save(
        str(output_path)
    )

    update_scan_status(
        "detected",
        5,
        f"[UPLOAD] Document received: {output_name}",
        [
            "[UPLOAD] DOCUMENT RECEIVED",
            f"[FILE] {output_name}"
        ]
    )

    # Run the existing OCR -> Navarasa -> sentiment -> database pipeline
    # without blocking the Flask interface.
    import threading

    thread = threading.Thread(
        target=process_image,
        args=(str(output_path),),
        daemon=True
    )

    thread.start()

    return jsonify({
        "ok": True,
        "filename": output_name,
        "message": "SCAN RECEIVED. ANALYSIS STARTED."
    })


@app.route(
    "/api/scan-status"
)
def scan_status():

    if not SCAN_STATUS_FILE.exists():

        return jsonify({
            "status": "idle",
            "progress": 0,
            "message": "WAITING FOR DOCUMENT...",
            "lines": []
        })

    try:

        with open(
            SCAN_STATUS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return jsonify(
                json.load(file)
            )

    except Exception as exc:

        return jsonify({
            "status": "error",
            "progress": 0,
            "message": str(exc),
            "lines": []
        })

@app.route("/api/scan-reset", methods=["POST"])
def scan_reset():
    """Reset browser-facing scan state before a new physical scan."""
    payload = {
        "status": "idle",
        "progress": 0,
        "message": "SYSTEM WAITING FOR DOCUMENT.",
        "lines": ["SYSTEM WAITING FOR DOCUMENT."],
        "result": {}
    }

    try:
        SCAN_STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SCAN_STATUS_FILE, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2, ensure_ascii=False)
        return jsonify({"ok": True})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


# ============================================================
# STARTUP
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("FREEING THE PARROT")
    print("INTERFACE SERVER")
    print("=" * 60)
    print("[ENGINE] Navarasa engine loaded.")
    print(f"[DATABASE] SQLite: {DB_FILE}")
    print("[CHAT] Validation gate: ONLINE")
    print("[CHAT] Fast-relief gate: ONLINE")
    print("[CHAT] Socratic engine: ONLINE")
    print("[GLITCH] Answer-count escalation: ONLINE")
    print("[GLITCH] Answer-count escalation: ONLINE")
    print("[TERMINATION] User-controlled shutdown: ONLINE")
    print("[PROFANITY] Expletive detection: ONLINE")
    changelog_path = BASE_DIR / "changelog.md"
    if changelog_path.exists():
        print(f"[CHANGELOG] Loaded: {changelog_path}")
    else:
        print("[CHANGELOG] Not found in installation root; endpoint will check beside server file.")

    if PRINTER_NAME:
        print(f"[PRINTER] Configured: {PRINTER_NAME}")
    else:
        print("[PRINTER] Development mode.")
        print("[PRINTER] Receipts will be saved locally.")

    ensure_chat_table()

    print(f"[INTERFACE] http://localhost:{PORT}")
    print("=" * 60)

    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False
    )




