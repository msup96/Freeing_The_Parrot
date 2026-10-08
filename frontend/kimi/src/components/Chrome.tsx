import { motion } from 'framer-motion';
import { STAGE_META } from '../lib/session';
import { transition } from '../lib/motion';

/** Fixed atmosphere: paper grain + museum vignette */
export function Atmosphere() {
  return (
    <>
      <div className="vignette" />
      <div className="grain-overlay" />
    </>
  );
}

/** Gold measurement ticks along the left and right edges */
function MeasurementMarks() {
  const ticks = Array.from({ length: 24 });
  return (
    <>
      {(['left-3', 'right-3'] as const).map((side) => (
        <div key={side} className={`fixed top-0 bottom-0 ${side} z-40 hidden md:flex flex-col justify-between py-10 pointer-events-none`}>
          {ticks.map((_, i) => (
            <div
              key={i}
              className={i % 6 === 0 ? 'w-3 h-px bg-gold/50' : 'w-1.5 h-px bg-gold/25'}
            />
          ))}
        </div>
      ))}
    </>
  );
}

/** Catalogue metadata frame — present on every stage, in the installation voice */
export function Chrome({ stage, broken }: { stage: number; broken?: boolean }) {
  const meta = STAGE_META[stage];
  return (
    <>
      <MeasurementMarks />
      <motion.header
        className={`fixed top-0 inset-x-0 z-40 ${stage === 1 ? 'hidden md:flex' : 'flex'} items-start justify-between px-5 md:px-12 pt-5 md:pt-7 pointer-events-none`}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={transition('REVEAL', 0.4)}
      >
        <div className={broken ? 'font-mono text-[10px] md:text-[11px] tracking-[0.35em] uppercase text-crimson/80' : 'meta-label'}>
          {broken ? `SESSION / TRACE — 027` : 'APPARATUS / ARCHIVE'}
        </div>
        <div className="meta-label text-right">
          {broken ? 'NO. 027' : 'NO. 027'}
        </div>
      </motion.header>
      <motion.footer
        className={`fixed bottom-0 inset-x-0 z-40 ${stage === 1 ? 'hidden md:flex' : 'flex'} items-end justify-between px-5 md:px-12 pb-5 md:pb-7 pointer-events-none`}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={transition('REVEAL', 0.6)}
      >
        <div className="meta-label">{meta ? `${meta.index} — ${meta.name}` : ''}</div>
        <div className={`meta-label ${broken ? 'text-crimson/80' : ''}`}>{meta?.world ?? ''}</div>
      </motion.footer>
    </>
  );
}
