import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { transition } from '../lib/motion';
import type { ChatTurn, Session } from '../lib/session';

function EvidenceRow({
  label,
  children,
  sub,
  delay = 0,
}: {
  label: string;
  children: React.ReactNode;
  sub?: React.ReactNode;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-40px' }}
      transition={transition('ARCHIVE', delay)}
      className="border-t border-parchment/10 py-6 md:py-8 grid md:grid-cols-[220px_1fr] gap-3 md:gap-8"
    >
      <div className="font-mono text-[10px] md:text-[11px] tracking-[0.35em] text-crimson/90 uppercase">{label}</div>
      <div className="font-mono text-xs md:text-sm text-parchment/90 leading-relaxed">
        {children}
        {sub && <span className="block mt-2 font-mono text-[11px] text-parchment-dim tracking-wide">{sub}</span>}
      </div>
    </motion.div>
  );
}

function Connector() {
  return (
    <motion.div
      initial={{ scaleY: 0 }}
      whileInView={{ scaleY: 1 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5 }}
      className="ml-[2px] md:ml-[109px] w-px h-6 bg-crimson/40 origin-top"
    />
  );
}

function MachineTable({ rows }: { rows: Array<[string, unknown]> }) {
  return (
    <div className="grid gap-2 border border-parchment/10 p-3 text-[10px]">
      {rows.map(([label, value]) => (
        <div key={label} className="grid grid-cols-[minmax(110px,0.4fr)_1fr] gap-3 border-b border-parchment/5 pb-2 last:border-0 last:pb-0">
          <span className="text-crimson/80 uppercase">{label.replaceAll('_', ' ')}</span>
          <span className="break-words text-parchment-dim">{value === null || value === undefined ? 'NOT COMPUTED' : typeof value === 'object' ? JSON.stringify(value) : String(value)}</span>
        </div>
      ))}
    </div>
  );
}

function ArtifactList({ title, items }: { title: string; items: unknown[] }) {
  return (
    <div className="mt-4">
      <div className="mb-2 text-[9px] uppercase tracking-[0.22em] text-crimson/80">{title}</div>
      {items.length ? <div className="space-y-2">{items.map((item, index) => <MachineTable key={index} rows={Object.entries(item as Record<string, unknown>)} />)}</div> : <div className="text-parchment-faint">NOT AVAILABLE IN THIS SESSION</div>}
    </div>
  );
}

/** A pinned archival specimen tile on the Wall of Fame */
function WallTile({
  index,
  title,
  text,
  archetype,
  self = false,
  selfImage,
}: {
  index: number;
  title: string;
  text: string;
  archetype?: string;
  self?: boolean;
  selfImage?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 18, rotate: self ? 0 : (index % 3) - 1 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={transition('ARCHIVE', self ? 0.2 : (index % 6) * 0.06)}
      className={`relative aspect-[3/4] border ${
        self ? 'border-gold shadow-[0_0_24px_rgba(201,162,39,0.25)]' : 'border-parchment/15'
      } p-3 flex flex-col justify-between overflow-hidden`}
      style={{ background: self ? '#141a13' : '#0e0e0d' }}
    >
      <div className="flex items-center justify-between">
        <div className={`font-mono text-[8px] tracking-[0.25em] ${self ? 'text-gold' : 'text-parchment-faint/70'}`}>
          № {String(index + 1).padStart(3, '0')}
        </div>
        {archetype && (
          <span className="font-mono text-[7px] tracking-[0.15em] text-parchment-faint uppercase">
            {archetype}
          </span>
        )}
      </div>

      {self && selfImage ? (
        <img src={selfImage} alt="" className="absolute inset-0 w-full h-full object-cover opacity-50" />
      ) : (
        <div className="my-auto py-1">
          <p className="font-mono text-[9px] tracking-wider text-gold/90 uppercase line-clamp-1 mb-1 font-semibold">
            {title}
          </p>
          <p className="font-serif italic text-[10px] text-parchment-dim leading-snug line-clamp-4">
            {text ? `“${text}”` : '— specimen —'}
          </p>
        </div>
      )}

      <div className="flex items-center justify-between border-t border-parchment/10 pt-1.5">
        <div className={`font-mono text-[8px] tracking-[0.2em] ${self ? 'text-gold' : 'text-parchment-faint/60'}`}>
          {self ? 'YOUR TRACE' : 'ARCHIVED'}
        </div>
        <div className={`w-1.5 h-1.5 rounded-full ${self ? 'bg-gold animate-pulse' : 'bg-crimson/60'}`} />
      </div>
    </motion.div>
  );
}

/** Stage 08 — DATA JOURNEY · WALL OF FAME · CONSENT */
export default function Stage08DataJourney({
  session,
  onConsent,
}: {
  session: Session;
  onConsent: (c: 'private' | 'wall') => void;
}) {
  const [phase, setPhase] = useState(0); // 0 layers, 1 wall, 2 consent
  const card = session.selectedCard;
  const reveal = session.reveal;

  useEffect(() => {
    const t1 = window.setTimeout(() => setPhase(1), 2000);
    const t2 = window.setTimeout(() => setPhase(2), 4000);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, []);

  // Only backend-provided specimens are eligible for the wall. The participant's
  // deck is session material, not a collection of other participants.
  const wallSpecimens = reveal?.wall_specimens ?? [];
  const sessionIdShort = session.sessionId ? session.sessionId.slice(-8) : '—';

  return (
    <div className="relative min-h-[100dvh] bg-[#0a0a09] px-6 md:px-0 py-24 text-parchment selection:bg-crimson selection:text-parchment">
      <div className="max-w-3xl mx-auto">
        {/* Title header */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={transition('REVEAL')} className="mb-12">
          <div className="font-mono text-[10px] tracking-[0.45em] text-crimson mb-3">
            SESSION № {sessionIdShort.toUpperCase()} — DECONSTRUCTION
          </div>
          <h2 className="font-mono text-2xl md:text-4xl tracking-[0.16em] text-parchment">
            WHAT ACTUALLY HAPPENED
          </h2>
          <p className="mt-3 font-serif italic text-xs md:text-sm text-parchment-dim">
            The Parrot was the performer. The Silent Reader was the observer.
          </p>
        </motion.div>

        <div className="mb-10 border border-crimson/20 bg-black/30 p-4 font-mono text-[10px] tracking-[0.16em] text-parchment-faint" aria-label="Provenance path">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
            {['RAW', 'OBSERVED', 'INTERPRETED', 'INFERRED', 'VALIDATED'].map((level, index) => (
              <span key={level} className="flex items-center gap-3">
                <span className={index === 4 ? 'text-gold' : 'text-crimson/80'}>{level}</span>
                {index < 4 && <span className="text-crimson/50">→</span>}
              </span>
            ))}
          </div>
          <div className="mt-3 text-[9px] text-parchment-faint/70">ONE SESSION · {session.turns.length} TURN{session.turns.length === 1 ? '' : 'S'} · SERVER REVEAL DATA ONLY</div>
        </div>

        {/* ——— MACHINE TRANSFORMATION ——— */}
        {reveal && (
          <motion.section
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={transition('REVEAL', 0.25)}
            className="mb-10 border border-crimson/30 bg-[#080b0a] p-4 md:p-6 font-mono text-[10px] tracking-[0.12em]"
            aria-label="Machine transformation"
          >
            <div className="flex items-center justify-between border-b border-crimson/20 pb-3 text-crimson">
              <span>MAGIC → MECHANISM</span>
              <span className="text-parchment-faint/60">SESSION-LOCAL / READ-ONLY</span>
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-3 text-parchment-dim">
              <div><span className="text-crimson/80">RAW TEXT</span><br />{reveal.machine_transformation?.raw_text?.character_count ?? 0} chars / {reveal.machine_transformation?.raw_text?.turn_count ?? session.turns.length} turns</div>
              <div><span className="text-crimson/80">OBSERVED</span><br />{reveal.observed_signals?.length ?? 0} evidence signals</div>
              <div><span className="text-crimson/80">INFERRED</span><br />{reveal.machine_transformation?.inference_ids?.length ?? 0} bounded hypotheses</div>
            </div>
            <div className="mt-4 border-t border-crimson/10 pt-3 text-parchment-faint/80">
              {reveal.machine_transformation?.evidence_ids?.join(' · ') || 'No evidence identifiers returned'}
            </div>
          </motion.section>
        )}

        {/* ——— ACTUAL ANALYTICAL ARTIFACTS ——— */}
        {reveal?.analytical_artifacts && (
          <EvidenceRow label="WHAT THE MACHINE ACTUALLY MEASURED" sub="Authoritative server artifacts; values are session measurements, not psychological truths.">
            <ArtifactList title="LINGUISTIC TURN MEASUREMENTS" items={(reveal.analytical_artifacts.linguistic?.turn_sequence as unknown[]) ?? []} />
            <ArtifactList title="TEMPORAL / BEHAVIOURAL TURN MEASUREMENTS" items={(reveal.analytical_artifacts.temporal?.turn_sequence as unknown[]) ?? []} />
            <MachineTable rows={Object.entries(reveal.analytical_artifacts.linguistic ?? {}).filter(([key]) => key !== 'turn_sequence')} />
            <MachineTable rows={Object.entries(reveal.analytical_artifacts.temporal ?? {}).filter(([key]) => key !== 'turn_sequence')} />
          </EvidenceRow>
        )}

        {reveal?.observed_signals && (
          <EvidenceRow label="EVIDENCE → INFERENCE" sub="Each record preserves its value, source events, provenance, scope, and limitations.">
            <ArtifactList title="EVIDENCE RECORDS" items={reveal.observed_signals} />
            <ArtifactList title="INFERENCE RECORDS" items={reveal.inference_records ?? []} />
            <MachineTable rows={Object.entries(reveal.analytical_artifacts?.deep_reader_packet ?? {})} />
          </EvidenceRow>
        )}

        {reveal?.card_provenance && (
          <EvidenceRow label="HOW THE 27 READINGS WERE CONSTRUCTED" sub="Card provenance is exposed without revealing internal prompt text.">
            <ArtifactList title={`${reveal.card_provenance.length} CARD PROVENANCE RECORDS`} items={reveal.card_provenance} />
          </EvidenceRow>
        )}

        {/* ——— NAVARASA TRAJECTORY ——— */}
        {reveal && (
          <EvidenceRow
            label="NAVARASA TRAJECTORY"
            sub={reveal.navarasa_trajectory?.dominant_rasa?.label
              ? `Dominant detected label: ${reveal.navarasa_trajectory.dominant_rasa.label}. This is an interaction signal, not a trait.`
              : 'No stable Rasa trajectory was supported by this session.'}
          >
            {reveal.navarasa_trajectory?.detected_sequence?.length
              ? reveal.navarasa_trajectory.detected_sequence.join(' → ')
              : 'INSUFFICIENT EVIDENCE FOR A STABLE RASA TRAJECTORY.'}
            <ArtifactList title="TURN-LEVEL NAVARASA OUTPUT" items={(reveal.analytical_artifacts?.navarasa?.turn_sequence as unknown[]) ?? []} />
            <MachineTable rows={Object.entries(reveal.analytical_artifacts?.navarasa ?? {}).filter(([key]) => key !== 'turn_sequence')} />
          </EvidenceRow>
        )}

        {/* ——— INTERACTION PROFILE ——— */}
        {reveal?.interaction_profile && (
          <EvidenceRow
            label="INTERACTION PROFILE"
            sub="What this interaction made computationally legible; not a permanent or psychological profile."
          >
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              {Object.entries(reveal.interaction_profile).map(([key, value]) => (
                <div key={key} className="border border-parchment/10 p-2">
                  <div className="text-[9px] uppercase text-crimson/80">{key.replaceAll('_', ' ')}</div>
                  <div className="mt-1 text-gold">{String(value)}</div>
                </div>
              ))}
            </div>
          </EvidenceRow>
        )}

        {/* ——— 1. WHAT YOU GAVE ——— */}
        <EvidenceRow
          label="WHAT YOU GAVE"
          sub="Direct physical inputs received across intake and conversational turns."
        >
          {session.offering ? (
            <div>
              <div className="flex items-center gap-2 mb-2 font-mono text-xs">
                <span>INTAKE MODALITY:</span>
                <span className="text-gold font-bold">{session.offering.channel.toUpperCase()}</span>
              </div>
              {session.offering.text && (
                <div className="border-l-2 border-gold/40 pl-3 py-1 my-2 font-serif italic text-parchment-dim">
                  “{session.offering.text}”
                </div>
              )}
              {session.offering.imageDataUrl && (
                <img
                  src={session.offering.imageDataUrl}
                  alt="offering specimen"
                  className="mt-3 w-32 md:w-44 border border-parchment/20"
                />
              )}
              {session.turns.length > 0 && (
                <div className="mt-3 text-xs text-parchment-dim font-mono">
                  {session.turns.filter((t: ChatTurn) => t.role === 'participant').length} statement(s) submitted to the Parrot.
                </div>
              )}
            </div>
          ) : (
            reveal?.what_you_gave || 'No participant input is available in this reveal.'
          )}
        </EvidenceRow>

        <Connector />

        {/* ——— 2. WHAT THE SYSTEM OBSERVED ——— */}
        <EvidenceRow
          label="WHAT THE SYSTEM OBSERVED"
          sub={reveal?.what_was_recorded_sub || 'Deterministic computational counts and timestamps preserved in the append-only event store.'}
        >
          {reveal?.what_the_system_observed || reveal?.what_was_recorded || 'The authoritative reveal did not provide an observation summary.'}
        </EvidenceRow>

        <Connector />

        {/* ——— 3. WHAT THE SYSTEM INTERPRETED ——— */}
        <EvidenceRow
          label="WHAT THE SYSTEM INTERPRETED"
          sub={reveal?.what_was_interpreted_sub || 'Derived solely from linguistic rhythm, vocabulary, and sentiment tone.'}
        >
          {reveal?.what_the_system_interpreted || reveal?.what_was_interpreted || 'No interpreted output was returned for this session.'}
        </EvidenceRow>

        <Connector />

        {/* ——— 4. WHAT THE SYSTEM INFERRED ——— */}
        <EvidenceRow
          label="WHAT THE SYSTEM INFERRED"
          sub={reveal?.what_was_constructed_sub || 'Hypotheses for reflection, combining archetype seeds with subjective completion.'}
        >
          {reveal?.what_the_system_inferred || reveal?.what_was_constructed || 'No inferred output was returned for this session.'}
          <span className="block mt-3 text-[11px] text-parchment-dim/80 border-l border-crimson/40 pl-3 italic">
            Notice: The apparatus did not diagnose you. It prepared mirrors designed to allow personal projection.
          </span>
        </EvidenceRow>

        <Connector />

        {/* ——— 5. WHAT YOU CHOSE ——— */}
        <EvidenceRow
          label="WHAT YOU CHOSE"
          sub={reveal?.what_you_chose?.disclaimer || 'Subjective validation reported by the participant. Not an objective diagnosis.'}
        >
          {card ? (
            <div>
              <div className="font-mono text-xs tracking-wider text-gold font-bold uppercase">
                CARD {String(card.id).padStart(2, '0')} — {card.title}
              </div>
              <div className="mt-1 font-serif italic text-parchment-dim">
                “{card.statement}”
              </div>
              <div className="mt-3 font-mono text-[10px] tracking-widest text-crimson/90">
                ▸ STATUS: RESONANCE MARKED BY PARTICIPANT
              </div>
            </div>
          ) : reveal?.what_you_chose ? (
            <div>
              <div className="font-mono text-xs tracking-wider text-gold font-bold uppercase">
                CARD {String(reveal.what_you_chose.card_index).padStart(2, '0')} — {reveal.what_you_chose.title}
              </div>
              <div className="mt-1 font-serif italic text-parchment-dim">
                “{reveal.what_you_chose.statement}”
              </div>
            </div>
          ) : (
            '—'
          )}
        </EvidenceRow>

        {reveal?.selection_pattern && (
          <EvidenceRow label="HOW YOUR SELECTIONS FORMED A PATTERN" sub="Recorded selection behavior only; RESONATES is participant-reported and is not validation.">
            <MachineTable rows={Object.entries(reveal.selection_pattern)} />
          </EvidenceRow>
        )}

        {/* ——— 6. WHAT WE CANNOT KNOW ——— */}
        {reveal?.what_we_cannot_know && (
          <>
            <Connector />
            <EvidenceRow
              label="WHAT WE CANNOT KNOW"
              sub="The sovereign boundary of machine observation."
            >
              <ul className="space-y-2 font-mono text-xs text-parchment-dim">
                {reveal.what_we_cannot_know.map((lim: string, i: number) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="text-crimson">✕</span>
                    <span>{lim}</span>
                  </li>
                ))}
              </ul>
            </EvidenceRow>
          </>
        )}
      </div>

      {/* ——— Wall of Fame ——— */}
      <AnimatePresence>
        {phase >= 1 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={transition('REVEAL')}
            className="max-w-4xl mx-auto mt-20 md:mt-28"
          >
            <div className="font-mono text-[10px] tracking-[0.45em] text-crimson mb-2 uppercase">
              THE WALL OF FAME
            </div>
            <p className="font-mono text-[11px] text-parchment-faint tracking-[0.15em] mb-8">
              Session materials available for consent. No cross-session specimens are loaded here.
            </p>

            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
              {wallSpecimens.slice(0, 11).map((s: { title: string; qualitative_reading: string; archetype?: string }, i: number) => (
                <WallTile
                  key={i}
                  index={i}
                  title={s.title}
                  text={s.qualitative_reading}
                  archetype={s.archetype}
                />
              ))}

              {/* The participant's material, waiting for a decision */}
              <WallTile
                index={26}
                title={card?.title || 'Your Selected Reading'}
                text={card?.statement || session.offering?.text || 'Your trace in this session'}
                archetype={card?.archetype || 'Participant'}
                self
                selfImage={session.offering?.imageDataUrl}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ——— Sovereign Consent Gate ——— */}
      <AnimatePresence>
        {phase >= 2 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 1.2 }}
            className="max-w-3xl mx-auto mt-24 md:mt-32 mb-16 text-center border-t border-parchment/10 pt-16"
          >
            <p className="font-mono text-sm md:text-lg tracking-[0.25em] text-parchment leading-relaxed text-balance">
              DO YOU CONSENT YOUR DATA
              <br />
              TO BE ADDED TO THE WALL OF FAME?
            </p>
            <p className="mt-5 font-mono text-[11px] tracking-[0.2em] text-parchment-faint leading-loose max-w-xl mx-auto">
              You now know what happened behind the conversation. Therefore this consent has meaning.
              If you keep it private, your session trace will be purged completely.
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
