import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { DeckCard } from '../lib/deck';

/**
 * What the machine has actually recorded by the time this screen appears: the participant turned
 * cards (SELECTION), pressed RESONATES (RESONANCE), and the lifecycle call that records it has
 * already succeeded before Stage 07 mounts (RESPONSE). Nothing here is measured; no latency is claimed.
 */
const ANNOTATIONS: Array<{ text: string; at: number; desktop: string }> = [
  { text: 'SELECTION: VOLUNTARY', at: 3, desktop: '-left-2 top-6 -translate-x-full' },
  { text: 'RESPONSE: RECORDED', at: 4, desktop: '-left-2 bottom-10 -translate-x-full' },
  { text: 'RESONANCE: SELF-REPORTED', at: 5, desktop: '-right-2 top-16 translate-x-full' },
  { text: 'VALIDATION: PARTICIPANT-SUPPLIED', at: 6, desktop: '-right-2 top-28 translate-x-full' },
];

/**
 * Stage 07 — THE BREAK.
 * Not a hacker glitch: the backstage infrastructure suddenly becomes visible.
 * Hard cuts, typographic replacement, spatial snapping, material collapse.
 */
export default function Stage07Break({
  card,
  onComplete,
  selectionCount = 1,
  turnCount,
  readingCount,
}: {
  card: DeckCard;
  onComplete: () => void;
  selectionCount?: number;
  turnCount?: number;
  readingCount?: number;
}) {
  const [step, setStep] = useState(0);

  useEffect(() => {
    // 1 card visible · 2 typo · 3 label changes · 4 texture dies · 5 serif→mono
    // 6 alignment snaps · 7 aesthetic collapses · 8 the Parrot was the performer
    // 9 the Silent Reader was the observer · 10 signals recorded · 11 the choice became data
    const delays = [600, 1200, 1800, 2400, 3000, 3600, 4200, 5000, 6200, 7600, 9000];
    const timers = delays.map((d, i) => window.setTimeout(() => setStep(i + 1), d));
    const done = window.setTimeout(onComplete, 11200);
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

      <div className={`min-h-[100dvh] flex ${step >= 3 ? 'items-start justify-start pl-4 sm:pl-[8%] md:pl-[14%] pt-[16%] sm:pt-[12%] md:pt-[18%] pb-40' : 'items-center justify-center'} transition-all`} style={{ transitionDuration: '250ms' }}>
        {/* the card the participant turned and reported as resonating */}
        <motion.div
          className="w-[min(56vw,210px)] md:w-[280px] aspect-[2/3] relative"
          layout
          transition={{ duration: 0.25, ease: [0.85, 0, 0.15, 1] }}
        >
          <motion.div
            className={`relative w-full h-full flex flex-col justify-between border p-2 ${
              step >= 6 ? 'items-start text-left' : 'items-center text-center'
            }`}
            animate={{
              borderColor: step >= 2 ? 'rgba(166,58,43,0.7)' : 'rgba(201,162,39,0.9)',
              backgroundColor: step >= 7 ? '#0a0a09' : step >= 2 ? '#0d0d0c' : '#10160f',
              boxShadow:
                step >= 7
                  ? '0 0 0 rgba(0,0,0,0)'
                  : step >= 2
                    ? '0 20px 40px rgba(0,0,0,0.8)'
                    : '0 40px 80px rgba(0,0,0,0.7)',
            }}
            transition={{ duration: 0.2 }}
          >
            <div className="font-mono text-[10px] tracking-[0.3em] pt-3 text-gold/80">
              № {String(card.id).padStart(2, '0')}
            </div>
            <div className="px-5">
              {/* beat 4 — the ornament dies; what remains is the record's own identifier */}
              {step >= 4 ? (
                <div className="font-mono text-[9px] tracking-[0.15em] text-crimson/80 break-all">{card.cardId}</div>
              ) : (
                <div className="text-3xl text-gold/90">{card.glyph}</div>
              )}
              {/* beat 5 — serif becomes mono */}
              <div
                className={`mt-2 leading-snug ${
                  step >= 5
                    ? `font-mono text-sm md:text-base tracking-[0.08em] uppercase ${step >= 7 ? 'text-parchment-dim' : 'text-parchment'}`
                    : 'font-display text-lg md:text-xl tracking-[0.14em] text-parchment'
                }`}
              >
                {card.title}
              </div>
              <p
                className={`mt-3 leading-relaxed ${
                  step >= 5
                    ? 'font-mono not-italic text-[11px] md:text-xs text-parchment-dim'
                    : 'font-serif italic text-xs md:text-sm text-parchment-dim'
                }`}
              >
                {card.statement}
              </p>
            </div>
            <div className="pb-3 font-mono text-[9px] tracking-[0.35em] text-parchment-faint/60">
              {step >= 6 ? `№ ${String(card.id).padStart(2, '0')} / 27` : 'THE TWENTY-SEVEN'}
            </div>
            {/* beat 7 — the card is shown as a machine record: scanlines on this object only */}
            {step >= 7 && <div className="crt-scan" aria-hidden="true" />}
          </motion.div>

          {/* archival status indicators — beside the card on wide screens */}
          {ANNOTATIONS.filter((a) => step >= a.at).map((a) => (
            <motion.div
              key={`d-${a.text}`}
              className={`absolute ${a.desktop} hidden md:block font-mono text-[9px] tracking-[0.25em] text-crimson/80 whitespace-nowrap`}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.15 }}
            >
              ▸ {a.text}
            </motion.div>
          ))}

          {/* the same annotations, stacked beneath the card on small screens */}
          <div className="absolute left-0 top-full mt-3 md:hidden space-y-1">
            {ANNOTATIONS.filter((a) => step >= a.at).map((a) => (
              <motion.div
                key={`m-${a.text}`}
                className="max-w-[calc(100vw-2rem)] font-mono text-[8px] sm:text-[9px] tracking-[0.12em] sm:tracking-[0.2em] leading-snug text-crimson/80 whitespace-normal break-words"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.15 }}
              >
                ▸ {a.text}
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* the words */}
      <div className="fixed inset-x-0 bottom-[4%] md:bottom-[12%] text-center space-y-2 md:space-y-3 px-6">
        <AnimatePresence>
          {step >= 8 && (
            <motion.div
              key="l1"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.08 }}
              className="font-mono text-sm md:text-2xl tracking-[0.25em] text-parchment"
            >
              THE PARROT WAS THE PERFORMER.
            </motion.div>
          )}
          {step >= 9 && (
            <motion.div
              key="l2"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.08 }}
              className="font-mono text-sm md:text-2xl tracking-[0.25em] text-crimson"
            >
              THE SILENT READER WAS THE OBSERVER.
            </motion.div>
          )}
          {step >= 10 && (
            <motion.div
              key="l3"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.08 }}
              className="font-mono text-[10px] md:text-xs tracking-[0.2em] text-parchment-dim"
            >
              WHILE YOU WERE TALKING, THE SYSTEM WAS RECORDING SIGNALS.
            </motion.div>
          )}
          {step >= 10 && (
            <motion.div
              key="signals"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.08, delay: 0.1 }}
              className="flex flex-wrap justify-center gap-x-6 gap-y-1 font-mono text-[9px] md:text-[10px] tracking-[0.2em] text-parchment-faint"
            >
              <span>SESSION LOCKED</span>
              {turnCount !== undefined && <span>TURNS RECORDED {String(turnCount).padStart(2, '0')}</span>}
              {readingCount !== undefined && <span>READINGS {readingCount}</span>}
              <span>CARDS SELECTED {String(selectionCount).padStart(2, '0')}</span>
              <span>RESONANCE PARTICIPANT-REPORTED</span>
            </motion.div>
          )}
          {step >= 11 && (
            <motion.div
              key="l4"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.08 }}
              className="pt-1 font-mono text-sm md:text-2xl tracking-[0.25em] text-parchment"
            >
              YOUR CHOICE BECAME DATA.
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
