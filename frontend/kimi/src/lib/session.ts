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

export type ChosenCardReveal = {
  card_index: number;
  title: string;
  statement: string;
  validation: string;
  disclaimer: string;
};

export type SessionReveal = {
  session_id: string;
  what_you_gave: string;
  what_you_gave_channel?: string;
  turn_texts?: string[];
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
