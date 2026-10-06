import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { transition, MECHANICAL } from '../lib/motion';
import type { DeckCard } from '../lib/deck';

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
        <div className={`font-display ${large ? 'text-lg md:text-xl' : 'text-[9px] md:text-xs'} tracking-[0.14em] text-parchment leading-snug`}>
          {card.title}
        </div>
        {card.archetype && (
          <div className={`mt-1 font-mono ${large ? 'text-[10px]' : 'text-[6px]'} tracking-[0.25em] text-gold/60 uppercase`}>
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
      <div className={`pb-3 font-mono ${large ? 'text-[9px]' : 'text-[6px] md:text-[7px]'} tracking-[0.35em] text-parchment-faint/60`}>
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
  onComplete: (card: DeckCard) => void;
  onRetry?: () => void;
}) {
  const [phase, setPhase] = useState<'concluded' | 'silence' | 'deck'>('concluded');
  const [dealt, setDealt] = useState(0); // 1 → 3 → 9 → 27
  const [hovered, setHovered] = useState<number | null>(null);
  const [selected, setSelected] = useState<DeckCard | null>(null);
  const [resonating, setResonating] = useState(false);

  // Transition ritual: CONVERSATION CONCLUDED → THE PARROT HAS NOTHING MORE TO SAY → 27 CARDS APPEAR
  useEffect(() => {
    const t1 = window.setTimeout(() => setPhase('silence'), 1200);
    const t2 = window.setTimeout(() => setPhase('deck'), 2400);
    const t3 = window.setTimeout(() => setDealt(3), 2900);
    const t4 = window.setTimeout(() => setDealt(9), 3400);
    const t5 = window.setTimeout(() => setDealt(27), 4000);
    return () => [t1, t2, t3, t4, t5].forEach(clearTimeout);
  }, []);

  const handleSelect = (card: DeckCard) => {
    if (resonating) return;
    setSelected(card);
  };

  const handleConfirmResonance = () => {
    if (!selected || resonating) return;
    setResonating(true);
    window.setTimeout(() => {
      onComplete(selected);
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
    <div className="relative min-h-[100dvh] flex flex-col items-center justify-center px-4 py-20 overflow-hidden">
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
              ONE OF THESE MAY FEEL FAMILIAR.
            </h2>
            <p className="mt-1 font-serif italic text-xs md:text-sm text-parchment-dim">
              Turn the one that sounds like you
            </p>
          </motion.div>

          {/* the 27-card grid */}
          <div
            className={`grid grid-cols-3 sm:grid-cols-6 md:grid-cols-9 gap-2 md:gap-3 w-full max-w-5xl transition-opacity duration-700 ${
              selected ? 'opacity-20 pointer-events-none' : 'opacity-100'
            }`}
          >
            {cards.slice(0, dealt).map((card, i) => (
              <motion.button
                key={card.cardId}
                className="relative aspect-[2/3] min-h-[44px] cursor-pointer"
                initial={{ opacity: 0, y: 30, rotate: i % 2 ? 2 : -2 }}
                animate={{ opacity: 1, y: 0, rotate: 0 }}
                transition={{ duration: 0.5, delay: (i % 9) * 0.04, ease: MECHANICAL }}
                whileHover={{ y: -8 }}
                onHoverStart={() => setHovered(card.id)}
                onHoverEnd={() => setHovered(null)}
                onClick={() => handleSelect(card)}
                disabled={!!selected}
                style={{ transformStyle: 'preserve-3d' }}
                aria-label={`Card № ${card.id}: ${card.title}`}
              >
                <motion.div
                  className="w-full h-full"
                  animate={hovered === card.id && !selected ? { scale: 1.04 } : { scale: 1 }}
                  transition={transition('SETTLE')}
                  style={{
                    filter:
                      hovered === card.id && !selected
                        ? 'drop-shadow(0 16px 20px rgba(0,0,0,0.65))'
                        : 'drop-shadow(0 4px 8px rgba(0,0,0,0.4))',
                  }}
                >
                  <img
                    src="/assets/card-back.png"
                    alt=""
                    className="w-full h-full object-cover rounded-[3px]"
                    draggable={false}
                  />
                </motion.div>
                {/* index hint on hover */}
                <AnimatePresence>
                  {hovered === card.id && !selected && (
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

      {/* Selected Card Modal — Prominently centered with mechanical archival presence */}
      <AnimatePresence>
        {selected && (
          <motion.div
            className="fixed inset-0 z-50 flex flex-col items-center justify-center p-4 md:p-6 bg-[#070b08]/85 backdrop-blur-md"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
          >
            {/* Atmospheric brass focal glow behind the elevated card */}
            <motion.div
              className="absolute pointer-events-none rounded-full"
              style={{
                width: 'min(90vw, 520px)',
                height: 'min(90vw, 520px)',
                background: 'radial-gradient(circle, rgba(196,160,53,0.18) 0%, rgba(23,31,21,0.5) 45%, transparent 70%)',
              }}
              initial={{ scale: 0.6, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.8, opacity: 0 }}
              transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
            />

            {/* Centered elevated physical card */}
            <motion.div
              className="relative z-10 w-[min(82vw,290px)] md:w-[330px] aspect-[2/3] max-h-[66vh]"
              initial={{ y: 80, scale: 0.82, opacity: 0, rotateX: 10 }}
              animate={
                resonating
                  ? { y: 0, scale: [1, 1.02, 1], opacity: 1, rotateX: 0, filter: ['brightness(1)', 'brightness(1.12)', 'brightness(1)'] }
                  : { y: 0, scale: 1, opacity: 1, rotateX: 0, filter: 'brightness(1)' }
              }
              exit={{ y: 50, scale: 0.9, opacity: 0 }}
              transition={
                resonating
                  ? { duration: 0.8, ease: 'easeInOut' }
                  : { duration: 0.7, ease: [0.16, 1, 0.3, 1] }
              }
            >
              <CardFace card={selected} large />
            </motion.div>

            {/* Selection actions: RESONATES vs CHOOSE ANOTHER */}
            <div className="relative z-10 mt-6 md:mt-8 flex flex-col items-center gap-3">
              {!resonating ? (
                <>
                  <motion.button
                    initial={{ opacity: 0, y: 14 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3, duration: 0.4 }}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    className="brass-button px-9 py-3.5 min-h-[44px] text-xs md:text-sm tracking-[0.3em] font-mono cursor-pointer shadow-[0_4px_20px_rgba(0,0,0,0.5)]"
                    onClick={handleConfirmResonance}
                  >
                    RESONATES
                  </motion.button>
                  <motion.button
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.42, duration: 0.4 }}
                    className="text-parchment-faint hover:text-parchment text-[11px] font-mono tracking-[0.2em] transition-colors py-1.5 cursor-pointer"
                    onClick={() => setSelected(null)}
                  >
                    CHOOSE ANOTHER
                  </motion.button>
                </>
              ) : (
                <motion.div
                  initial={{ opacity: 0, letterSpacing: '0.2em', y: 6 }}
                  animate={{ opacity: 1, letterSpacing: '0.45em', y: 0 }}
                  transition={{ duration: 0.8 }}
                  className="font-mono text-xs md:text-sm text-gold py-2"
                >
                  RESONANCE RECORDED.
                </motion.div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
