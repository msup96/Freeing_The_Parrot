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

export type Session = {
  offering: Offering | null;
  turns: ChatTurn[];
  cardId: number | null;
  consent: 'private' | 'wall' | null;
};

export const emptySession: Session = {
  offering: null,
  turns: [],
  cardId: null,
  consent: null,
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
