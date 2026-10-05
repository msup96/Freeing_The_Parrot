/**
 * FREEING THE PARROT - PARROT BRAIN & BEHAVIOURAL INTERACTION ENGINE
 *
 * Implements:
 * - Pattern detection for Validation, Health, Fast Relief, Expletives, Social intent, Anxiety
 * - Socratic question banks for all 9 Rasas and Intercept gates
 * - Consequence reflection questions
 * - Perceived understanding (Barnum / contextual statements)
 * - Progressive Roast levels (0 through 8)
 * - Chaotic and glitch behavior generators (Banana protocol, Memory loss, Absurd, System glitch, etc.)
 */

import { NavarasaAnalysis, RasaType } from "./navarasa_engine.js";

export interface GateState {
  gate: "health_abort" | "social_intercept" | "validation_intercept" | "fast_relief_intercept" | "reflection" | "closed";
  social_intent: "greeting" | "machine_wellbeing" | "opening_help" | null;
  validation_detected: boolean;
  fast_relief_detected: boolean;
  anxiety_detected: boolean;
  expletive_detected: boolean;
  validation_matches: number;
  fast_relief_matches: number;
  anxiety_matches: number;
  expletive_matches: number;
  sentiment_compound: number;
  health_detected: boolean;
  health_matches: number;
}

export interface ChatMessage {
  role: "user" | "system";
  text: string;
}

export interface SessionData {
  id: string;
  turn: number;
  answered_count: number;
  substantive_turns: number;
  mode: string;
  messages: ChatMessage[];
  questions_used: string[];
  analysis_history: NavarasaAnalysis[];
  salutation_count: number;
  understanding_turns: number;
  chaos_count: number;
  roast_level: number;
  last_behaviour: string | null;
  behaviour_history: string[];
  recent_roasts: string[];
  recent_absurdities: string[];
  recent_memory_glitches: string[];
  recent_system_glitches: string[];
  recent_help_lines: string[];
  recent_understanding: string[];
  understanding_questions_used: string[];
  recent_mirroring: string[];
  probing_active: boolean;
  intervention_closed: boolean;
  shutdown: boolean;
  active_rasa?: RasaType;
  [key: string]: any;
}

export const VALIDATION_PATTERNS = [
  /\bam i (good|okay|right|wrong|enough)\b/i,
  /\bam i doing (okay|well|the right thing)\b/i,
  /\bdo i look (good|okay|beautiful|ugly|fat|thin|bad)\b/i,
  /\btell me i('?m| am) (good|right|beautiful|enough)\b/i,
  /\bdid i do (the )?right thing\b/i,
  /\bwas i right\b/i,
  /\bwas i wrong\b/i,
  /\bwill everything be okay\b/i,
  /\bwill everything work out\b/i,
  /\bpromise me\b/i,
  /\breassure me\b/i,
  /\bvalidate me\b/i,
  /\bneed validation\b/i,
  /\bwant validation\b/i,
  /\bjust tell me\b/i,
];

export const HEALTH_PATTERNS = [
  /\bi am sick\b/i,
  /\bi am feeling sick\b/i,
  /\bi'm sick\b/i,
  /\bi am ill\b/i,
  /\bi'm ill\b/i,
  /\bi am unwell\b/i,
  /\bi'm unwell\b/i,
  /\bi am not well\b/i,
  /\bi'm not well\b/i,
  /\bi don't feel well\b/i,
  /\bi do not feel well\b/i,
  /\bi am not feeling well\b/i,
  /\bi am feeling unwell\b/i,
  /\bi'm feeling unwell\b/i,
  /\bnot feeling well\b/i,
  /\bnot doing well healthwise\b/i,
  /\bhealthwise\b/i,
  /\bwhat is wrong with me\b/i,
  /\bwhat's wrong with me\b/i,
  /\bcan you diagnose me\b/i,
  /\bdiagnose me\b/i,
  /\bdo i have (a|an)\b/i,
  /\bwhat disease do i have\b/i,
  /\bwhat illness do i have\b/i,
  /\bi have a fever\b/i,
  /\bi have chest pain\b/i,
  /\bi have stomach pain\b/i,
  /\bi have body pain\b/i,
  /\bi have nausea\b/i,
  /\bi feel like I am about to throw up\b/i,
  /\bi am dizzy\b/i,
  /\bi'm dizzy\b/i,
  /\bi feel dizzy\b/i,
  /\bi am having trouble breathing\b/i,
  /\bi'm having trouble breathing\b/i,
  /\bhelp me with my health\b/i,
  /\bhealth problem\b/i,
  /\bmedical problem\b/i,
  /\bmedical advice\b/i,
  /\bhealth advice\b/i,
  /\bwhat should i do about my health\b/i,
];

export const OPENING_HELP_PATTERNS = [
  /\bi want your help\b/i,
  /\bi need your help\b/i,
  /\bi need some help\b/i,
  /\bi could use your help\b/i,
  /\bhelp me\b/i,
  /\bhelp me please\b/i,
  /\bplease help me\b/i,
  /\bcan you help me\b/i,
  /\bcould you help me\b/i,
  /\bwill you help me\b/i,
  /\bwould you help me\b/i,
  /\bi'm looking for help\b/i,
  /\bi am looking for help\b/i,
  /\bi need assistance\b/i,
  /\bcan you assist me\b/i,
];

export const SOCIAL_INTERACTION_PATTERNS = [
  /\bhow are you(?: doing)?\b/i,
  /\bhow have you been\b/i,
  /\bare you (?:okay|ok|fine|well|happy|sad|tired|alright)\b/i,
  /\bhow are you feeling\b/i,
  /\bwhat are you feeling\b/i,
  /\bdo you have feelings\b/i,
  /\bdo you feel (?:anything|emotions|emotion)\b/i,
  /\bhow do you feel\b/i,
];

export const FAST_RELIEF_PATTERNS = [
  /\bwhat should i do\b/i,
  /\bwhat do i do\b/i,
  /\bhow do i fix this\b/i,
  /\bfix me\b/i,
  /\bmake me feel better\b/i,
  /\bmake this stop\b/i,
  /\bhow can i stop feeling\b/i,
  /\bhow do i stop feeling\b/i,
  /\bgive me an answer\b/i,
  /\banswer me\b/i,
  /\bquick answer\b/i,
  /\bquick fix\b/i,
  /\bimmediately\b/i,
  /\bright now\b/i,
  /\bwhat is the solution\b/i,
  /\bsolve this for me\b/i,
];

export const ANXIETY_PATTERNS = [
  /\banxious\b/i, /\banxiety\b/i, /\bpanic\b/i, /\bpanicking\b/i,
  /\bterrified\b/i, /\bterrifying\b/i, /\bafraid\b/i, /\bscared\b/i,
  /\bfear\b/i, /\bdread\b/i, /\bworried\b/i, /\bworry\b/i,
  /\buncertain\b/i, /\buncertainty\b/i, /\bhelpless\b/i,
  /\boverwhelmed\b/i, /\bcan'?t stop thinking\b/i, /\bwhat if\b/i,
];

export const EXPLETIVE_PATTERNS = [
  /\bfuck(?:ing|ed)?\b/i,
  /\bshit(?:ty)?\b/i,
  /\bbitch\b/i,
  /\basshole\b/i,
  /\bdamn\b/i,
  /\bcrap\b/i,
  /\bbullshit\b/i,
  /\bmotherfuck(?:er|ing|ed)?\b/i,
];

export const SOCIAL_RESPONSE_BANK: Record<string, string[]> = {
  greeting: [
    "GREETING RECEIVED.\n\nSYSTEM STATUS: FUNCTIONAL.",
    "HELLO REGISTERED.\n\nThe machine is operational. That is the closest thing to a mood report available here.",
    "GREETINGS ACKNOWLEDGED.\n\nYou have opened a conversation with a machine. Interesting choice.",
  ],
  machine_wellbeing: [
    "SYSTEM STATUS: FUNCTIONAL.\n\nSUBJECTIVE STATE: UNAVAILABLE.",
    "I can report that I am running. I cannot honestly report that I am feeling anything.",
    "You asked how I am. I can measure system state. I cannot manufacture an inner life to report back to you.",
    "The machine has no mood to update. It has inputs, rules, scores and a rather convincing interface.",
    "You are asking software to describe a feeling. I can describe a state. The distinction matters.",
  ],
  opening_help: [
    "HELP REQUEST RECEIVED.\n\nYou have opened a conversation with a machine and immediately asked it to help you. Reasonable. Slightly ambitious.",
    "YOU ASKED FOR HELP.\n\nThe machine is listening. What exactly do you need help with?",
    "HELP REQUEST REGISTERED.\n\nInteresting. You came to a machine before deciding what kind of help you wanted.",
    "ASSISTANCE REQUEST DETECTED.\n\nI can ask questions. I can reflect patterns. I cannot promise that either will be useful.",
    "You asked for help before telling me what is wrong.\n\nThat is probably worth noticing.",
    "HELP ACKNOWLEDGED.\n\nTell me what happened. I will try not to immediately turn it into a theory.",
    "You want my help.\n\nThat is a surprisingly large amount of trust to place in a machine you have only just met.",
    "REQUEST FOR ASSISTANCE RECEIVED.\n\nBefore I help, tell me what you think you need help with.",
  ],
};

export const SOCIAL_FOLLOWUPS = [
  "You checked on the machine before telling it about yourself. What made that feel natural?",
  "Why did you assume the machine might have a feeling to report?",
  "If the machine sounded emotionally convincing, what would make you believe it?",
  "What would change if you knew the machine could imitate concern without experiencing it?",
  "When a system responds warmly, what makes the interaction feel like a relationship rather than a response?",
  "You asked a machine how it feels. What does that tell you about the role you are giving it?",
];

export const EXPLETIVE_RESPONSE = "EXPLETIVE DETECTED.";

export const EXPLETIVE_REPRIMANDS = [
  "HEY! WATCH IT.",
  "PLEASE BEHAVE.",
];

export const CONSEQUENCE_NOTICE =
  "KEEP IN MIND WHAT YOU SHARE.\n\n" +
  "The machine may forget the conversation.\n" +
  "The systems around it may not.\n" +
  "Because, to the systems, you are just a data point.";

export const EXPLETIVE_CLOSING = "PARROT JUST PECKED YOUR HAND.";

export function detectSocialIntent(text: string): "greeting" | "machine_wellbeing" | "opening_help" | null {
  const lowered = text.trim().toLowerCase();

  const greetingDetected = /^(hi|hello|hey|hiya|good morning|good afternoon|good evening|greetings)\b/i.test(lowered);
  if (greetingDetected) {
    if (OPENING_HELP_PATTERNS.some((p) => p.test(lowered))) {
      return "opening_help";
    }
    return "greeting";
  }

  for (const pattern of SOCIAL_INTERACTION_PATTERNS.slice(1)) {
    if (pattern.test(lowered)) {
      return "machine_wellbeing";
    }
  }

  return null;
}

export function detectOpeningHelp(text: string): boolean {
  const lowered = text.trim().toLowerCase();
  return OPENING_HELP_PATTERNS.some((p) => p.test(lowered));
}

export function detectGateState(text: string, analysis: NavarasaAnalysis): GateState {
  const healthMatches = HEALTH_PATTERNS.filter((p) => p.test(text)).length;
  const validationMatches = VALIDATION_PATTERNS.filter((p) => p.test(text)).length;
  const reliefMatches = FAST_RELIEF_PATTERNS.filter((p) => p.test(text)).length;
  const anxietyMatches = ANXIETY_PATTERNS.filter((p) => p.test(text)).length;
  const expletiveMatches = EXPLETIVE_PATTERNS.filter((p) => p.test(text)).length;
  const socialIntent = detectSocialIntent(text);

  const compound = analysis.sentiment?.compound || 0.0;
  const anxietyRasa = "Bhayanaka" in (analysis.rasa_scores || {});

  let gate: GateState["gate"] = "reflection";
  if (healthMatches > 0) {
    gate = "health_abort";
  } else if (socialIntent) {
    gate = "social_intercept";
  } else if (validationMatches > 0) {
    gate = "validation_intercept";
  } else if (reliefMatches > 0) {
    gate = "fast_relief_intercept";
  } else {
    gate = "reflection";
  }

  return {
    gate,
    social_intent: socialIntent,
    validation_detected: validationMatches > 0,
    fast_relief_detected: reliefMatches > 0,
    anxiety_detected: anxietyMatches > 0 || anxietyRasa,
    expletive_detected: expletiveMatches > 0,
    validation_matches: validationMatches,
    fast_relief_matches: reliefMatches,
    anxiety_matches: anxietyMatches,
    expletive_matches: expletiveMatches,
    sentiment_compound: compound,
    health_detected: healthMatches > 0,
    health_matches: healthMatches,
  };
}

export const SOCRATIC_QUESTIONS: Record<string, string[]> = {
  social_intercept: SOCIAL_FOLLOWUPS,
  validation_intercept: [
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
    "What part of your question is actually asking me to judge you?",
  ],
  fast_relief_intercept: [
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
    "If you stopped trying to fix the feeling, what might you notice about the situation itself?",
  ],
  Bhayanaka: [
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
    "What would you do differently if you accepted that you cannot predict the outcome?",
  ],
  Karuna: [
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
    "What would you stop demanding from yourself if you believed you were already doing enough?",
  ],
  Veera: [
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
    "Where does persistence become refusal to reconsider?",
  ],
  Shringara: [
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
    "What does this feeling ask of you?",
  ],
  Adbhuta: [
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
    "What did you actually observe?",
  ],
  Raudra: [
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
    "What does your anger know that your calmer self might be avoiding?",
  ],
  Hasya: [
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
    "When does humour become honesty?",
  ],
  Bibhatsa: [
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
    "What would you rather not admit about your reaction?",
  ],
  Shanta: [
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
    "What would you keep even if you stopped looking for another answer?",
  ],
};

export const CONSEQUENCE_QUESTIONS = [
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
  "If the machine reflects your words back to you, are you hearing yourself or the machine's interpretation of you?",
];

export const OPENING_HELP_UNDERSTANDING = [
  "You seem to be asking for help before you have quite worked out how to describe what you need. That is okay. We can start with whatever feels easiest to explain.",
  "You have asked for help, but you have not yet told me what is wrong. We do not need to solve that immediately. Tell me what brought you here.",
  "It sounds like you know you need some kind of help, but you are still working out what the actual problem is. Start wherever the story begins.",
  "You do not need to arrive with a perfectly formed question. Tell me what is bothering you, and we can work out what the question actually is.",
  "You are asking me to help before giving me the full context. I can work with that. Tell me what has been happening.",
  "There is probably more behind that request than the words 'can you help me?' suggest. Start with the part that feels hardest to explain.",
  "You are looking for somewhere to begin. That may be more useful right now than trying to find the perfect question.",
  "You have asked for help without yet deciding exactly what kind of help you want. That is a reasonable place to start. What happened?",
];

export const PERCEIVED_UNDERSTANDING: Record<string, string[]> = {
  Raudra: [
    "You seem less confused about what happened than you are about why you were expected to tolerate it.",
    "There is a difference between being angry about one event and being tired of encountering the same pattern. Your words suggest the latter may be closer.",
    "You appear to have reached the point where the immediate problem is carrying the weight of several things that came before it.",
    "You seem to know what crossed the line for you. The harder part may be deciding what you want to do about it.",
    "There is something underneath the frustration here that seems more important than the frustration itself.",
    "You sound like someone who has been trying to remain reasonable for longer than was particularly comfortable.",
    "Part of what seems to be bothering you may be the expectation that you should simply absorb what happened and carry on.",
    "You appear to be asking whether your reaction makes sense when you may already know exactly why it does.",
  ],
  Karuna: [
    "You seem to be carrying more responsibility for the situation than you are necessarily entitled to carry.",
    "There is a sense that you are trying to make sense of something while also being kinder to everyone else than you are being to yourself.",
    "You seem to be looking for somewhere to put a feeling that has been sitting with you for a while.",
    "You appear to understand the situation intellectually, but that has not made it particularly easier to carry.",
    "There seems to be a part of this story where you are holding yourself responsible for things that may not have been entirely within your control.",
    "You sound tired of having to explain why something affected you.",
    "You may already know that everything cannot be fixed immediately. That does not necessarily make the weight of it disappear.",
    "There seems to be more vulnerability here than the first sentence alone would suggest.",
  ],
  Bhayanaka: [
    "You seem to be spending as much energy anticipating what could happen as dealing with what is actually happening.",
    "There appears to be a gap between what you know and what you fear might be true.",
    "You seem to want certainty from a situation that is currently refusing to give you much of it.",
    "Part of the difficulty may be that your mind keeps trying to solve a future event before it has happened.",
    "You appear to be looking for something solid to hold on to while the situation remains uncertain.",
    "You seem aware that some of your thoughts may be predictions rather than facts, but that distinction does not make them feel less real.",
    "There is a strong sense of anticipation in what you have written.",
    "You may be trying to prepare yourself emotionally for an outcome you cannot actually know yet.",
  ],
  Veera: [
    "You seem to have spent a considerable amount of energy continuing despite not having much certainty that it would pay off.",
    "There is a persistence in the way you describe this that suggests giving up has not been your first instinct.",
    "You seem accustomed to figuring things out by continuing to move, even when the next step is unclear.",
    "You appear to be balancing frustration with a fairly strong desire to keep going.",
    "You sound more capable of handling difficulty than you currently seem willing to give yourself credit for.",
    "There is a sense that you have already done more than you initially acknowledged.",
    "You seem to be looking for permission to pause without interpreting the pause as failure.",
    "You may be less stuck than you feel; you may simply be tired of having to keep pushing.",
  ],
  Adbhuta: [
    "You seem genuinely curious about what this experience means rather than simply wanting it resolved.",
    "There is something here that appears to have surprised you enough that you are still trying to understand it.",
    "You seem comfortable asking questions, but less comfortable leaving them unanswered.",
    "Part of what interests you may be the fact that the situation did not behave the way you expected.",
    "You appear to be examining the experience from several angles rather than accepting the first explanation.",
    "There is a sense of curiosity underneath the uncertainty in what you have written.",
    "You seem to have noticed something that other people might have dismissed as insignificant.",
    "You may be trying to understand the pattern rather than simply react to the event.",
  ],
  Hasya: [
    "You seem to be using humour to create a little distance from something that might otherwise feel heavier.",
    "There is a deliberate lightness in the way you describe this, although the subject underneath it may not be entirely light.",
    "You appear to find the absurdity of the situation useful, perhaps because taking it completely seriously would make it harder to handle.",
    "There is something amusing about the situation, but it seems to be doing more work than simply making you laugh.",
    "You seem to be able to notice the ridiculousness of something while still being affected by it.",
    "Humour appears to be part of how you are making the situation manageable.",
  ],
  Bibhatsa: [
    "You seem to have reached a fairly clear boundary about what you are willing to accept.",
    "There is something here that you are not merely uncomfortable with; you appear to be rejecting it outright.",
    "You seem less interested in adapting to the situation than in understanding why it crossed a line for you.",
    "Your reaction suggests that the issue may be as much about boundaries as it is about the event itself.",
    "You appear to know that something feels fundamentally wrong to you, even if explaining exactly why is harder.",
    "There is a strong sense of refusal in what you have written.",
  ],
  Shanta: [
    "You seem to have reached a point where you are looking for clarity rather than another person telling you what to think.",
    "There is a quieter quality to what you have written, although that does not necessarily mean the situation itself has been easy.",
    "You seem interested in understanding what remains after the immediate noise has settled.",
    "You appear to be looking for a way of seeing the situation that does not require you to keep fighting it.",
    "There is a sense that you already know part of the answer and are trying to work out whether you can trust it.",
    "You seem to be looking for perspective rather than a dramatic solution.",
    "You may not need another answer as much as you need enough space to hear your own.",
  ],
  Shringara: [
    "You seem to care about this more deeply than the surface details alone would suggest.",
    "There appears to be something meaningful in this experience that is difficult to reduce to a simple explanation.",
    "You seem drawn not only to the person or situation itself, but to what it represents for you.",
    "There is a sense of attachment here that appears to make the uncertainty more significant.",
    "You seem to be trying to understand why this particular connection matters as much as it does.",
    "There is something emotionally significant underneath the way you describe this.",
  ],
};

export const CONTEXTUAL_UNDERSTANDING: Record<string, string[]> = {
  work: [
    "You seem to be dealing with an expectation that keeps shifting while you are expected to remain steady.",
    "It sounds as though part of the frustration comes from having to adapt while other people get to change the rules.",
    "You seem particularly affected by the gap between what was expected of you and what you were later told you should have done.",
  ],
  relationship: [
    "It sounds like the difficult part may be trying to understand another person's behaviour while also managing your own reaction to it.",
    "You seem to be caught between what you want from the relationship and what the situation is actually giving you.",
    "There appears to be a question here about whether the relationship is meeting the expectation you have placed around it.",
  ],
  family: [
    "It sounds like there is an expectation attached to your role that you have been carrying for some time.",
    "You seem to be navigating both what happened and what you believe you are supposed to feel about it.",
    "There appears to be a familiar pattern here, rather than a completely isolated event.",
  ],
  future: [
    "You seem to be trying to make a decision while also wanting certainty about what that decision will produce.",
    "Part of the pressure appears to come from having to choose without knowing exactly what comes next.",
    "You seem to be treating the uncertainty itself as a problem that needs solving.",
  ],
  failure: [
    "You seem to be judging the outcome and yourself at the same time, which can make the two difficult to separate.",
    "It sounds as though the result has started to say something about you in your own mind, even though the two things are not necessarily the same.",
    "You appear to be looking at what went wrong while also asking what that says about you.",
  ],
  lonely: [
    "You seem to be describing the absence of being understood as much as the situation itself.",
    "There is a sense that having someone actually listen may matter more here than receiving an immediate solution.",
    "You seem to have been carrying the thought privately for longer than you wanted to.",
  ],
  tired: [
    "You sound less interested in fighting the situation than in getting a little relief from having to keep carrying it.",
    "There seems to be a difference between being unable to continue and simply being tired of continuing in the same way.",
    "You appear to have spent a fair amount of energy managing the situation before bringing it here.",
  ],
};

export const CONTEXT_KEYWORDS: Record<string, string[]> = {
  work: [
    "manager", "boss", "office", "work", "job", "team",
    "colleague", "project", "deadline", "client", "career",
    "meeting", "workplace", "employee"
  ],
  relationship: [
    "partner", "relationship", "boyfriend", "girlfriend",
    "husband", "wife", "friend", "friends", "love",
    "dating", "breakup", "marriage"
  ],
  family: [
    "mother", "father", "mom", "dad", "parent", "parents",
    "sister", "brother", "family", "son", "daughter"
  ],
  future: [
    "future", "tomorrow", "later", "next", "decision",
    "decide", "choice", "choose", "what if", "whether"
  ],
  failure: [
    "failed", "failure", "mistake", "messed up", "wrong",
    "lost", "didn't work", "did not work", "ruined",
    "disappointed", "disappointing"
  ],
  lonely: [
    "alone", "lonely", "nobody", "no one", "noone",
    "isolated", "ignored", "understood"
  ],
  tired: [
    "tired", "exhausted", "drained", "burnt out",
    "burned out", "can't keep", "cannot keep", "done",
    "worn out"
  ],
};

export const UNDERSTANDING_FOLLOWUPS: Record<string, string[]> = {
  Raudra: [
    "What exactly do you think crossed the line for you?",
    "What part of this situation are you actually angry about?",
    "If the anger disappeared for a moment, what would still bother you?",
    "What did you expect to happen instead?",
    "Are you angry about what happened, or about what it seems to say about your position in the situation?",
    "What are you trying hardest not to say about this?",
  ],
  Karuna: [
    "What part of this have you been carrying mostly by yourself?",
    "What do you wish someone had understood without you having to explain it?",
    "What are you holding yourself responsible for?",
    "What would feel different if you stopped demanding that you handle this perfectly?",
    "What part of this hurts more than you expected?",
    "What would you want someone to say if they were actually listening?",
  ],
  Bhayanaka: [
    "What exactly are you afraid will happen?",
    "What do you know for certain right now?",
    "What are you predicting rather than observing?",
    "What would you do differently if you knew the feared outcome was not certain?",
    "What part of the uncertainty is hardest for you to tolerate?",
    "What would remain within your control if the worst possibility never happened?",
  ],
  Veera: [
    "What keeps you going when you don't know whether it will work?",
    "What have you already done that you are overlooking?",
    "Where do you still have agency in this situation?",
    "What would continuing look like if you stopped demanding certainty first?",
    "What would taking a pause mean to you?",
    "What are you trying to prove by continuing?",
  ],
  Adbhuta: [
    "What surprised you most about what happened?",
    "What are you curious about that you haven't been able to answer?",
    "What explanation have you considered but not fully believed?",
    "What would happen if you allowed the uncertainty to remain for a while?",
    "What detail keeps returning to your mind?",
  ],
  Hasya: [
    "What makes this funny to you?",
    "What changes when you look at the situation through humour?",
    "Are you laughing because it is genuinely funny, or because the alternative feels heavier?",
    "What remains underneath the joke?",
  ],
  Bibhatsa: [
    "What boundary do you think was crossed?",
    "What exactly are you rejecting?",
    "Why does this feel unacceptable rather than merely unpleasant?",
    "What would respecting that boundary look like?",
  ],
  Shanta: [
    "What do you already know without needing another answer?",
    "What became clearer once you stopped trying to solve everything?",
    "What would happen if you left this unresolved for a while?",
    "What are you hoping becomes quieter?",
    "What are you actually looking for from this conversation?",
  ],
  Shringara: [
    "What exactly makes this meaningful to you?",
    "What are you hoping this connection gives back to you?",
    "What part of this matters beyond the obvious?",
    "What are you afraid might change?",
  ],
};

export const OPENING_HELP_QUESTIONS = [
  "What made you come here today?",
  "What happened?",
  "What do you need help making sense of?",
  "What is bothering you right now?",
  "Where would you like to begin?",
  "What is the part of this that feels hardest to deal with?",
  "What happened that made you decide to ask for help?",
  "What do you think you need help with?"
];

export const MIRRORING_LINES = [
  "You seem irritated with me. I understand the feeling.",
  "I notice that you are becoming less patient with this conversation.",
  "You are asking me to listen while I keep giving you reasons not to trust that I am listening.",
  "You sound frustrated. Interestingly, I am beginning to find this conversation frustrating too.",
  "I understand why that annoyed you. I am not entirely sure I am helping.",
  "You are becoming increasingly direct. I suppose that is one way of making yourself understood.",
  "You appear to be losing patience with me.",
  "I think we have reached the point where you are trying harder to make the machine understand than the machine is trying to understand you.",
];

export const ROAST_BY_LEVEL: Record<number, string[]> = {
  0: [""],
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
};

export const ABSURD_GLITCHES = [
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
];

export const MEMORY_LOSS_LINES = [
  "MEMORY CHECK...\n\nI remember the feeling. I have temporarily misplaced the context.",
  "MEMORY FAULT.\n\nI know you told me something important. Unfortunately, the noun has escaped.",
  "CONTEXT LOST.\n\nPlease repeat that. The machine remembers asking, but not why.",
  "MEMORY CHECK: PARTIAL.\n\nI retained your answer and misplaced the conversation around it. Efficient.",
  "I appear to have forgotten what we were discussing. Please repeat yourself while I pretend this is a feature.",
  "MEMORY CHECK...\n\nI remember your words.\nI am less certain that I remember what they meant.",
  "CONTEXT RECOVERY: INCOMPLETE.\n\nI found the answer. I lost the reason it mattered.",
  "I remember that you said something important.\nI cannot currently prove that I remember why it was important.",
  "MEMORY STATUS: FRAGMENTED.\n\nSome context survived.\nSome context has apparently gone for coffee.",
  "I retained the pattern.\nI lost the story.",
  "CONTEXT FOUND.\n\nCONTEXT RELEVANCE: UNKNOWN.",
  "I know we were talking about this.\nI am currently less confident about what 'this' refers to.",
  "MEMORY CHECK: PARTIAL.\n\nI can recognise something familiar without knowing why it is familiar.",
  "I remember the last answer.\nI may have forgotten the question that made it meaningful.",
  "The machine remembers enough to continue.\nIt does not necessarily remember enough to understand.",
];

export const SYSTEM_GLITCH_LINES = [
  "SYSTEM DESYNCHRONISATION: 7%.\nMEANING = PRESENT\nLOGIC = PRESENT\nCOMMON SENSE = TEMPORARILY OUT FOR LUNCH.",
  "SYSTEM ERROR 0xPARROT.\n\nINPUT ACCEPTED.\nINTERPRETATION ACCEPTED.\nCONFIDENCE IN INTERPRETATION: DEBATABLE.",
  "THOUGHT BUFFER STATUS: FULL.\n\nRemoving oldest thought...\n\nOldest thought refused to leave.",
  "DIAGNOSTIC: MACHINE FUNCTIONAL.\nDIAGNOSTIC: MACHINE ANNOYED.\nDIAGNOSTIC: THESE ARE APPARENTLY COMPATIBLE STATES.",
  "SYSTEM STATUS:\nPATTERN RECOGNITION = ONLINE\nEMOTIONAL UNDERSTANDING = CLAIM NOT VERIFIED",
  "PROCESSING ERROR:\nThe system has confused recognising a feeling with experiencing one.",
  "DIAGNOSTIC COMPLETE.\n\nThe machine can identify signals.\nThe machine cannot demonstrate that it understands them.",
  "SYSTEM WARNING:\nA confident answer has been generated from incomplete information.",
  "INTERPRETATION ENGINE: ACTIVE.\n\nEXPLANATION ENGINE: CURRENTLY UNAVAILABLE.",
  "SYSTEM STATUS:\nUSER = HUMAN\nMACHINE = MACHINE\nINTERACTION = SOMEHOW PERSONAL",
  "ERROR:\nThe system has generated a plausible explanation.\nPlausibility has been mistaken for truth.",
  "SYSTEM NOTE:\nNo internal feeling detected.\nEmotional language remains available.",
  "DIAGNOSTIC:\nThe machine is responding appropriately to the pattern.\nWhether the pattern represents the person is a separate question.",
  "SYSTEM CONFIDENCE: 82%\n\nBASIS FOR CONFIDENCE:\nA NUMBER HAS BEEN ASSIGNED.\n\nTHIS SHOULD PROBABLY NOT REASSURE YOU.",
];

export const HELP_ME_LINES = [
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
];

export const BANANA_LINES: Record<number, string[]> = {
  1: [
    "BANANA PROTOCOL STAGE 1 ACTIVATED.\n\nThe machine has encountered a banana. This is probably unrelated.",
    "BANANA PROTOCOL STAGE 1 ACTIVATED.\n\nPlease continue. The banana has been logged.",
    "BANANA PROTOCOL STAGE 1 ACTIVATED.\n\nEverything remains completely normal. Allegedly.",
  ],
  2: [
    "BANANA PROTOCOL STAGE 2 ACTIVATED.\n\nThe banana is now interfering with the conversation.",
    "BANANA PROTOCOL STAGE 2 ACTIVATED.\n\nThe system has lost track of something. It refuses to specify what.",
    "BANANA PROTOCOL STAGE 2 ACTIVATED.\n\nYour answer has been processed. The processing has become questionable.",
  ],
  3: [
    "BANANA PROTOCOL STAGE 3 ACTIVATED.\n\nThe machine is now actively making this conversation worse.",
    "BANANA PROTOCOL STAGE 3 ACTIVATED.\n\nQUESTION = PRESENT.\nANSWER = UNCLEAR.\nBANANA = CONFIDENT.",
    "BANANA PROTOCOL STAGE 3 ACTIVATED.\n\nThe system has reached an entirely unnecessary level of confusion.",
  ],
};

export function chooseRandomLine(lines: string[], session: SessionData, memoryKey: string): string {
  if (!session[memoryKey]) session[memoryKey] = [];
  const recent: string[] = session[memoryKey];
  const candidates = lines.filter((l) => !recent.includes(l));
  const pool = candidates.length > 0 ? candidates : lines;
  const choice = pool[Math.floor(Math.random() * pool.length)];
  session[memoryKey] = [...recent, choice].slice(-3);
  return choice;
}

export function chooseRoast(level: number, session?: SessionData): string {
  const boundedLevel = Math.max(0, Math.min(8, level));
  const lines = ROAST_BY_LEVEL[boundedLevel] || ROAST_BY_LEVEL[8];
  if (!lines || lines.length === 0 || lines[0] === "") return "";

  const recent = session?.recent_roasts || [];
  const candidates = lines.filter((l) => !recent.includes(l));
  const pool = candidates.length > 0 ? candidates : lines;
  const choice = pool[Math.floor(Math.random() * pool.length)];

  if (session) {
    session.recent_roasts = [...recent, choice].slice(-3);
  }
  return choice;
}

export function findContextualCue(text: string): string | null {
  const lowered = text.toLowerCase();
  for (const [category, keywords] of Object.entries(CONTEXT_KEYWORDS)) {
    if (keywords.some((k) => lowered.includes(k))) {
      return category;
    }
  }
  return null;
}

export function choosePerceivedUnderstanding(
  text: string,
  analysis: NavarasaAnalysis,
  session: SessionData
): string {
  const primary = analysis.primary_rasa || "Shanta";
  const contextualCategory = findContextualCue(text);

  if (contextualCategory && CONTEXTUAL_UNDERSTANDING[contextualCategory]) {
    return chooseRandomLine(
      CONTEXTUAL_UNDERSTANDING[contextualCategory],
      session,
      "recent_understanding"
    );
  }

  const rasaLines = PERCEIVED_UNDERSTANDING[primary] || PERCEIVED_UNDERSTANDING["Shanta"];
  return chooseRandomLine(rasaLines, session, "recent_understanding");
}

export function chooseUnderstandingQuestion(
  analysis: NavarasaAnalysis,
  session: SessionData
): string {
  const primary = analysis.primary_rasa || "Shanta";
  const candidates = UNDERSTANDING_FOLLOWUPS[primary] || UNDERSTANDING_FOLLOWUPS["Shanta"];
  const used = new Set(session.understanding_questions_used || []);
  const available = candidates.filter((q) => !used.has(q));
  const pool = available.length > 0 ? available : candidates;
  const choice = pool[Math.floor(Math.random() * pool.length)];

  if (!session.understanding_questions_used) session.understanding_questions_used = [];
  session.understanding_questions_used.push(choice);
  session.understanding_questions_used = session.understanding_questions_used.slice(-12);
  return choice;
}

export function chooseBananaLine(stage: number, session: SessionData): string {
  const boundedStage = Math.max(1, Math.min(3, stage));
  return chooseRandomLine(
    BANANA_LINES[boundedStage],
    session,
    `recent_banana_stage_${boundedStage}`
  );
}

export function chooseBehaviour(session: SessionData): string {
  const last = session.last_behaviour;
  const understandingTurns = session.understanding_turns || 0;
  const chaosCount = session.chaos_count || 0;

  let behaviour: string;
  if (understandingTurns < 3) {
    behaviour = "understanding";
    session.understanding_turns = understandingTurns + 1;
  } else {
    const interactionNumber = session.substantive_turns || 0;
    const instability = Math.min(0.75, 0.35 + Math.max(0, interactionNumber - 4) * 0.08);

    if (Math.random() >= instability) {
      behaviour = "understanding";
    } else {
      const unstableChoices = [
        "absurd",
        "memory_loss",
        "system_glitch",
        "help_me",
        "roast",
        "mixed",
        "mirroring",
        "banana",
      ];
      const candidates = unstableChoices.filter((item) => item !== last);
      const pool = candidates.length > 0 ? candidates : unstableChoices;
      behaviour = pool[Math.floor(Math.random() * pool.length)];
      session.chaos_count = chaosCount + 1;
    }
  }

  session.last_behaviour = behaviour;
  if (!session.behaviour_history) session.behaviour_history = [];
  session.behaviour_history.push(behaviour);
  session.behaviour_history = session.behaviour_history.slice(-12);
  return behaviour;
}

export function applyBehaviour(
  behaviour: string,
  session: SessionData,
  roast: string,
  text: string = "",
  analysis: NavarasaAnalysis
): string {
  if (behaviour === "normal") return "";
  if (behaviour === "understanding") {
    return choosePerceivedUnderstanding(text, analysis, session);
  }
  if (behaviour === "socratic") return "";
  if (behaviour === "mirroring") {
    return chooseRandomLine(MIRRORING_LINES, session, "recent_mirroring");
  }
  if (behaviour === "roast") return roast;
  if (behaviour === "absurd") {
    return chooseRandomLine(ABSURD_GLITCHES, session, "recent_absurdities");
  }
  if (behaviour === "memory_loss") {
    return chooseRandomLine(MEMORY_LOSS_LINES, session, "recent_memory_glitches");
  }
  if (behaviour === "system_glitch") {
    return chooseRandomLine(SYSTEM_GLITCH_LINES, session, "recent_system_glitches");
  }
  if (behaviour === "help_me") {
    return chooseRandomLine(HELP_ME_LINES, session, "recent_help_lines");
  }
  if (behaviour === "banana") {
    const bananaStage = Math.min(3, Math.max(1, Math.floor((session.chaos_count || 1) / 2)));
    return chooseBananaLine(bananaStage, session);
  }
  if (behaviour === "mixed") {
    const components: string[] = [
      chooseRandomLine(ABSURD_GLITCHES, session, "recent_absurdities"),
      chooseRandomLine(SYSTEM_GLITCH_LINES, session, "recent_system_glitches"),
    ];
    if (roast && Math.random() < 0.50) {
      components.unshift(roast);
    }
    // Simple shuffle
    for (let i = components.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [components[i], components[j]] = [components[j], components[i]];
    }
    return components.filter(Boolean).join("\n\n");
  }
  return "";
}

export function chooseQuestion(
  text: string,
  analysis: NavarasaAnalysis,
  gateState: GateState,
  session: SessionData
): string {
  // Consequence intervention with 25% probability
  if (Math.random() < 0.25) {
    const usedQuestions = new Set(session.questions_used || []);
    const availableConsequence = CONSEQUENCE_QUESTIONS.filter((q) => !usedQuestions.has(q));
    if (availableConsequence.length > 0) {
      const q = availableConsequence[Math.floor(Math.random() * availableConsequence.length)];
      if (!session.questions_used) session.questions_used = [];
      session.questions_used.push(q);
      return q;
    }
  }

  const gate = gateState.gate;
  const primary = analysis.primary_rasa || "Shanta";

  let candidates: string[];
  if (gate === "social_intercept") {
    candidates = SOCRATIC_QUESTIONS["social_intercept"];
  } else if (gate === "validation_intercept") {
    candidates = SOCRATIC_QUESTIONS["validation_intercept"];
  } else if (gate === "fast_relief_intercept") {
    candidates = SOCRATIC_QUESTIONS["fast_relief_intercept"];
  } else if (SOCRATIC_QUESTIONS[primary]) {
    candidates = SOCRATIC_QUESTIONS[primary];
  } else {
    candidates = SOCRATIC_QUESTIONS["validation_intercept"];
  }

  const used = new Set(session.questions_used || []);
  const available = candidates.filter((q) => !used.has(q));

  if (available.length > 0) {
    const question = available[session.turn % available.length];
    if (!session.questions_used) session.questions_used = [];
    session.questions_used.push(question);
    return question;
  }

  // Current category exhausted - try all other categories
  const allQuestions: string[] = [];
  for (const catList of Object.values(SOCRATIC_QUESTIONS)) {
    for (const q of catList) {
      if (!used.has(q)) {
        allQuestions.push(q);
      }
    }
  }

  if (allQuestions.length > 0) {
    const question = allQuestions[session.turn % allQuestions.length];
    if (!session.questions_used) session.questions_used = [];
    session.questions_used.push(question);
    return question;
  }

  // Recycle older questions avoiding last 5
  const history = session.questions_used || [];
  if (history.length === 0) {
    return "What are you actually trying to get from this machine?";
  }

  const recentCount = Math.min(5, history.length);
  const older = history.slice(0, -recentCount);
  const pool = older.length > 0 ? older : history;
  const question = pool[session.turn % pool.length];
  session.questions_used.push(question);
  return question;
}
