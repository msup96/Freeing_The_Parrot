export type OfferingChannel = 'write' | 'speak' | 'show' | 'look';

export type Offering = {
  channel: OfferingChannel;
  text?: string;
  imageDataUrl?: string;
  media?: Blob;
  filename?: string;
  timestamp: number;
};

export type ChatTurn = {
  role: 'participant' | 'parrot';
  text: string;
  behaviour?: string;
};

import type { DeckCard } from './deck';

export type SelectedCard = DeckCard & { selectionOrder: number };

export type ChosenCardReveal = {
  card_index: number;
  title: string;
  statement: string;
  validation: string;
  disclaimer: string;
};

export type SelectionPattern = {
  selected_count?: number;
  selected_card_ids?: string[];
  selected_card_indices?: number[];
  selection_order?: string[];
  semantic_anchors?: string[];
  semantic_motifs?: string[];
  archetypes?: string[];
  categories?: string[];
  reading_groups?: string[];
  resonance_recorded?: boolean;
};

/** One serialized evidence record (OBSERVED / INTERPRETED), as produced by the backend. */
export type EvidenceRecord = {
  evidence_id: string;
  signal_type: string;
  value: unknown;
  observation: string;
  source_event_ids: string[];
  provenance_level: string;
  limitations?: string[];
  limitation_notes?: string[];
};

/** One serialized inference record, including candidates the evidence contract closed. */
export type InferenceRecord = {
  inference_id: string;
  claim: string;
  evidence_refs: string[];
  alternative_interpretations?: string[];
  contradictions?: Array<{ description?: string; effect_on_confidence?: string }>;
  eligibility: string | null;
  confidence?: number | null;
  confidence_basis?: string | null;
  limitation_notes?: string[];
};

/** One card's machine provenance. Hidden composition internals are never rendered. */
export type CardProvenanceRecord = {
  card_id: string;
  card_index: number;
  title: string;
  semantic_anchor?: string;
  semantic_motif?: string;
  archetype?: string;
  provenance?: { evidence_ids?: string[]; inference_ids?: string[] };
  selection_state: string;
};

export type SessionReveal = {
  session_id: string;
  what_you_gave: string;
  what_you_gave_channel?: string;
  turn_texts?: string[];
  machine_transformation?: {
    raw_text?: { character_count?: number; turn_count?: number };
    turn_sequence?: number[];
    evidence_ids?: string[];
    inference_ids?: Array<string | null>;
  };
  observed_signals?: EvidenceRecord[];
  analytical_artifacts?: {
    linguistic?: Record<string, unknown>;
    temporal?: Record<string, unknown>;
    engagement?: Record<string, unknown>;
    navarasa?: Record<string, unknown>;
    evidence_bundle?: Record<string, unknown>;
    inference_evaluation?: Record<string, unknown>;
    deep_reader_packet?: Record<string, unknown>;
  };
  inference_records?: InferenceRecord[];
  card_provenance?: CardProvenanceRecord[];
  navarasa_trajectory?: {
    detected_sequence?: string[];
    dominant_rasa?: { label?: string | null; status?: string };
    transition_count?: { value?: number | null; status?: string };
    beginning_end_changed?: { value?: boolean | null; status?: string };
    quality_limitations?: { defaulted_shanta_turns?: number; status?: string };
  };
  interaction_profile?: Record<string, number | string | null>;
  selection_pattern?: SelectionPattern & { total_cards_presented?: number; cards_inspected?: number | null; selection_status?: string };
  what_was_recorded: string;
  what_the_system_observed?: string;
  what_was_recorded_sub: string;
  what_was_interpreted: string;
  what_the_system_interpreted?: string;
  what_was_interpreted_sub?: string;
  what_was_constructed?: string;
  what_the_system_inferred?: string;
  what_was_constructed_sub?: string;
  what_you_chose: ChosenCardReveal;
  what_we_cannot_know?: string[];
  wall_specimens?: Array<{
    card_id?: string;
    card_index: number;
    title: string;
    archetype: string;
    qualitative_reading: string;
  }>;
};

export type Session = {
  sessionId?: string;
  offering: Offering | null;
  turns: ChatTurn[];
  cards: DeckCard[];
  selectedCard: DeckCard | null;
  selectedCards: DeckCard[];
  cardId: number | null;
  reveal?: SessionReveal | null;
  consent: 'private' | 'wall' | null;
  receipt?: string | null;
};

export const emptySession: Session = {
  sessionId: undefined,
  offering: null,
  turns: [],
  cards: [],
  selectedCard: null,
  selectedCards: [],
  cardId: null,
  reveal: null,
  consent: null,
  receipt: null,
};

export const STAGE_META: Record<number, { index: string; name: string; world: string }> = {
  1: { index: '01', name: 'APPARATUS', world: 'WAITING ROOM' },
  2: { index: '02', name: 'OFFERING', world: 'INTAKE' },
  3: { index: '03', name: 'HIDDEN READER', world: 'DARKROOM' },
  4: { index: '04', name: 'THE PARROT', world: 'CONVERSATION' },
  6: { index: '06', name: 'THE DECK', world: 'TWENTY-SEVEN' },
  7: { index: '07', name: 'THE BREAK', world: 'RESONANCE' },
  8: { index: '08', name: 'DATA JOURNEY', world: 'THE WALL' },
  9: { index: '09', name: 'EXIT', world: 'RELEASE' },
};
