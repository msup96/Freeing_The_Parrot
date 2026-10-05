export type DeckCard = {
  id: number;
  glyph: string;
  title: string;
  statement: string;
};

const GLYPHS = ['✶', '☽', '🜂', '⚖', '◉', '⚘', '☍', '✦', '⎔', '⌁'];

const CARDS: [string, string][] = [
  ['The Rewritten Talk', 'A conversation you keep editing in your head long after it ended.'],
  ['The Quiet Ledger', 'Favours given are remembered more carefully than favours received.'],
  ['The Open Door', 'Openness to people is real, though it stops at certain rooms.'],
  ['The Borrowed Voice', 'Some opinions were tried on before they became yours.'],
  ['The Late Reply', 'A message left unanswered says more than one sent quickly.'],
  ['The Two Rooms', 'A public self and a private self do not always agree.'],
  ['The Held Breath', 'Some decisions are made long before they are announced.'],
  ['The Small Ritual', 'One habit is kept mostly because stopping feels unlucky.'],
  ['The Careful Kindness', 'Kindness is given freely, but a limit sits beneath it.'],
  ['The Doubt at Night', 'Certainty is easier by day than after midnight.'],
  ['The Old Photograph', 'Some pictures hold a version of you that is still argued with.'],
  ['The Unsaid Thing', 'A truth is nearly said, then postponed once more.'],
  ['The Chosen Distance', 'Closeness is wanted, in measured amounts.'],
  ['The Sharp Memory', 'A remark from years ago can still be quoted exactly.'],
  ['The Second Draft', 'Work is quietly judged harsher than anyone else would judge it.'],
  ['The Restless Map', 'Somewhere else has always looked slightly more possible.'],
  ['The Kept Promise', 'A vow made lightly ended up costing something.'],
  ['The Mask Drawer', 'Different rooms get different versions of the same person.'],
  ['The Slow Forgiveness', 'Some wrongs are forgiven in words but not in habit.'],
  ['The Hidden Talent', 'A gift is used less often than it deserves.'],
  ['The Waiting Room', 'Some part of life feels like it is waiting to begin.'],
  ['The Loud Silence', 'Being unasked has felt heavier than being refused.'],
  ['The Inherited Rule', 'A family rule is still obeyed, though nobody remembers its reason.'],
  ['The Held Hand', 'Support is offered easily and asked for rarely.'],
  ['The Unfinished Song', 'Something started with great energy is still unfinished.'],
  ['The Turned Key', 'A change of mind is possible, but never announced.'],
  ['The Last Light', 'Comfort arrives in small things at the end of the day.'],
];

export const DECK: DeckCard[] = CARDS.map(([title, statement], index) => ({
  id: index + 1,
  glyph: GLYPHS[index % GLYPHS.length],
  title,
  statement,
}));
