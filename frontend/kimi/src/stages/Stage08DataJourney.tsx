import { useEffect, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { transition } from '../lib/motion';
import { DECK } from '../lib/deck';
import type { Session } from '../lib/session';

function EvidenceRow({ label, children, delay = 0 }: { label: string; children: React.ReactNode; delay?: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-60px' }}
      transition={transition('ARCHIVE', delay)}
      className="border-t border-parchment/10 py-6 md:py-8 grid md:grid-cols-[220px_1fr] gap-3 md:gap-8"
    >
      <div className="font-mono text-[10px] md:text-[11px] tracking-[0.35em] text-crimson/90">{label}</div>
      <div className="font-mono text-xs md:text-sm text-parchment/85 leading-relaxed">{children}</div>
    </motion.div>
  );
}

function Connector() {
  return (
    <motion.div
      initial={{ scaleY: 0 }}
      whileInView={{ scaleY: 1 }}
      viewport={{ once: true }}
      transition={{ duration: 0.6 }}
      className="ml-[2px] md:ml-[109px] w-px h-8 bg-crimson/50 origin-top"
    />
  );
}

/** A pinned archival specimen tile */
function WallTile({ index, session, self }: { index: number; session: Session; self?: boolean }) {
  const card = session.cardId ? DECK.find((c) => c.id === session.cardId) : null;
  return (
    <motion.div
      initial={{ opacity: 0, y: 18, rotate: self ? 0 : (index % 3) - 1 }}
      animate={{ opacity: 1, y: 0 }}
      transition={transition('ARCHIVE', self ? 0.2 : index * 0.05)}
      className={`relative aspect-[3/4] border ${self ? 'border-gold/70' : 'border-parchment/15'} p-2 flex flex-col justify-between overflow-hidden`}
      style={{ background: self ? '#141a13' : '#0e0e0d' }}
    >
      <div className={`font-mono text-[8px] tracking-[0.25em] ${self ? 'text-gold' : 'text-parchment-faint/70'}`}>
        № {String(index + 1).padStart(3, '0')}
      </div>
      {self && session.offering?.imageDataUrl ? (
        <img src={session.offering.imageDataUrl} alt="" className="absolute inset-0 w-full h-full object-cover opacity-60" />
      ) : self && session.offering?.text ? (
        <p className="font-serif italic text-[10px] text-parchment-dim leading-snug line-clamp-4 px-1">
          “{session.offering.text}”
        </p>
      ) : (
        <div className="font-mono text-[9px] text-parchment-faint/50 tracking-[0.2em] px-1">— specimen —</div>
      )}
      <div className={`relative font-mono text-[8px] tracking-[0.2em] ${self ? 'text-parchment/90' : 'text-parchment-faint/50'}`}>
        {self && card ? `CARD ${String(card.id).padStart(2, '0')}` : 'ARCHIVED'}
      </div>
      <div className="absolute top-2 right-2 w-1.5 h-1.5 rounded-full bg-crimson/60" />
    </motion.div>
  );
}

/** Stage 08 — DATA JOURNEY · WALL OF FAME · CONSENT */
export default function Stage08DataJourney({ session, onConsent }: { session: Session; onConsent: (c: 'private' | 'wall') => void }) {
  const [phase, setPhase] = useState(0); // 0 journey, 1 wall, 2 consent
  const card = session.cardId ? DECK.find((c) => c.id === session.cardId)! : null;
  const firstWords = useMemo(() => {
    const t = session.turns.find((t) => t.role === 'participant');
    return t ? `“${t.text.slice(0, 80)}${t.text.length > 80 ? '…' : ''}”` : '—';
  }, [session.turns]);

  useEffect(() => {
    const t1 = window.setTimeout(() => setPhase(1), 2600);
    const t2 = window.setTimeout(() => setPhase(2), 5200);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, []);

  return (
    <div className="relative min-h-[100dvh] bg-[#0a0a09] px-6 md:px-0 py-24">
      <div className="max-w-3xl mx-auto">
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={transition('REVEAL')} className="mb-10">
          <div className="font-mono text-[10px] tracking-[0.4em] text-crimson mb-4">SESSION № 027 — FULL TRACE</div>
          <h2 className="font-mono text-xl md:text-3xl tracking-[0.15em] text-parchment">WHAT ACTUALLY HAPPENED</h2>
        </motion.div>

        {/* ——— trace → connects → resolves → labels ——— */}
        <EvidenceRow label="WHAT YOU GAVE">
          {session.offering ? (
            <>
              channel: <span className="text-gold">{session.offering.channel.toUpperCase()}</span>
              {session.offering.text && <span className="block mt-2 text-parchment-dim">“{session.offering.text}”</span>}
              {session.offering.imageDataUrl && (
                <img src={session.offering.imageDataUrl} alt="offering specimen" className="mt-3 w-28 md:w-36 border border-parchment/20" />
              )}
            </>
          ) : (
            '—'
          )}
        </EvidenceRow>
        <Connector />
        <EvidenceRow label="WHAT WAS RECORDED">
          the offering and live conversation record are available to this session.
          <span className="block mt-2 text-parchment-dim">
            hidden telemetry and analytical fields are intentionally withheld.
          </span>
        </EvidenceRow>
        <Connector />
        <EvidenceRow label="WHAT WAS INTERPRETED">
          the live Parrot response came from the session API. A participant-facing
          reveal contract is not available in this phase.
          <span className="block mt-2 text-parchment-dim">your first words back to you: {firstWords}</span>
        </EvidenceRow>
        <Connector />
        <EvidenceRow label="WHAT WAS CONSTRUCTED">
          no participant profile is fabricated by the Kimi adapter.
          <span className="block mt-2 text-parchment-dim">
            backend-supported reveal data must be supplied before this section can claim construction.
          </span>
        </EvidenceRow>
        <Connector />
        <EvidenceRow label="WHAT YOU CHOSE">
          {card ? (
            <>
              CARD {String(card.id).padStart(2, '0')} — {card.title}
              <span className="block mt-1 text-parchment-dim italic font-serif">“{card.statement}”</span>
            </>
          ) : (
            '—'
          )}
        </EvidenceRow>
      </div>

      {/* ——— Wall of Fame ——— */}
      <AnimatePresence>
        {phase >= 1 && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={transition('REVEAL')} className="max-w-4xl mx-auto mt-20 md:mt-28">
            <div className="font-mono text-[10px] tracking-[0.4em] text-crimson mb-2">THE WALL OF FAME</div>
            <p className="font-mono text-[11px] text-parchment-faint tracking-[0.15em] mb-8">specimens pinned where the theatre used to be</p>
            <div className="grid grid-cols-3 md:grid-cols-6 gap-2 md:gap-3">
              {Array.from({ length: 12 }, (_, i) => (
                <WallTile key={i} index={i} session={session} />
              ))}
              {/* the participant's material, waiting for a decision */}
              <WallTile index={26} session={session} self />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ——— Consent — almost still ——— */}
      <AnimatePresence>
        {phase >= 2 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 1.6 }}
            className="max-w-3xl mx-auto mt-24 md:mt-32 mb-16 text-center border-t border-parchment/10 pt-16"
          >
            <p className="font-mono text-sm md:text-lg tracking-[0.25em] text-parchment leading-relaxed text-balance">
              DO YOU CONSENT YOUR DATA<br />TO BE ADDED TO THE WALL OF FAME?
            </p>
            <p className="mt-5 font-mono text-[10px] tracking-[0.2em] text-parchment-faint leading-loose">
              you now know what happened. therefore this consent has meaning.
            </p>
            <div className="mt-10 flex flex-col md:flex-row items-center justify-center gap-4 md:gap-8">
              <button
                className="brass-button px-8 py-4 min-h-[44px] min-w-[220px]"
                onClick={() => onConsent('private')}
              >
                KEEP PRIVATE
              </button>
              <button
                className="brass-button px-8 py-4 min-h-[44px] min-w-[220px]"
                onClick={() => onConsent('wall')}
              >
                ADD TO WALL OF FAME
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
