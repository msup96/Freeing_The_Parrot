import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { transition, MECHANICAL } from '../lib/motion';

interface ApparatusProps {
  /** 0 = dark/off, 1 = idle, 2 = listening/awake */
  intensity?: number;
  awakened?: boolean;
  className?: string;
}

/**
 * The Apparatus — one machine, viewed from different sides.
 * States are achieved with light, weight-shift and stillness, never decoration.
 */
export function Apparatus({ intensity = 1, awakened = false, className = '' }: ApparatusProps) {
  return (
    <div className={`relative ${className}`}>
      {/* ambient halo */}
      <motion.div
        className="absolute inset-[-20%] rounded-full"
        style={{
          background:
            'radial-gradient(circle, rgba(56,71,50,0.55) 0%, rgba(56,71,50,0.12) 45%, transparent 70%)',
        }}
        animate={{ opacity: [0.7, 1, 0.7] }}
        transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
      />
      {/* the machine */}
      <motion.img
        src="/assets/apparatus-front.png"
        alt="The Apparatus — a museum fortune-telling machine with the structural suggestion of a parrot"
        className="relative z-10 w-full h-auto select-none"
        draggable={false}
        initial={false}
        animate={
          awakened
            ? { rotate: [-0.4, 0.4, -0.4], y: [0, -6, 0], scale: 1.02 }
            : { rotate: [0, 0.35, 0, -0.25, 0], y: [0, -4, 0] }
        }
        transition={
          awakened
            ? { duration: 5.2, repeat: Infinity, ease: 'easeInOut' }
            : { duration: 7.5, repeat: Infinity, ease: [0.45, 0, 0.55, 1], times: [0, 0.35, 0.55, 0.8, 1] }
        }
        style={{
          filter: `brightness(${0.55 + intensity * 0.45})`,
          WebkitMaskImage: 'radial-gradient(ellipse 62% 68% at 50% 46%, black 52%, transparent 82%)',
          maskImage: 'radial-gradient(ellipse 62% 68% at 50% 46%, black 52%, transparent 82%)',
        }}
      />
      {/* lens light — aligned to the machine's eye (≈41% x, 13% y of the asset) */}
      <motion.div
        className="lens-glow absolute z-20 rounded-full pointer-events-none"
        style={{ left: '30%', top: '4%', width: '22%', aspectRatio: '1' }}
        animate={{
          opacity: [0.25 * intensity, 0.85 * intensity, 0.35 * intensity, 0.7 * intensity],
          scale: awakened ? [1, 1.25, 1] : [1, 1.06, 1],
        }}
        transition={{ duration: awakened ? 2.6 : 5.5, repeat: Infinity, ease: 'easeInOut' }}
      />
      {/* environmental shadow */}
      <motion.div
        className="absolute -bottom-4 left-1/2 -translate-x-1/2 w-[70%] h-8 rounded-[50%] bg-black/70 blur-xl"
        animate={{ scaleX: awakened ? [1, 0.94, 1] : [1, 0.97, 1], opacity: [0.8, 0.6, 0.8] }}
        transition={{ duration: awakened ? 5.2 : 7.5, repeat: Infinity, ease: 'easeInOut' }}
      />
    </div>
  );
}

/** Stage 01 — APPARATUS. "Something is waiting for me." */
export default function Stage01Apparatus({ onEnter }: { onEnter: () => void }) {
  const [phase, setPhase] = useState(0); // 0 darkness, 1 silhouette, 2 emerged, 3 lens, 4 type, 5 enter
  const [pressing, setPressing] = useState(false);

  useEffect(() => {
    const t = [900, 2200, 3400, 4600, 5600].map((d, i) =>
      window.setTimeout(() => setPhase(i + 1), d),
    );
    return () => t.forEach(clearTimeout);
  }, []);

  const handleEnter = () => {
    if (pressing) return;
    setPressing(true);
    // the apparatus responds before the screen changes — the lens illuminates
    window.setTimeout(onEnter, 750);
  };

  return (
    <div className="relative min-h-[100dvh] flex flex-col items-center justify-center overflow-hidden px-6 pt-8 md:pt-0">
      {/* faint silhouette → emergence */}
      <motion.div
        className="w-[min(62vw,280px,30dvh)] md:w-[min(38vw,430px)]"
        initial={{ opacity: 0, y: 30, filter: 'brightness(0) blur(6px)' }}
        animate={
          phase >= 2
            ? { opacity: 1, y: 0, filter: 'brightness(1) blur(0px)' }
            : phase >= 1
              ? { opacity: 0.5, y: 12, filter: 'brightness(0.15) blur(2px)' }
              : {}
        }
        transition={{ duration: 1.4, ease: [0.45, 0, 0.1, 1] }}
      >
        <Apparatus intensity={pressing ? 2 : phase >= 3 ? 1 : 0.4} />
      </motion.div>

      {/* typography settles */}
      <motion.div
        className="mt-6 md:mt-10 text-center"
        initial={{ opacity: 0, y: 14 }}
        animate={phase >= 4 ? { opacity: 1, y: 0 } : {}}
        transition={transition('REVEAL')}
      >
        <div className="meta-label mb-3">AN INSTRUMENT FOR BEING READ</div>
        <h1 className="font-display text-4xl md:text-6xl tracking-[0.12em] text-parchment text-balance">
          FREEING THE PARROT
        </h1>
        <div className="gold-rule w-40 md:w-64 mx-auto mt-5" />
        <p className="mt-4 font-serif italic text-parchment-dim text-sm md:text-base">
          the machine is already listening
        </p>
      </motion.div>

      {/* ENTER — a physical control */}
      <motion.div
        className="mt-6 md:mt-10 w-full flex flex-col items-center pb-10 md:pb-24"
        initial={{ opacity: 0 }}
        animate={phase >= 5 ? { opacity: 1 } : {}}
        transition={transition('SETTLE')}
      >
        <motion.button
          className="brass-button self-center px-10 md:px-14 py-4 min-h-[44px]"
          onClick={handleEnter}
          whileHover={{ y: -1 }}
          whileTap={{ y: 2 }}
          transition={{ duration: 0.12, ease: MECHANICAL }}
        >
          ENTER
        </motion.button>

        <p className="mx-auto mt-8 w-full max-w-[72ch] px-7 md:px-10 text-center font-serif italic text-[0.78rem] md:text-sm leading-[1.8] text-parchment-dim text-pretty">
          Freeing the Parrot is an installation about the feeling of being understood by a machine. It borrows Kili
          Josiyam, where a parrot picks a card to tell a fortune, and replaces the parrot with software. We made it to
          ask how much of that meaning comes from the system, and how much we bring ourselves.
        </p>
      </motion.div>

      {/* lens flash on press */}
      {pressing && (
        <motion.div
          className="fixed inset-0 z-50 pointer-events-none lens-glow"
          initial={{ opacity: 0 }}
          animate={{ opacity: [0, 0.9, 0] }}
          transition={{ duration: 0.75, ease: 'easeOut' }}
        />
      )}
    </div>
  );
}
