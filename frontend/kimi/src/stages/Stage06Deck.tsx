import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { transition, MECHANICAL } from '../lib/motion';
import { DECK, type DeckCard } from '../lib/deck';

function CardFace({ card, large }: { card: DeckCard; large?: boolean }) {
  return (
    <div
      className={`relative w-full h-full border ${large ? 'border-gold/90' : 'border-brass/60'} flex flex-col items-center justify-between text-center`}
      style={{
        background: 'linear-gradient(165deg, #171f15 0%, #10160f 55%, #0b100c 100%)',
        boxShadow: large
          ? '0 40px 80px rgba(0,0,0,0.7), inset 0 0 40px rgba(56,71,50,0.35)'
          : '0 10px 24px rgba(0,0,0,0.5)',
      }}
    >
      <div className={`font-mono ${large ? 'text-[10px]' : 'text-[7px] md:text-[8px]'} tracking-[0.3em] text-gold/80 pt-3`}>
        № {String(card.id).padStart(2, '0')}
      </div>
      <div className={large ? 'px-6' : 'px-2'}>
        <div className={`${large ? 'text-4xl' : 'text-lg md:text-2xl'} text-gold/90`}>{card.glyph}</div>
        <div className={`mt-2 font-display ${large ? 'text-xl md:text-2xl' : 'text-[9px] md:text-xs'} tracking-[0.14em] text-parchment leading-snug`}>
          {card.title}
        </div>
        {large && (
          <>
            <div className="gold-rule w-24 mx-auto my-4" />
            <p className="font-serif italic text-sm md:text-base text-parchment-dim leading-relaxed text-balance">{card.statement}</p>
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

/** Stage 06 — THE 27-CARD DECK. "Turn the one that sounds like you." */
export default function Stage06Deck({ onComplete }: { onComplete: (card: DeckCard) => void }) {
  const [dealt, setDealt] = useState(0); // 1 → 3 → 9 → 27
  const [hovered, setHovered] = useState<number | null>(null);
  const [selected, setSelected] = useState<DeckCard | null>(null);
  const [resonates, setResonates] = useState(false);

  // physically dealt: one card → three → nine → twenty-seven → settle
  useEffect(() => {
    const t = [
      window.setTimeout(() => setDealt(1), 900),
      window.setTimeout(() => setDealt(3), 1700),
      window.setTimeout(() => setDealt(9), 2500),
      window.setTimeout(() => setDealt(27), 3400),
    ];
    return () => t.forEach(clearTimeout);
  }, []);

  const choose = (card: DeckCard) => {
    if (selected) return;
    setSelected(card);
    window.setTimeout(() => setResonates(true), 1400);
    window.setTimeout(() => onComplete(card), 3600);
  };

  return (
    <div className="relative min-h-[100dvh] flex flex-col items-center justify-center px-4 py-24 overflow-hidden">
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={transition('REVEAL')} className="text-center mb-8 md:mb-12">
        <div className="meta-label mb-3">THE DECK IS DEALT</div>
        <h2 className="font-display text-2xl md:text-4xl tracking-[0.12em] text-balance">TURN THE ONE THAT SOUNDS LIKE YOU</h2>
      </motion.div>

      {/* the deck */}
      <div className={`grid grid-cols-3 md:grid-cols-9 gap-2 md:gap-3 w-full max-w-5xl transition-opacity duration-1000 ${selected ? 'opacity-25' : 'opacity-100'}`}>
        {DECK.slice(0, dealt).map((card, i) => (
          <motion.button
            key={card.id}
            className="relative aspect-[2/3] min-h-[44px] cursor-pointer"
            initial={{ opacity: 0, y: 40, rotate: i % 2 ? 3 : -3 }}
            animate={{ opacity: 1, y: 0, rotate: 0 }}
            transition={{ duration: 0.6, delay: (i % 9) * 0.05, ease: MECHANICAL }}
            whileHover={{ y: -10 }}
            onHoverStart={() => setHovered(card.id)}
            onHoverEnd={() => setHovered(null)}
            onClick={() => choose(card)}
            disabled={!!selected}
            style={{ transformStyle: 'preserve-3d' }}
          >
            <motion.div
              className="w-full h-full"
              animate={hovered === card.id && !selected ? { scale: 1.04 } : { scale: 1 }}
              transition={transition('SETTLE')}
              style={{
                filter: hovered === card.id && !selected ? 'drop-shadow(0 18px 24px rgba(0,0,0,0.65))' : 'drop-shadow(0 6px 10px rgba(0,0,0,0.45))',
              }}
            >
              <img src="/assets/card-back.png" alt="" className="w-full h-full object-cover rounded-[4px]" draggable={false} />
            </motion.div>
            {/* number + registration mark on hover */}
            <AnimatePresence>
              {hovered === card.id && !selected && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={transition('SETTLE')}
                  className="absolute inset-x-0 -bottom-6 text-center font-mono text-[9px] tracking-[0.3em] text-gold"
                >
                  № {String(card.id).padStart(2, '0')}
                </motion.div>
              )}
            </AnimatePresence>
          </motion.button>
        ))}
      </div>

      {/* the chosen card separates from the deck */}
      <AnimatePresence>
        {selected && (
          <motion.div
            className="fixed inset-0 z-40 flex items-center justify-center pointer-events-none px-6"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={transition('SETTLE')}
          >
            <motion.div
              className="w-[min(64vw,240px)] md:w-[280px] aspect-[2/3]"
              initial={{ y: 80, scale: 0.8, opacity: 0 }}
              animate={{ y: 0, scale: 1, opacity: 1 }}
              transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
            >
              <CardFace card={selected} large />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {resonates && selected && (
          <motion.div
            className="fixed bottom-16 md:bottom-20 inset-x-0 z-40 text-center"
            initial={{ opacity: 0, letterSpacing: '0.2em' }}
            animate={{ opacity: 1, letterSpacing: '0.6em' }}
            exit={{ opacity: 0 }}
            transition={{ duration: 1.2, ease: [0.45, 0, 0.1, 1] }}
          >
            <span className="font-mono text-xs md:text-sm text-gold">RESONATES</span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
