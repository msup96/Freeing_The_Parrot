import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Apparatus } from './Stage01Apparatus';
import { transition } from '../lib/motion';
import type { Session } from '../lib/session';

/** Stage 09 — EXIT. An afterimage, not a congratulations screen. */
export default function Stage09Exit({ session, onRestart }: { session: Session; onRestart: () => void }) {
  const [phase, setPhase] = useState(0);
  const priv = session.consent === 'private';
  const card = session.selectedCard;

  useEffect(() => {
    const t = [2200, 4600, 7000, 9200, 11400].map((d, i) => window.setTimeout(() => setPhase(i + 1), d));
    return () => t.forEach(clearTimeout);
  }, []);

  return (
    <div className="relative min-h-[100dvh] flex flex-col items-center justify-center px-6 overflow-hidden">
      {/* private: material disappears — not "DELETE SUCCESSFUL" */}
      {priv && phase < 3 && (
        <div className="absolute inset-0 flex items-center justify-center gap-8 md:gap-16 pointer-events-none">
          {[
            session.offering?.text ? `“${session.offering.text.slice(0, 40)}…”` : 'specimen',
            card ? card.title : 'trace',
            'session № 027',
          ].map((label, i) => (
            <motion.div
              key={i}
              className="font-mono text-[9px] md:text-[10px] tracking-[0.3em] text-parchment-faint text-center max-w-[120px]"
              initial={{ opacity: 0, y: 10 }}
              animate={phase >= 1 ? { opacity: 0, y: -14, filter: 'blur(4px)' } : { opacity: 0.85, y: 0 }}
              transition={
                phase >= 1
                  ? { duration: 1.1, delay: i * 0.45, ease: [0.45, 0, 0.1, 1] }
                  : { duration: 0.8, delay: 0.4 + i * 0.3 }
              }
            >
              {label}
            </motion.div>
          ))}
        </div>
      )}
      {priv && phase >= 2 && phase < 3 && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="absolute font-mono text-[10px] tracking-[0.4em] text-parchment-faint">
          SURFACE: EMPTY
        </motion.div>
      )}

      {/* wall: one tile among many */}
      {!priv && phase < 3 && (
        <motion.div
          initial={{ opacity: 0, scale: 1.4 }}
          animate={{ opacity: 1, scale: 0.5 }}
          transition={{ duration: 2.4, ease: [0.16, 1, 0.3, 1] }}
          className="absolute flex flex-col items-center gap-3 pointer-events-none"
        >
          <div className="w-40 aspect-[3/4] border border-gold/50 bg-forest-2 p-3 flex flex-col justify-between">
            <span className="font-mono text-[9px] tracking-[0.25em] text-gold">№ 027</span>
            <span className="font-serif italic text-[11px] text-parchment-dim">
              {session.offering?.text ? `“${session.offering.text.slice(0, 48)}”` : 'specimen'}
            </span>
            <span className="font-mono text-[8px] tracking-[0.2em] text-parchment-faint">ARCHIVED</span>
          </div>
          {phase >= 2 && (
            <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="font-mono text-[10px] tracking-[0.4em] text-parchment-faint">
              ONE TILE AMONG MANY
            </motion.span>
          )}
        </motion.div>
      )}

      {/* the apparatus returns — lens dims — cage closes — quiet */}
      <AnimatePresence>
        {phase >= 3 && (
          <motion.div
            className="w-[min(60vw,240px)] md:w-[300px]"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={transition('EXIT')}
          >
            <motion.div
              animate={phase >= 4 ? { filter: 'brightness(0.45)' } : {}}
              transition={{ duration: 2.2, ease: [0.45, 0, 0.1, 1] }}
            >
              <Apparatus intensity={phase >= 4 ? 0.25 : 0.8} />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* fade to black — afterimage */}
      {phase >= 5 && (
        <motion.div
          className="fixed inset-0 z-[70] bg-black flex flex-col items-center justify-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 2.4, ease: [0.45, 0, 0.1, 1] }}
        >
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.6, duration: 2 }}
            className="text-center"
          >
            <div className="font-mono text-[10px] tracking-[0.5em] text-parchment-faint/70">FORTUNA VIDET OMNIA</div>
            <div className="mt-3 font-serif italic text-xs text-parchment-faint/50">fortune sees everything</div>
            <p className="mx-auto mt-8 max-w-sm font-serif text-xs leading-relaxed text-parchment-faint/60">
              Freeing the Parrot turns one consented session into a reflective portrait—your words, choices, and signals remain a conversation, not a fixed identity.
            </p>
            <button
              onClick={onRestart}
              className="mt-14 font-mono text-[10px] tracking-[0.45em] text-parchment-faint hover:text-gold transition-colors duration-700 min-h-[44px] px-6"
            >
              BEGIN AGAIN
            </button>
          </motion.div>
        </motion.div>
      )}
    </div>
  );
}
