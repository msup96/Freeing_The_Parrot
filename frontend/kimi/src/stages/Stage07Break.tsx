import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { DeckCard } from '../lib/deck';

/**
 * Stage 07 — THE BREAK.
 * Not a hacker glitch: the backstage infrastructure suddenly becomes visible.
 * Hard cuts, typographic replacement, spatial snapping, material collapse.
 */
export default function Stage07Break({ card, onComplete }: { card: DeckCard; onComplete: () => void }) {
  const [step, setStep] = useState(0);

  useEffect(() => {
    // 1 card visible · 2 typo · 3 label changes · 4 texture dies · 5 serif→mono
    // 6 alignment snaps · 7 aesthetic collapses · 8 forensic system · 9-10 the words
    const delays = [600, 1200, 1800, 2400, 3000, 3600, 4200, 5000, 5800];
    const timers = delays.map((d, i) => window.setTimeout(() => setStep(i + 1), d));
    const done = window.setTimeout(onComplete, 7200);
    return () => { timers.forEach(clearTimeout); clearTimeout(done); };
  }, [onComplete]);

  return (
    <motion.div
      className="relative min-h-[100dvh] overflow-hidden"
      animate={{ backgroundColor: step >= 3 ? '#0a0a09' : 'rgba(0,0,0,0)' }}
      transition={{ duration: step >= 3 ? 0.2 : 0.8 }}
    >
      {/* subtle archival alignment lines */}
      {step >= 3 && (
        <>
          <motion.div className="fixed left-[12%] top-0 bottom-0 w-px bg-crimson/30" initial={{ scaleY: 0 }} animate={{ scaleY: 1 }} transition={{ duration: 0.2 }} />
          <motion.div className="fixed right-[12%] top-0 bottom-0 w-px bg-crimson/30" initial={{ scaleY: 0 }} animate={{ scaleY: 1 }} transition={{ duration: 0.2 }} />
          <motion.div className="fixed top-[20%] left-0 right-0 h-px bg-crimson/20" initial={{ scaleX: 0 }} animate={{ scaleX: 1 }} transition={{ duration: 0.2 }} />
        </>
      )}

      <div className={`min-h-[100dvh] flex ${step >= 3 ? 'items-start justify-start pl-[14%] pt-[18%]' : 'items-center justify-center'} transition-all`} style={{ transitionDuration: '250ms' }}>
        {/* the card — participant's actual validated reading */}
        <motion.div
          className="w-[min(64vw,240px)] md:w-[280px] aspect-[2/3] relative"
          layout
          transition={{ duration: 0.25, ease: [0.85, 0, 0.15, 1] }}
        >
          <motion.div
            className="w-full h-full flex flex-col items-center justify-between text-center border p-2"
            animate={{
              borderColor: step >= 2 ? 'rgba(166,58,43,0.7)' : 'rgba(201,162,39,0.9)',
              backgroundColor: step >= 2 ? '#0d0d0c' : '#10160f',
              boxShadow: step >= 2 ? '0 20px 40px rgba(0,0,0,0.8)' : '0 40px 80px rgba(0,0,0,0.7)',
            }}
            transition={{ duration: 0.2 }}
          >
            <div className="font-mono text-[10px] tracking-[0.3em] pt-3 text-gold/80">
              № {String(card.id).padStart(2, '0')}
            </div>
            <div className="px-5">
              <div className="text-3xl text-gold/90">{card.glyph}</div>
              <div className="mt-2 font-display text-lg md:text-xl tracking-[0.14em] leading-snug text-parchment">
                {card.title}
              </div>
              <p className="mt-3 font-serif italic text-xs md:text-sm text-parchment-dim leading-relaxed">
                {card.statement}
              </p>
            </div>
            <div className="pb-3 font-mono text-[9px] tracking-[0.35em] text-parchment-faint/60">
              THE TWENTY-SEVEN
            </div>
          </motion.div>

          {/* archival status indicators */}
          {step >= 3 && (
            <>
              {[
                { text: 'SELECTION: VOLUNTARY', pos: 'left-1 top-6 md:-left-2 md:-translate-x-full' },
                { text: 'RESPONSE: RECORDED', pos: 'right-1 top-16 md:-right-2 md:translate-x-full' },
                { text: 'RESONANCE: SELF-REPORTED', pos: 'left-1 bottom-16 md:-left-2 md:-translate-x-full' },
                { text: 'VALIDATION: PARTICIPANT-SUPPLIED', pos: 'right-1 bottom-10 md:-right-2 md:translate-x-full' },
              ].map((a, i) => (
                <motion.div
                  key={i}
                  className={`absolute ${a.pos} font-mono text-[8px] md:text-[9px] tracking-[0.12em] md:tracking-[0.25em] text-crimson/80 whitespace-nowrap max-w-[45vw] overflow-hidden text-ellipsis`}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.15, delay: i * 0.15 }}
                >
                  ▸ {a.text}
                </motion.div>
              ))}
            </>
          )}
        </motion.div>
      </div>

      {/* the words */}
      <div className="fixed inset-x-0 bottom-[18%] text-center space-y-4 px-6">
        <AnimatePresence>
          {step >= 8 && (
            <motion.div
              key="l1"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.08 }}
              className="font-mono text-lg md:text-3xl tracking-[0.3em] text-parchment"
            >
              YOU PLAYED YOUR CARDS.
            </motion.div>
          )}
          {step >= 9 && (
            <motion.div
              key="l2"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.08 }}
              className="font-mono text-lg md:text-3xl tracking-[0.3em] text-crimson"
            >
              NOW I PLAY MINE.
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
