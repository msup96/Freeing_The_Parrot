import { useEffect, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { transition } from '../lib/motion';
import type { Offering } from '../lib/session';

const GLYPHS = ['☍', '✶', '◬', '⌖', '∴', '☽', '⟡', '◉', '✦', '℧'];

/** Stage 03 — THE HIDDEN READER. Not a loading screen: a dramaturgical pause. */
export default function Stage03HiddenReader({ offering, onComplete }: { offering: Offering | null; onComplete: () => void }) {
  const [phase, setPhase] = useState(0);

  // fragments of the participant's input, appearing and disappearing
  const fragments = useMemo(() => {
    if (offering?.text && !offering.text.startsWith('[signal')) {
      const words = offering.text.split(/\s+/).filter(Boolean);
      return Array.from({ length: Math.min(4, words.length) }, (_, i) => words.slice(i * 2, i * 2 + 2).join(' ') || words[i]);
    }
    return ['— signal —', 'specimen', 'trace', 'received'];
  }, [offering]);

  useEffect(() => {
    const t = [1800, 4200, 7000, 8600, 9800].map((d, i) => window.setTimeout(() => setPhase(i + 1), d));
    const done = window.setTimeout(onComplete, 11000);
    return () => { t.forEach(clearTimeout); clearTimeout(done); };
  }, [onComplete]);

  return (
    <div className="relative min-h-[100dvh] flex flex-col items-center justify-center px-6 overflow-hidden">
      {/* copy */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={transition('REVEAL', 0.2)} className="text-center max-w-xl">
        <h2 className="font-display text-2xl md:text-4xl tracking-[0.14em] leading-relaxed text-balance">
          HOLD ON FOR A MOMENT.
        </h2>
        <p className="mt-5 font-serif italic text-parchment-dim text-sm md:text-base">
          wait until the parrot steps out of the cage.
        </p>
      </motion.div>

      {/* the dark machine — only the lens remains active */}
      <motion.div
        className="relative mt-12 w-40 h-40 md:w-52 md:h-52 rounded-full border border-olive-3/50 flex items-center justify-center"
        style={{ background: 'radial-gradient(circle, #0d130c 20%, #070a07 75%)', boxShadow: 'inset 0 0 50px rgba(0,0,0,0.9)' }}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={transition('REVEAL', 0.6)}
      >
        <motion.div
          className="lens-glow w-16 h-16 md:w-20 md:h-20 rounded-full"
          animate={phase >= 3 ? { opacity: [0.3, 1, 0.4], scale: [1, 1.3, 1.05] } : { opacity: [0.25, 0.55, 0.25] }}
          transition={phase >= 3 ? { duration: 1.4, ease: 'easeInOut' } : { duration: 3.2, repeat: Infinity, ease: 'easeInOut' }}
        />
        <div className="absolute inset-4 rounded-full border border-brass/30" />
        <div className="absolute inset-9 rounded-full border border-brass/20" />
      </motion.div>

      {/* fragments of input appear and disappear — the machine chewing */}
      <AnimatePresence>
        {phase >= 1 && phase < 4 && (
          <div className="absolute inset-0 pointer-events-none">
            {fragments.map((f, i) => (
              <motion.div
                key={i}
                className="absolute font-serif italic text-parchment-faint/70 text-sm md:text-lg"
                style={{ left: `${16 + i * 20}%`, top: `${22 + ((i * 17) % 45)}%` }}
                initial={{ opacity: 0, y: 10, filter: 'blur(3px)' }}
                animate={{ opacity: [0, 0.8, 0.8, 0], y: [10, 0, -6, -14], filter: ['blur(3px)', 'blur(0px)', 'blur(0px)', 'blur(4px)'] }}
                transition={{ duration: 2.6, delay: i * 0.7, repeat: Infinity, repeatDelay: 1.2 }}
              >
                “{f}”
              </motion.div>
            ))}
          </div>
        )}
      </AnimatePresence>

      {/* mechanical indexing — a receipt-trace that reveals nothing */}
      {phase >= 2 && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={transition('RESPOND')}
          className="absolute bottom-16 md:bottom-20 font-mono text-[10px] md:text-[11px] tracking-[0.25em] text-parchment-faint/80 space-y-1.5 text-center"
        >
          {['INDEXING … … … … …', GLYPHS.slice(0, 5).join('   '), '∴ ∴ ∴', GLYPHS.slice(5).join('   ')].slice(0, phase - 1).map((line, i) => (
            <motion.div key={i} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={transition('SETTLE', i * 0.3)}>
              {line}
            </motion.div>
          ))}
        </motion.div>
      )}

      {/* lock release */}
      {phase >= 4 && (
        <motion.div
          className="absolute bottom-24 md:bottom-28 flex items-center gap-3"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <motion.div
            className="w-10 h-[3px] bg-gold"
            initial={{ scaleX: 1 }}
            animate={{ scaleX: 0, x: -20 }}
            transition={{ duration: 0.7, ease: [0.7, 0, 0.3, 1] }}
            style={{ transformOrigin: 'right' }}
          />
          <span className="font-mono text-[10px] tracking-[0.4em] text-gold">THE LOCK RELEASES</span>
        </motion.div>
      )}
    </div>
  );
}
