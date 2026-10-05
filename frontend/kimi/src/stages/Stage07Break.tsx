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
    const delays = [1200, 2600, 3600, 4500, 5400, 6300, 7200, 8400, 10200, 12400];
    const timers = delays.map((d, i) => window.setTimeout(() => setStep(i + 1), d));
    const done = window.setTimeout(onComplete, 14400);
    return () => { timers.forEach(clearTimeout); clearTimeout(done); };
  }, [onComplete]);

  const brokenTitle = card.title.replace(/[AEIOU]/, 'Λ'); // the tiny typographic error
  const forensic = step >= 5;

  return (
    <motion.div
      className="relative min-h-[100dvh] overflow-hidden"
      animate={{ backgroundColor: step >= 6 ? '#0a0a09' : 'rgba(0,0,0,0)' }}
      transition={{ duration: step >= 6 ? 0.12 : 1 }}
    >
      {/* crimson hairlines — forensic grid intrudes */}
      {step >= 6 && (
        <>
          <motion.div className="fixed left-[12%] top-0 bottom-0 w-px bg-crimson/40" initial={{ scaleY: 0 }} animate={{ scaleY: 1 }} transition={{ duration: 0.15 }} />
          <motion.div className="fixed right-[12%] top-0 bottom-0 w-px bg-crimson/40" initial={{ scaleY: 0 }} animate={{ scaleY: 1 }} transition={{ duration: 0.15 }} />
          <motion.div className="fixed top-[20%] left-0 right-0 h-px bg-crimson/25" initial={{ scaleX: 0 }} animate={{ scaleX: 1 }} transition={{ duration: 0.15 }} />
        </>
      )}

      <div className={`min-h-[100dvh] flex ${step >= 5 ? 'items-start justify-start pl-[14%] pt-[22%]' : 'items-center justify-center'} transition-all`} style={{ transitionDuration: '150ms' }}>
        {/* the card — same object, betrayed by its own rendering */}
        <motion.div
          className="w-[min(60vw,220px)] md:w-[260px] aspect-[2/3] relative"
          layout
          transition={{ duration: 0.15, ease: [0.85, 0, 0.15, 1] }}
        >
          <motion.div
            className="w-full h-full flex flex-col items-center justify-between text-center border"
            animate={{
              borderColor: step >= 4 ? 'rgba(166,58,43,0.6)' : 'rgba(201,162,39,0.9)',
              backgroundColor: step >= 4 ? '#0d0d0c' : '#10160f',
              boxShadow: step >= 4 ? 'none' : '0 40px 80px rgba(0,0,0,0.7)',
            }}
            transition={{ duration: 0.15 }}
          >
            <div className={`${forensic ? 'font-mono' : 'font-mono'} text-[10px] tracking-[0.3em] pt-3 ${step >= 4 ? 'text-crimson/80' : 'text-gold/80'}`}>
              № {String(card.id).padStart(2, '0')}
            </div>
            <div className="px-5">
              {step < 4 && <div className="text-3xl text-gold/90">{card.glyph}</div>}
              <div className={`mt-2 ${forensic ? 'font-mono text-sm' : 'font-display text-xl'} tracking-[0.14em] leading-snug ${step >= 4 ? 'text-parchment/80' : 'text-parchment'}`}>
                {step >= 2 ? brokenTitle : card.title}
              </div>
              <p className={`mt-3 ${forensic ? 'font-mono text-[10px] tracking-[0.15em] not-italic' : 'font-serif italic text-sm'} ${step >= 4 ? 'text-parchment-faint' : 'text-parchment-dim'} leading-relaxed`}>
                {step >= 3 ? 'SELF-DESCRIPTION STIMULUS. BARNUM CLASS.' : card.statement}
              </p>
            </div>
            <div className={`pb-3 font-mono text-[9px] tracking-[0.35em] ${step >= 4 ? 'text-crimson/70' : 'text-parchment-faint/60'}`}>
              {step >= 3 ? `ITEM ${String(card.id).padStart(2, '0')} / 27` : 'THE TWENTY-SEVEN'}
            </div>
          </motion.div>

          {/* forensic annotations attach to the card */}
          {step >= 7 && (
            <>
              {[
                { text: 'SELECTION: VOLUNTARY', pos: '-left-2 top-6 -translate-x-full' },
                { text: 'LATENCY: MEASURED', pos: '-right-2 top-16 translate-x-full' },
                { text: 'COMPLIANCE: CONFIRMED', pos: '-left-2 bottom-10 -translate-x-full' },
              ].map((a, i) => (
                <motion.div
                  key={i}
                  className={`absolute ${a.pos} hidden md:block font-mono text-[9px] tracking-[0.25em] text-crimson/80 whitespace-nowrap`}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.1, delay: i * 0.25 }}
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
