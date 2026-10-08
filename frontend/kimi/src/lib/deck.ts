export type DeckCard = {
  id: number;
  cardId: string;
  glyph: string;
  semanticAnchor: string;
  semanticMotif: string;
  title: string;
  archetype?: string;
  statement: string;
};

export type ServerCard = {
  card_id: string;
  card_index: number;
  title: string;
  semantic_anchor?: string;
  semantic_motif?: string;
  archetype?: string;
  qualitative_reading: string;
};

const SEMANTIC_CARD_DATA = [
  ['INQUIRY', 'open-star'], ['GUIDANCE', 'lantern-beam'], ['RETURN', 'returning-loop'], ['SILENCE', 'weather-veil'], ['DELAY', 'held-hourglass'], ['RECONSIDERATION', 'turning-crescent'], ['ABSENCE', 'bell-negative-space'], ['DOUBT', 'worn-forked-path'], ['OMISSION', 'broken-glyph'], ['DEPTH', 'layered-contour'], ['RECOGNITION', 'reflected-point'], ['ATTENTION', 'narrow-beam'], ['CULTIVATION', 'branching-tree'], ['RECURRENCE', 'circular-current'], ['PAUSE', 'held-breath'], ['UNCERTAINTY', 'unstable-flame'], ['THRESHOLD', 'door-frame'], ['REVELATION', 'occluded-flame'], ['LANGUAGE', 'syntax-fragment'], ['AGENCY', 'upright-ray'], ['DIFFICULTY', 'clouded-point'], ['REFRAMING', 'shifting-frame'], ['ADAPTATION', 'branching-path'], ['DISCERNMENT', 'measured-thread'], ['PATTERN', 'repeating-tessellation'], ['INCOMPLETION', 'open-circle'], ['BEGINNING', 'rising-line'],
] as const;

// One restrained symbolic language: each family reuses a primitive, while the
// seed word changes the interruption, axis, or enclosure so no glyph repeats.
const SYMBOLIC_GLYPHS = [
  '·◌', '⌜·⌟', '◌↻', '⌁│', '│◫', '◒·', '◌∶', '╱·╲', '□╱',
  '≋◌', '◉╱', '│·│', '╱┬╲', '◌≋', '∪·', '╱◒', '⌑│', '◐│',
  '┄╱', '↑·', '◌╳', '⌁□', '╱┬', '·┄·', '▦·', '◌╯', '╱↑',
] as const;

const SYMBOLIC_SEEDS = [
  'opening', 'guiding', 'returning', 'veiling', 'deferring', 'reconsidering',
  'emptying', 'forking', 'breaking', 'layering', 'recognising', 'attending',
  'cultivating', 'recurring', 'pausing', 'flickering', 'crossing', 'revealing',
  'fragmenting', 'standing', 'clouding', 'reframing', 'adapting', 'measuring',
  'repeating', 'unfinishing', 'rising',
] as const;

export function cardsFromServer(cards: ServerCard[]): DeckCard[] {
  return cards.map((card) => ({
    id: card.card_index,
    cardId: card.card_id,
    glyph: SYMBOLIC_GLYPHS[card.card_index - 1],
    semanticAnchor: card.semantic_anchor ?? SEMANTIC_CARD_DATA[card.card_index - 1][0],
    semanticMotif: SYMBOLIC_SEEDS[card.card_index - 1],
    title: card.title,
    archetype: card.archetype,
    statement: card.qualitative_reading,
  }));
}

