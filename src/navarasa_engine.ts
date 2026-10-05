/**
 * FREEING THE PARROT
 * NAVARASA EMOTIONAL INTELLIGENCE ENGINE (TypeScript Port)
 *
 * Implements the 9-Rasa emotional framework with phrase matching,
 * negation detection, intensity modifiers, and sentiment calculation.
 */

export const RASAS = [
  "Shringara",
  "Hasya",
  "Karuna",
  "Raudra",
  "Veera",
  "Bhayanaka",
  "Bibhatsa",
  "Adbhuta",
  "Shanta",
] as const;

export type RasaType = typeof RASAS[number];

export interface EvidenceItem {
  word: string;
  rasa: RasaType;
  confidence: number;
  intensity: number;
  reason: string;
  occurrences: number;
}

export interface SentimentResult {
  positive: number;
  negative: number;
  neutral: number;
  compound: number;
}

export interface NavarasaAnalysis {
  primary_rasa: RasaType;
  rasa_scores: Partial<Record<RasaType, number>>;
  evidence: Partial<Record<RasaType, EvidenceItem[]>>;
  emotional_words: string[];
  analysis_quality: string;
  sentiment: SentimentResult;
  text: string;
}

export const EMOTIONAL_LEXICON: Record<RasaType, { core: Set<string>; phrases: string[] }> = {
  Shringara: {
    core: new Set([
      "love", "loving", "loved", "affection", "affectionate", "adore", "adored", "adoring",
      "attraction", "attracted", "beautiful", "beauty", "romantic", "romance", "passion",
      "passionate", "desire", "cherish", "cherished", "intimate", "intimacy", "tender",
      "tenderness", "fond", "fondness"
    ]),
    phrases: [
      "fall in love", "in love", "deeply in love", "madly in love",
      "love dearly", "love very much", "feel attracted", "feel attraction"
    ],
  },
  Hasya: {
    core: new Set([
      "laugh", "laughed", "laughing", "laughter", "funny", "humor", "humour", "hilarious",
      "amusing", "amused", "joke", "jokes", "joking", "comic", "comedy", "giggle", "giggles",
      "smile", "smiling", "joyful", "playful"
    ]),
    phrases: [
      "made me laugh", "couldn't stop laughing", "cannot stop laughing",
      "burst out laughing", "laugh out loud"
    ],
  },
  Karuna: {
    core: new Set([
      "sad", "sadness", "sorrow", "sorrowful", "grief", "grieving", "lonely", "loneliness",
      "alone", "hurt", "hurting", "heartbroken", "heartbreak", "pain", "painful", "cry",
      "crying", "tears", "regret", "regretful", "loss", "lost", "helpless", "hopeless",
      "despair", "desperate", "miserable", "misery", "mourning", "suffering"
    ]),
    phrases: [
      "feel alone", "feeling alone", "feel lonely", "feeling lonely",
      "broken heart", "brokenhearted", "lost someone", "miss someone",
      "miss them", "in pain", "feel helpless", "feel hopeless"
    ],
  },
  Raudra: {
    core: new Set([
      "angry", "anger", "furious", "fury", "rage", "raging", "hate", "hatred",
      "frustrated", "frustration", "annoyed", "annoyance", "irritated", "irritation",
      "resentful", "resentment", "hostile", "hostility", "outraged", "outrage",
      "enraged", "mad"
    ]),
    phrases: [
      "so angry", "extremely angry", "really angry", "very angry",
      "fed up", "sick of", "can't stand", "cannot stand",
      "lost my temper", "lose my temper"
    ],
  },
  Veera: {
    core: new Set([
      "brave", "bravery", "courage", "courageous", "bold", "determined", "determination",
      "strong", "strength", "resilient", "resilience", "confident", "confidence",
      "fearless", "persistent", "persistence", "persevere", "perseverance", "fight",
      "fighting", "overcome", "victory", "triumph", "empowered", "empowerment"
    ]),
    phrases: [
      "keep going", "face my fear", "face my fears", "stand up for myself",
      "fight back", "never give up", "won't give up", "will not give up",
      "push through", "rise above"
    ],
  },
  Bhayanaka: {
    core: new Set([
      "afraid", "fear", "fearful", "terrified", "terror", "scared", "frightened",
      "fright", "anxious", "anxiety", "panic", "panicked", "dread", "dreadful",
      "horrified", "horror", "nervous", "nervousness", "threat", "threatened",
      "unsafe", "danger", "dangerous", "worry", "worried", "uncertain", "uncertainty"
    ]),
    phrases: [
      "scared to death", "worried about", "afraid of", "terrified of",
      "fear of", "worst case", "worst-case scenario", "feel unsafe", "not safe"
    ],
  },
  Bibhatsa: {
    core: new Set([
      "disgusting", "disgust", "disgusted", "disgustingness", "gross", "repulsive",
      "repulsed", "revolting", "revolt", "nauseating", "nauseated", "vile", "horrible",
      "filthy", "dirty", "sickening", "offensive", "abhorrent", "repugnant", "contempt"
    ]),
    phrases: [
      "absolutely disgusting", "completely disgusting", "makes me sick",
      "sick to my stomach", "turns my stomach", "can't stomach", "cannot stomach"
    ],
  },
  Adbhuta: {
    core: new Set([
      "wonder", "wonderful", "wonderment", "amazed", "amazing", "amazement",
      "astonished", "astonishing", "astonishment", "awe", "awesome", "awestruck",
      "incredible", "incredibly", "curious", "curiosity", "fascinated", "fascinating",
      "discovery", "discover", "discovering", "surprised", "surprise", "unexpected",
      "marvel", "marvelous", "extraordinary", "wow"
    ]),
    phrases: [
      "filled with wonder", "full of wonder", "in awe", "blown away",
      "can't believe", "cannot believe", "mind blown", "mind-blowing", "what a discovery"
    ],
  },
  Shanta: {
    core: new Set([
      "calm", "peace", "peaceful", "serene", "serenity", "still", "stillness",
      "quiet", "tranquil", "tranquility", "content", "contentment", "relaxed",
      "relaxation", "balanced", "balance", "acceptance", "accept", "mindful",
      "mindfulness", "centered", "grounded"
    ]),
    phrases: [
      "at peace", "feel calm", "feeling calm", "feel peaceful", "feeling peaceful",
      "at ease", "inner peace", "peace of mind", "calm down"
    ],
  },
};

export const GENERIC_WORDS = new Set([
  "new", "people", "person", "places", "place", "travel", "travelling", "traveling",
  "see", "seeing", "look", "looking", "learn", "learning", "story", "stories",
  "beautifully", "absolutely", "really", "very", "extremely", "much", "more",
  "good", "great", "nice", "interesting"
]);

export const INTENSITY_MODIFIERS: Record<string, number> = {
  "slightly": 0.70,
  "somewhat": 0.80,
  "a little": 0.75,
  "little": 0.75,
  "mildly": 0.75,
  "quite": 1.10,
  "rather": 1.10,
  "pretty": 1.10,
  "really": 1.20,
  "very": 1.25,
  "so": 1.25,
  "deeply": 1.35,
  "strongly": 1.35,
  "extremely": 1.45,
  "absolutely": 1.45,
  "completely": 1.45,
  "totally": 1.45,
  "utterly": 1.50,
  "incredibly": 1.40,
};

export const NEGATION_WORDS = new Set([
  "not", "never", "no", "none", "neither", "nor", "without",
  "hardly", "barely", "don't", "dont", "doesn't", "doesnt",
  "didn't", "didnt", "isn't", "isnt", "wasn't", "wasnt",
  "can't", "cant", "cannot", "won't", "wont"
]);

export const POSITIVE_WORDS = new Set([
  "love", "beautiful", "amazing", "wonderful", "happy", "joy", "joyful",
  "great", "good", "brave", "peace", "peaceful", "calm", "excited",
  "awesome", "incredible", "funny", "laugh", "laughing", "adore"
]);

export const NEGATIVE_WORDS = new Set([
  "sad", "angry", "furious", "hate", "frustrated", "afraid", "fear",
  "terrified", "scared", "anxious", "pain", "hurt", "lonely",
  "disgusting", "horrible", "hopeless", "helpless", "grief"
]);

export function tokenize(text: string): string[] {
  const matches = text.toLowerCase().match(/\b[\w'-]+\b/g);
  return matches ? matches : [];
}

export function phraseOccurrences(text: string, phrase: string): number {
  const escaped = phrase.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const regex = new RegExp(`(?<!\\w)${escaped}(?!\\w)`, "gi");
  const matches = text.match(regex);
  return matches ? matches.length : 0;
}

export function getIntensity(tokens: string[], index: number): number {
  let intensity = 1.0;
  const windowStart = Math.max(0, index - 3);
  const previousWords = tokens.slice(windowStart, index);

  for (const [modifier, multiplier] of Object.entries(INTENSITY_MODIFIERS)) {
    const modifierTokens = modifier.split(" ");
    if (modifierTokens.length <= previousWords.length) {
      const slice = previousWords.slice(-modifierTokens.length);
      if (slice.join(" ") === modifier) {
        intensity *= multiplier;
        break;
      }
    }
  }

  return Math.round(Math.min(intensity, 1.5) * 1000) / 1000;
}

export function isNegated(tokens: string[], index: number): boolean {
  const windowStart = Math.max(0, index - 3);
  for (const word of tokens.slice(windowStart, index)) {
    if (NEGATION_WORDS.has(word)) {
      return true;
    }
  }
  return false;
}

export function calculateSentiment(text: string): SentimentResult {
  const tokens = tokenize(text);
  if (tokens.length === 0) {
    return { positive: 0, negative: 0, neutral: 1, compound: 0 };
  }

  let posCount = 0;
  let negCount = 0;
  for (const token of tokens) {
    if (POSITIVE_WORDS.has(token)) posCount++;
    if (NEGATIVE_WORDS.has(token)) negCount++;
  }

  const total = tokens.length;
  const positive = Math.round((posCount / total) * 1000) / 1000;
  const negative = Math.round((negCount / total) * 1000) / 1000;
  const neutral = Math.round(Math.max(0, 1 - positive - negative) * 1000) / 1000;

  let compound = 0;
  if (posCount > negCount) {
    compound = Math.min(1.0, posCount / Math.max(1, posCount + negCount));
  } else if (negCount > posCount) {
    compound = -Math.min(1.0, negCount / Math.max(1, posCount + negCount));
  }
  compound = Math.round(compound * 1000) / 1000;

  return { positive, negative, neutral, compound };
}

export function analyseText(textInput: string): NavarasaAnalysis {
  const text = (textInput || "").trim();
  if (!text) {
    return {
      primary_rasa: "Shanta",
      rasa_scores: {},
      evidence: {},
      emotional_words: [],
      analysis_quality: "no_text",
      sentiment: calculateSentiment(""),
      text: "",
    };
  }

  const lowerText = text.toLowerCase();
  const tokens = tokenize(lowerText);

  const evidence: Partial<Record<RasaType, EvidenceItem[]>> = {};
  const rawScores: Partial<Record<RasaType, number>> = {};
  const detectedWords: string[] = [];

  // Step 1: Phrase matching
  for (const [rasaKey, lexicon] of Object.entries(EMOTIONAL_LEXICON)) {
    const rasa = rasaKey as RasaType;
    for (const phrase of lexicon.phrases) {
      const occurrences = phraseOccurrences(lowerText, phrase);
      if (occurrences === 0) continue;

      const phraseWordCount = phrase.split(/\s+/).length;
      let confidence = Math.min(1.0, 0.90 + 0.03 * Math.min(phraseWordCount, 3));

      // Negation before phrase
      const phraseIndex = lowerText.indexOf(phrase);
      const beforePhrase = lowerText.substring(Math.max(0, phraseIndex - 20), phraseIndex);
      const wordsBefore = beforePhrase.split(/\s+/);
      const negated = wordsBefore.some((w) => NEGATION_WORDS.has(w));
      if (negated) {
        confidence *= 0.20;
      }

      if (!evidence[rasa]) evidence[rasa] = [];
      for (let i = 0; i < occurrences; i++) {
        evidence[rasa]!.push({
          word: phrase,
          rasa,
          confidence: Math.round(confidence * 1000) / 1000,
          intensity: 1.0,
          reason: "exact_emotional_phrase",
          occurrences: 1,
        });
        rawScores[rasa] = (rawScores[rasa] || 0) + confidence * 1.5;
        detectedWords.push(phrase);
      }
    }
  }

  // Step 2: Single word matching
  for (let i = 0; i < tokens.length; i++) {
    const token = tokens[i];
    if (GENERIC_WORDS.has(token)) continue;

    for (const [rasaKey, lexicon] of Object.entries(EMOTIONAL_LEXICON)) {
      const rasa = rasaKey as RasaType;
      if (!lexicon.core.has(token)) continue;
      if (isNegated(tokens, i)) continue;

      const intensity = getIntensity(tokens, i);
      const confidence = 0.95;

      if (!evidence[rasa]) evidence[rasa] = [];
      evidence[rasa]!.push({
        word: token,
        rasa,
        confidence,
        intensity,
        reason: "exact_emotional_lexicon",
        occurrences: 1,
      });

      rawScores[rasa] = (rawScores[rasa] || 0) + confidence * intensity;
      detectedWords.push(token);
    }
  }

  // Step 3: Group / deduplicate evidence
  const cleanedEvidence: Partial<Record<RasaType, EvidenceItem[]>> = {};
  for (const [rasaKey, items] of Object.entries(evidence)) {
    const rasa = rasaKey as RasaType;
    const grouped: Record<string, EvidenceItem> = {};
    for (const item of items || []) {
      const key = `${item.word}::${item.reason}`;
      if (!grouped[key]) {
        grouped[key] = { ...item };
      } else {
        grouped[key].occurrences += item.occurrences;
      }
    }
    cleanedEvidence[rasa] = Object.values(grouped);
  }

  // Step 4: Normalize scores
  const scoreEntries = Object.entries(rawScores) as [RasaType, number][];
  const rasaScores: Partial<Record<RasaType, number>> = {};
  if (scoreEntries.length > 0) {
    const maxScore = Math.max(...scoreEntries.map(([_, s]) => s));
    for (const [rasa, score] of scoreEntries) {
      rasaScores[rasa] = Math.round((score / maxScore) * 1000) / 1000;
    }
  }

  // Step 5: Determine primary Rasa
  let primaryRasa: RasaType = "Shanta";
  if (Object.keys(rasaScores).length > 0) {
    let topRasa: RasaType = "Shanta";
    let topScore = -1;
    for (const [rasaKey, score] of Object.entries(rasaScores)) {
      const rasa = rasaKey as RasaType;
      if (score! > topScore) {
        topScore = score!;
        topRasa = rasa;
      }
    }
    primaryRasa = topRasa;
  }

  // Step 6: Analysis quality
  const emotionalCount = detectedWords.length;
  let analysisQuality = "no_emotion_detected";
  if (emotionalCount === 1) analysisQuality = "weak_emotion_signal";
  else if (emotionalCount <= 3) analysisQuality = "moderate_emotion_signal";
  else if (emotionalCount > 3) analysisQuality = "strong_emotion_signal";

  // Step 7: Unique emotional words
  const emotionalWords = Array.from(new Set(detectedWords)).sort((a, b) =>
    a.toLowerCase().localeCompare(b.toLowerCase())
  );

  return {
    primary_rasa: primaryRasa,
    rasa_scores: rasaScores,
    evidence: cleanedEvidence,
    emotional_words: emotionalWords,
    analysis_quality: analysisQuality,
    sentiment: calculateSentiment(text),
    text,
  };
}
