import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { transition, MECHANICAL } from '../lib/motion';
import type { DeckCard } from '../lib/deck';
import type { SelectedCard } from '../lib/session';

function CardFace({ card, large }: { card: DeckCard; large?: boolean }) {
  return (
    <div
      className={`relative w-full h-full border ${large ? 'border-gold/90' : 'border-brass/60'} flex flex-col items-center justify-between text-center select-none`}
      style={{
        background: 'linear-gradient(165deg, #171f15 0%, #10160f 55%, #0b100c 100%)',
        boxShadow: large
          ? '0 40px 80px rgba(0,0,0,0.85), inset 0 0 40px rgba(56,71,50,0.35)'
          : '0 10px 24px rgba(0,0,0,0.5)',
      }}
    >
      <div className={`font-mono ${large ? 'text-[11px]' : 'text-[7px] md:text-[8px]'} tracking-[0.3em] text-gold/80 pt-3`}>
        № {String(card.id).padStart(2, '0')}
      </div>
      <div className={large ? 'px-6 max-h-[72%] overflow-y-auto' : 'px-2'}>
        <div className={`${large ? 'text-3xl md:text-4xl' : 'text-lg md:text-2xl'} text-gold/90 mb-1`}>{card.glyph}</div>
        <div className={`font-display ${large ? 'text-lg md:text-xl' : 'text-[8px] sm:text-[9px] md:text-xs'} tracking-[0.08em] text-parchment leading-tight break-words max-w-full`}>
          {card.title}
        </div>
        <div className={`mt-1 font-mono ${large ? 'text-[9px]' : 'text-[8px] md:text-[9px]'} tracking-[0.22em] text-gold/70 uppercase`}>
          TERRITORY · {card.semanticAnchor}
        </div>
        {card.archetype && (
          <div className={`mt-1 font-mono ${large ? 'text-[10px]' : 'text-[5px] sm:text-[6px]'} tracking-[0.14em] leading-tight text-gold/60 uppercase break-words max-w-full`}>
            {card.archetype}
          </div>
        )}
        {large && (
          <>
            <div className="gold-rule w-24 mx-auto my-3" />
            <p className="font-serif italic text-xs md:text-sm text-parchment-dim leading-relaxed text-balance px-2">
              {card.statement}
            </p>
          </>
        )}
      </div>
      <div className={`pb-3 font-mono ${large ? 'text-[9px]' : 'text-[8px] md:text-[9px]'} tracking-[0.35em] text-parchment-faint/60`}>
        THE TWENTY-SEVEN
      </div>
      {/* registration marks */}
      <div className="absolute top-1.5 left-1.5 w-2 h-2 border-t border-l border-gold/60" />
      <div className="absolute top-1.5 right-1.5 w-2 h-2 border-t border-r border-gold/60" />
      <div className="absolute bottom-1.5 left-1.5 w-2 h-2 border-b border-l border-gold/60" />
      <div className="absolute bottom-1.5 right-1.5 w-2 h-2 border-b border-r border-gold/60" />
    </div>
  );
}

/** Stage 06 — THE 27-CARD POST-CONVERSATION DECK. */
export default function Stage06Deck({
  cards,
  onComplete,
  onRetry,
}: {
  cards: DeckCard[];
  onComplete: (cards: SelectedCard[]) => void;
  onRetry?: () => void;
}) {
  const [phase, setPhase] = useState<'concluded' | 'silence' | 'deck'>('concluded');
  const [dealt, setDealt] = useState(0); // 1 → 3 → 9 → 27
  const [hovered, setHovered] = useState<number | null>(null);
  const [selected, setSelected] = useState<DeckCard[]>([]);
  const [flipped, setFlipped] = useState<Set<string>>(new Set());
  const [shuffled, setShuffled] = useState(false);
  const [resonating, setResonating] = useState(false);
  const allCardsFlipped = dealt === 27 && flipped.size === cards.length;

  const toggleAllCards = () => {
    if (allCardsFlipped) {
      setFlipped(new Set());
      return;
    }
    setFlipped(new Set(cards.map((card) => card.cardId)));
  };

  // Transition ritual: CONVERSATION CONCLUDED → THE PARROT HAS NOTHING MORE TO SAY → 27 CARDS APPEAR
  useEffect(() => {
    const t1 = window.setTimeout(() => setPhase('silence'), 1200);
    const t2 = window.setTimeout(() => setPhase('deck'), 2400);
    const t3 = window.setTimeout(() => setDealt(3), 2900);
    const t4 = window.setTimeout(() => setDealt(9), 3400);
    const t5 = window.setTimeout(() => setDealt(27), 4000);
    return () => [t1, t2, t3, t4, t5].forEach(clearTimeout);
  }, []);

  const handleCardClick = (card: DeckCard) => {
    if (resonating) return;
    if (!flipped.has(card.cardId)) {
      setFlipped((current) => new Set(current).add(card.cardId));
      return;
    }
    setSelected((current) => current.some((item) => item.cardId === card.cardId)
      ? current.filter((item) => item.cardId !== card.cardId)
      : [...current, card]);
  };

  const handleConfirmResonance = () => {
    if (selected.length === 0 || resonating) return;
    setResonating(true);
    window.setTimeout(() => {
      onComplete(selected.map((card, index) => ({ ...card, selectionOrder: index + 1 })));
    }, 1500);
  };

  if (cards.length !== 27) {
    return (
      <div className="min-h-[100dvh] flex flex-col items-center justify-center px-6 gap-6 text-center">
        <div className="font-mono text-xs md:text-sm tracking-[0.25em] text-crimson">
          THE DECK COULD NOT BE DEALT.
        </div>
        {onRetry && (
          <button className="brass-button px-6 py-3 min-h-[44px] text-xs font-mono" onClick={onRetry}>
            RETRY DEALING
          </button>
        )}
      </div>
    );
  }

  return (
    <div 
      className="relative min-h-[100dvh] flex flex-col items-center justify-center px-4 py-20 overflow-hidden"
      style={{
        fontFamily: 'inherit',
        fontSize: '16'
      }}
    >
      {/* Prelude ritual sequence */}
      {phase !== 'deck' ? (
        <div className="min-h-[60vh] flex items-center justify-center text-center px-6">
          <AnimatePresence mode="wait">
            {phase === 'concluded' && (
              <motion.div
                key="concluded"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={transition('REVEAL')}
                className="font-mono text-xs md:text-sm tracking-[0.45em] text-parchment-dim"
              >
                CONVERSATION CONCLUDED.
              </motion.div>
            )}
            {phase === 'silence' && (
              <motion.div
                key="silence"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={transition('REVEAL')}
                className="font-mono text-xs md:text-sm tracking-[0.35em] text-parchment-faint"
              >
                THE PARROT HAS NOTHING MORE TO SAY.
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      ) : (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={transition('REVEAL')}
            className="text-center mb-6 md:mb-10"
          >
            <div className="meta-label mb-2">TWENTY-SEVEN CARDS</div>
              <h2 className="font-display text-xl md:text-3xl tracking-[0.14em] text-balance text-parchment">
              READINGS, NOT REWARDS.
            </h2>
            <p className="mt-1 font-serif italic text-xs md:text-sm text-parchment-dim">
              Flip the readings, shuffle them, then choose any number that resonates.
            </p>
            <div className="mt-4 flex flex-wrap items-center justify-center gap-3">
              <button type="button" className="brass-button min-h-11 px-4 py-2 text-[10px] tracking-[0.2em]" onClick={() => setShuffled((value) => !value)}>
                {shuffled ? 'SHUFFLE COMPLETE' : 'SHUFFLE THE READINGS'}
              </button>
              <button
                type="button"
                className="brass-button min-h-11 px-4 py-2 text-[10px] tracking-[0.2em]"
                onClick={toggleAllCards}
                aria-expanded={allCardsFlipped}
                aria-controls="twenty-seven-card-grid"
              >
                {allCardsFlipped ? 'CLOSE ALL CARDS' : 'OPEN ALL CARDS'}
              </button>
            </div>
          </motion.div>

          {/* the 27-card grid */}
          <div
            id="twenty-seven-card-grid"
            aria-label="Twenty-seven reading cards"
            className={`grid grid-cols-3 sm:grid-cols-6 md:grid-cols-9 gap-2 md:gap-3 w-full max-w-5xl transition-opacity duration-700 ${
              'opacity-100'
            }`}
          >
            {(shuffled ? [...cards].reverse() : cards).slice(0, dealt).map((card, i) => (
              <motion.button
                key={card.cardId}
                className={`relative aspect-[2/3] min-h-[44px] cursor-pointer ${selected.some((item) => item.cardId === card.cardId) ? 'ring-2 ring-gold ring-offset-2 ring-offset-[#0a0a09]' : ''}`}
                initial={{ opacity: 0, y: 30, rotate: i % 2 ? 2 : -2 }}
                animate={{ opacity: 1, y: 0, rotate: 0 }}
                transition={{ duration: 0.5, delay: (i % 9) * 0.04, ease: MECHANICAL }}
                whileHover={{ y: -8 }}
                onHoverStart={() => setHovered(card.id)}
                onHoverEnd={() => setHovered(null)}
                onClick={() => handleCardClick(card)}
                aria-pressed={selected.some((item) => item.cardId === card.cardId)}
                aria-label={`${flipped.has(card.cardId) ? 'Select' : 'Flip'} card № ${card.id}: ${card.title}`}
                style={{ transformStyle: 'preserve-3d' }}
              >
                <motion.div
                  className="w-full h-full"
                  animate={hovered === card.id ? { scale: 1.04 } : { scale: 1 }}
                  transition={transition('SETTLE')}
                  style={{
                    filter:
                      hovered === card.id
                        ? 'drop-shadow(0 16px 20px rgba(0,0,0,0.65))'
                        : 'drop-shadow(0 4px 8px rgba(0,0,0,0.4))',
                  }}
                >
                  {flipped.has(card.cardId) ? (
                    <CardFace card={card} />
                  ) : (
                    <img
                      src="/assets/card-back.png"
                      alt=""
                      className="w-full h-full object-cover rounded-[3px]"
                      draggable={false}
                    />
                  )}
                </motion.div>
                {/* index hint on hover */}
                <AnimatePresence>
                  {hovered === card.id && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      transition={transition('SETTLE')}
                      className="absolute inset-x-0 -bottom-6 text-center font-mono text-[9px] tracking-[0.25em] text-gold pointer-events-none"
                    >
                      № {String(card.id).padStart(2, '0')}
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.button>
            ))}
          </div>
        </>
      )}

      <div className="mt-8 flex flex-col items-center gap-3" aria-live="polite">
        <div className="font-mono text-[10px] tracking-[0.24em] text-parchment-dim uppercase">
          Selected: {selected.length} card{selected.length === 1 ? '' : 's'}
        </div>
        <button
          type="button"
          disabled={selected.length === 0 || resonating}
          onClick={handleConfirmResonance}
          className="brass-button px-9 py-3.5 min-h-[44px] text-xs md:text-sm tracking-[0.3em] font-mono disabled:cursor-not-allowed disabled:opacity-35"
        >
          {resonating ? 'RESONANCE RECORDED.' : 'RESONATE'}
        </button>
        <div className="font-serif italic text-xs text-parchment-faint">
          Flip to inspect. Select or deselect. Resonance confirms the complete set.
        </div>
      </div>
    </div>
  );
}
