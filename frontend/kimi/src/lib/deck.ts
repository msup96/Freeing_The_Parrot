export type DeckCard = {
  id: number;
  cardId: string;
  glyph: string;
  title: string;
  archetype?: string;
  statement: string;
};

export type ServerCard = {
  card_id: string;
  card_index: number;
  title: string;
  archetype?: string;
  qualitative_reading: string;
};

const GLYPHS = ['✶', '☽', '🜂', '⚖', '◉', '⚘', '☍', '✦', '⎔', '⌁'];

export function cardsFromServer(cards: ServerCard[]): DeckCard[] {
  return cards.map((card) => ({
    id: card.card_index,
    cardId: card.card_id,
    glyph: GLYPHS[(card.card_index - 1) % GLYPHS.length],
    title: card.title,
    archetype: card.archetype,
    statement: card.qualitative_reading,
  }));
}

