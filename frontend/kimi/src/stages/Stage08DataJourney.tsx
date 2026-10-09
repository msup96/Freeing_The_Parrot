import { useEffect, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { transition } from '../lib/motion';
import type { Session } from '../lib/session';

type Row = Record<string, unknown>;
const NA = 'NOT AVAILABLE';
const obj = (v: unknown): Row => (v && typeof v === 'object' && !Array.isArray(v) ? (v as Row) : {});
const rows = (v: unknown): Row[] => (Array.isArray(v) ? (v as Row[]) : []);
const pad = (n: number | string) => String(n).padStart(2, '0');

function fmt(v: unknown, digits = 2): string {
  if (v === null || v === undefined || v === '') return NA;
  if (typeof v === 'number') return Number.isInteger(v) ? String(v) : v.toFixed(digits);
  if (typeof v === 'boolean') return v ? 'YES' : 'NO';
  return String(v).replaceAll('_', ' ');
}

/** Short `key: value` rendering of one evidence value. Never a JSON dump. */
function flat(v: unknown): string {
  if (v === null || v === undefined) return NA;
  if (Array.isArray(v)) return v.map((x) => fmt(x)).join(' → ');
  if (typeof v === 'object') {
    return Object.entries(v as Row)
      .map(([k, val]) => `${k.replaceAll('_', ' ')}: ${Array.isArray(val) ? val.map((x) => fmt(x)).join(' → ') : fmt(val)}`)
      .join(' · ');
  }
  return fmt(v);
}

/** `first → final (mean m unit)` for a trajectory the backend marked ok. */
function stat(t: Row): string {
  if (t.status !== 'ok') return NA;
  return `${fmt(t.first)} → ${fmt(t.final)}  (mean ${fmt(t.mean)}${t.unit ? ` ${String(t.unit)}` : ''})`;
}

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

function Tier({ number, title, level, description, children }: { number: string; title: string; level: string; description: string; children: React.ReactNode }) {
  return (
    <section className="relative mb-10 border border-parchment/10 bg-[#11110f]/70 px-4 py-5 md:px-6 md:py-7" aria-labelledby={`tier-${number}`}>
      <div className="mb-5 border-b border-crimson/20 pb-4">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 font-mono">
          <span className="text-[10px] tracking-[0.3em] text-crimson">{number}</span>
          <h3 id={`tier-${number}`} className="text-sm tracking-[0.22em] text-parchment">{title}</h3>
          <span className="text-[9px] uppercase tracking-[0.2em] text-gold/80">{level}</span>
        </div>
        <p className="mt-2 max-w-2xl font-serif text-xs italic leading-relaxed text-parchment-dim">{description}</p>
      </div>
      {children}
    </section>
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

function Kv({ rows: items }: { rows: Array<[string, React.ReactNode]> }) {
  return (
    <div className="grid grid-cols-[minmax(110px,0.45fr)_1fr] gap-x-4 gap-y-1.5 text-[11px]">
      {items.map(([label, value]) => (
        <div key={label} className="contents">
          <div className="pt-0.5 text-[9px] uppercase tracking-[0.2em] text-crimson/80">{label}</div>
          <div className="break-words text-parchment-dim">{value}</div>
        </div>
      ))}
    </div>
  );
}

function Tag({ children }: { children: React.ReactNode }) {
  return <div className="mb-2 mt-5 text-[9px] uppercase tracking-[0.25em] text-crimson/80 first:mt-0">{children}</div>;
}

/** One evidence or inference record: an id, then labelled fields. */
function RecordBlock({ id, fields }: { id: string; fields: Array<[string, React.ReactNode]> }) {
  return (
    <div className="mb-3 border border-parchment/10 bg-black/20 p-3">
      <div className="mb-2 text-[10px] tracking-[0.3em] text-gold">{id}</div>
      <Kv rows={fields} />
    </div>
  );
}

function Table({ head, body }: { head: string[]; body: React.ReactNode[][] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[480px] text-left text-[11px]">
        <thead>
          <tr className="text-[9px] uppercase tracking-[0.18em] text-crimson/80">
            {head.map((h) => (
              <th key={h} className="pb-2 pr-4 font-normal">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="text-parchment-dim">
          {body.map((cells, i) => (
            <tr key={i} className="border-t border-parchment/5">
              {cells.map((cell, j) => (
                <td key={j} className="py-1.5 pr-4 align-top">{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
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
          {self ? 'YOUR TRACE' : 'CONSTRUCTED'}
        </div>
        <div className={`w-1.5 h-1.5 rounded-full ${self ? 'bg-gold animate-pulse' : 'bg-crimson/60'}`} />
      </div>
    </motion.div>
  );
}

const PROFILE_FIELDS: Array<[string, string, string]> = [
  ['INPUT', 'input_modality', ''],
  ['TURNS', 'turn_count', ''],
  ['TEXT VOLUME', 'character_count', ' characters'],
  ['QUESTION DENSITY', 'question_density', ''],
  ['SELF-REFERENCE (MEAN)', 'self_reference_mean', ''],
  ['REPETITION', 'repetition_count', ''],
  ['MESSAGE VARIANCE', 'message_length_variation', ''],
  ['RESPONSE LATENCY (MEAN)', 'response_latency_mean_seconds', ' s'],
  ['INTER-TURN GAP (MEAN)', 'inter_turn_gap_mean_seconds', ' s'],
  ['INTERACTION STATE', 'interaction_state', ''],
  ['NAVARASA', 'navarasa_status', ''],
  ['EVIDENCE', 'evidence_count', ''],
  ['INFERENCES', 'eligible_inference_count', ''],
  ['READINGS', 'readings_constructed', ''],
  ['SELECTED', 'card_selection_count', ''],
  ['RESONANCE', 'resonance', ''],
];

/**
 * Stage 08 — THE MACHINE REVEAL.
 * Renders the backend's serialized reveal in the canonical order. It computes nothing:
 * every value is read from `session.reveal`; anything missing is shown as NOT AVAILABLE.
 */
export default function Stage08DataJourney({
  session,
  onConsent,
}: {
  session: Session;
  onConsent: (c: 'private' | 'wall') => void;
}) {
  const [phase, setPhase] = useState(0); // 0 sections, 1 wall, 2 consent
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

  const wallSpecimens = reveal?.wall_specimens ?? [];
  const sessionIdShort = session.sessionId ? session.sessionId.slice(-8) : '—';

  const art = obj(reveal?.analytical_artifacts);
  const linguistic = obj(art.linguistic);
  const temporal = obj(art.temporal);
  const navarasa = obj(art.navarasa);
  const packet = obj(art.deep_reader_packet);
  const signals = useMemo(() => reveal?.observed_signals ?? [], [reveal?.observed_signals]);
  const inferences = useMemo(() => reveal?.inference_records ?? [], [reveal?.inference_records]);
  const cardRecords = useMemo(() => reveal?.card_provenance ?? [], [reveal?.card_provenance]);
  const pattern = reveal?.selection_pattern;
  const profile = reveal?.interaction_profile;

  // Labels only: E-01.. / I-01.. number the records the backend returned, in order.
  const evidenceLabel = useMemo(() => new Map(signals.map((s, i) => [s.evidence_id, `E-${pad(i + 1)}`])), [signals]);
  const inferenceLabel = useMemo(() => new Map(inferences.map((r, i) => [r.inference_id, `I-${pad(i + 1)}`])), [inferences]);

  const lingRows = rows(linguistic.turn_sequence);
  const tempRows = rows(temporal.turn_sequence);
  const tempByTurn = new Map(tempRows.map((r) => [Number(r.turn_index), r]));
  const turnByEvent = new Map<string, number>();
  for (const r of [...lingRows, ...tempRows]) turnByEvent.set(String(r.event_id), Number(r.turn_index));
  const turnsOf = (ids: string[] = []): string => {
    const turns = [...new Set(ids.map((id) => turnByEvent.get(id)).filter((t): t is number => t !== undefined))].sort((a, b) => a - b);
    if (turns.length === 0) return NA;
    return turns.length > 4 ? `T${pad(turns[0])} – T${pad(turns[turns.length - 1])}` : turns.map((t) => `T${pad(t)}`).join(' · ');
  };

  const participantTurns = session.turns.filter((t) => t.role === 'participant').length;
  const rawText = obj(reveal?.machine_transformation?.raw_text);
  const offeringText = session.offering?.text;

  const selectedRecords = (pattern?.selected_card_ids ?? [])
    .map((id) => cardRecords.find((c) => c.card_id === id))
    .filter((c): c is NonNullable<typeof c> => Boolean(c));
  const interpreted = signals.filter((s) => s.provenance_level === 'INTERPRETED');
  const nav = (key: string) => obj(navarasa[key]);
  const detected = (navarasa.detected_sequence as string[] | undefined) ?? [];
  const defaultedTurns = Number(navarasa.defaulted_shanta_turns ?? 0);
  const conversationInference = obj(navarasa.conversation_inference);
  const inferenceAlternatives = rows(conversationInference.alternative_readings);
  const readings = cardRecords.length;

  return (
    <div className="relative min-h-[100dvh] bg-[#0a0a09] px-6 md:px-0 py-24 text-parchment selection:bg-crimson selection:text-parchment">
      <div className="max-w-3xl mx-auto">
        {/* Title header */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={transition('REVEAL')} className="mb-12">
          <div className="font-mono text-[10px] tracking-[0.45em] text-crimson mb-3">
            SESSION № {sessionIdShort.toUpperCase()} — DECONSTRUCTION
          </div>
          <h2 className="font-mono text-2xl md:text-4xl tracking-[0.16em] text-parchment">THE MACHINE REVEAL</h2>
          <p className="mt-3 font-serif italic text-xs md:text-sm text-parchment-dim">
            The Parrot was the performer. The Silent Reader was the observer.
          </p>
        </motion.div>

        <div className="mb-10 border border-crimson/20 bg-black/30 p-4 font-mono text-[10px] tracking-[0.16em] text-parchment-faint" aria-label="Provenance path">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
            {['RAW', 'OBSERVED', 'MEASURED', 'EVIDENCE', 'INFERRED', 'CONSTRUCTED', 'SELECTED', 'CANNOT KNOW'].map((level, index, levels) => (
              <span key={level} className="flex items-center gap-3">
                <span className={index === levels.length - 1 ? 'text-gold' : 'text-crimson/80'}>{level}</span>
                {index < levels.length - 1 && <span className="text-crimson/50">→</span>}
              </span>
            ))}
          </div>
          <div className="mt-3 text-[9px] text-parchment-faint/70">ONE SESSION · SERVER REVEAL DATA ONLY</div>
        </div>

        <Tier number="01" title="RAW" level="WHAT WAS RECORDED" description="The material that entered this session, before analysis or interpretation.">
        {/* ——— 01 WHAT YOU GAVE ——— */}
        <EvidenceRow label="01 — WHAT YOU GAVE" sub="Your own input, as it entered the system.">
          <Kv
            rows={[
              ['INPUT MODALITY', (session.offering?.channel ?? reveal?.what_you_gave_channel ?? NA).toString().toUpperCase()],
              [
                'TEXT RECEIVED',
                offeringText ? (
                  <span className="font-serif italic">“{offeringText}”</span>
                ) : session.offering?.imageDataUrl ? (
                  'IMAGE OFFERING (NO TEXT)'
                ) : reveal?.what_you_gave ? (
                  <span className="font-serif italic">“{reveal.what_you_gave}”</span>
                ) : (
                  NA
                ),
              ],
              ['CONVERSATIONAL TURNS', fmt(rawText.turn_count ?? (participantTurns || null))],
              ['CHARACTERS RECEIVED', fmt(rawText.character_count)],
            ]}
          />
          {session.offering?.imageDataUrl && (
            <img src={session.offering.imageDataUrl} alt="offering specimen" className="mt-3 w-32 md:w-44 border border-parchment/20" />
          )}
        </EvidenceRow>

        <Connector />

        </Tier>
        <Tier number="02" title="OBSERVED" level="WHAT WAS RECORDED" description="Turn-by-turn signals recorded from this interaction, without a claim about who you are.">
        {/* ——— 02 WHAT THE SYSTEM OBSERVED ——— */}
        <EvidenceRow label="02 — WHAT THE SYSTEM OBSERVED" sub="Turn by turn. Measured from your text and timing; not interpreted.">
          {lingRows.length === 0 ? (
            'NO TURNS WERE RECORDED FOR THIS SESSION.'
          ) : (
            <Table
              head={['TURN', 'LENGTH', 'TOKENS', 'QUESTION', 'SELF-REF', 'LATENCY s', 'GAP s', 'REPEAT']}
              body={lingRows.map((r) => {
                const t = obj(tempByTurn.get(Number(r.turn_index)));
                return [
                  `T${pad(Number(r.turn_index))}`,
                  fmt(r.message_length),
                  fmt(r.token_count),
                  fmt(r.utterance_is_question),
                  fmt(r.self_reference_count),
                  fmt(t.response_latency),
                  fmt(t.inter_turn_gap),
                  fmt(t.repeated_message),
                ];
              })}
            />
          )}
        </EvidenceRow>

        <Connector />

        </Tier>
        <Tier number="03" title="MEASURED" level="WHAT WAS CALCULATED" description="Numerical summaries describe this interaction; they are not a profile of you.">
        {/* ——— 03 WHAT THE SYSTEM MEASURED ——— */}
        <EvidenceRow label="03 — WHAT THE SYSTEM MEASURED" sub="Session-wide signals. A measurement describes the interaction, not you.">
          <Tag>LINGUISTIC</Tag>
          <Kv
            rows={[
              [
                'QUESTION RATE',
                obj(linguistic.question_rate).status === 'ok'
                  ? `${fmt(obj(linguistic.question_rate).value)}  (${fmt(obj(linguistic.question_rate).question_turns)} of ${fmt(obj(linguistic.question_rate).turn_count)} turns)`
                  : NA,
              ],
              ['SELF-REFERENCE', stat(obj(linguistic.self_reference_trajectory))],
              ['TYPE-TOKEN RATIO', stat(obj(linguistic.type_token_ratio_trajectory))],
              ['TOKEN COUNT', stat(obj(linguistic.token_count_trajectory))],
              ['MESSAGE LENGTH', stat(obj(linguistic.message_length_trajectory))],
              ['REPETITION', fmt(obj(temporal.repetition).repetition_count)],
              ['MESSAGE VARIANCE', fmt(obj(obj(temporal.volatility).message_length).normalized_variation)],
            ]}
          />
          <Tag>TEMPORAL</Tag>
          <Kv
            rows={[
              ['RESPONSE LATENCY', stat(obj(temporal.response_latency_trajectory))],
              ['INTER-TURN GAP', stat(obj(temporal.inter_turn_gap_trajectory))],
              [
                'VOLATILITY',
                obj(obj(temporal.volatility).message_length).status === 'ok'
                  ? `${fmt(obj(obj(temporal.volatility).message_length).transition_count)} length changes · range ${fmt(obj(obj(temporal.volatility).message_length).range)}`
                  : NA,
              ],
              [
                'BEGINNING → END',
                obj(temporal.beginning_vs_ending).status === 'ok'
                  ? `length ${fmt(obj(obj(temporal.beginning_vs_ending).beginning).message_length)} → ${fmt(obj(obj(temporal.beginning_vs_ending).ending).message_length)}`
                  : NA,
              ],
            ]}
          />
        </EvidenceRow>

        <Connector />

        </Tier>
        <Tier number="05" title="INFERRED" level="WHAT THE SYSTEM INTERPRETED" description="Bounded interpretations are interaction-scoped claims, not facts or diagnoses.">
        {/* ——— 04 NAVARASA TRAJECTORY ——— */}
        <EvidenceRow label="04 — NAVARASA TRAJECTORY" sub="Detected emotional vocabulary per turn. A default label is not a detection.">
          {rows(navarasa.turn_sequence).length > 0 && (
            <Table
              head={['TURN', 'SIGNAL', 'WORDS']}
              body={rows(navarasa.turn_sequence).map((r) => [
                `T${pad(Number(r.turn_index))}`,
                r.defaulted_primary === true ? 'NO RASA DETECTED' : fmt(r.primary_rasa),
                Array.isArray(r.emotional_words) && r.emotional_words.length ? (r.emotional_words as string[]).join(', ') : '—',
              ])}
            />
          )}
          <div className="mt-4">
            <Kv
              rows={[
                ['TRAJECTORY', detected.length ? detected.join(' → ') : 'INSUFFICIENT EVIDENCE FOR A STABLE RASA TRAJECTORY'],
                ['TRANSITIONS', fmt(nav('transition_count').value)],
  ['DOMINANT SIGNAL', fmt(nav('dominant_rasa').label)],
  [
  'CONVERSATION INFERENCE',
  conversationInference.status === 'supported'
    ? `${fmt(conversationInference.label)} (${fmt(conversationInference.confidence)} confidence; ${fmt(conversationInference.evidence_turn_count)} detected turns)`
    : 'INSUFFICIENT EVIDENCE — NO STABLE CONVERSATION-LEVEL INFERENCE',
  ],
  [
  'ALTERNATIVE READINGS',
  inferenceAlternatives.length
    ? inferenceAlternatives.map((item) => `${fmt(item.label)} (${fmt(item.share)})`).join(' · ')
    : 'NONE RECORDED',
  ],
  [
  'DEFAULTED TURNS',

                  defaultedTurns > 0 ? `${defaultedTurns} turn(s) had no emotional vocabulary; their default label is not shown as evidence.` : '0',
                ],
              ]}
            />
          </div>
        </EvidenceRow>

        <Connector />

        {/* ——— 05 WHAT THE SYSTEM INTERPRETED ——— */}
        <EvidenceRow label="05 — WHAT THE SYSTEM INTERPRETED" sub="Labels produced by rules applied to the measurements above. Interaction-scoped.">
          {interpreted.length === 0
            ? 'NOTHING WAS INTERPRETED. THE EVIDENCE DID NOT SUPPORT IT.'
            : interpreted.map((s) => (
                <RecordBlock
                  key={s.evidence_id}
                  id={evidenceLabel.get(s.evidence_id) ?? s.evidence_id}
                  fields={[
                    ['SIGNAL', s.signal_type.replaceAll('_', ' ').toUpperCase()],
                    ['VALUE', flat(s.value)],
                    ['PROVENANCE', s.provenance_level],
                    ['LIMITATION', s.limitation_notes?.length ? s.limitation_notes.join(' ') : '—'],
                  ]}
                />
              ))}
        </EvidenceRow>

        <Connector />

        </Tier>
        <Tier number="04" title="EVIDENCE" level="WHAT SUPPORTS A CLAIM" description="Observed records that the system used as support, with their event references and limitations.">
        {/* ——— 06 EVIDENCE ——— */}
        <EvidenceRow label="06 — EVIDENCE" sub="OBSERVATION → EVIDENCE → INFERENCE. This is how the machine got there.">
          {signals.length === 0
            ? 'NO EVIDENCE RECORDS WERE RETURNED FOR THIS SESSION.'
            : signals.map((s) => (
                <RecordBlock
                  key={s.evidence_id}
                  id={evidenceLabel.get(s.evidence_id) ?? s.evidence_id}
                  fields={[
                    ['SIGNAL', s.signal_type.replaceAll('_', ' ').toUpperCase()],
                    ['VALUE', flat(s.value)],
                    ['OBSERVATION', s.observation],
                    ['SOURCE', turnsOf(s.source_event_ids)],
                    ['PROVENANCE', s.provenance_level],
                    ['LIMITATION', s.limitation_notes?.length ? s.limitation_notes.join(' ') : 'NONE RECORDED'],
                  ]}
                />
              ))}
        </EvidenceRow>

        <Connector />

        {/* ——— 07 INFERENCE ——— */}
        <EvidenceRow label="07 — INFERENCE" sub="Bounded claims. Support is within this interaction, not the probability that a claim is true of you.">
          {inferences.length === 0
            ? 'NO INFERENCE RECORDS WERE RETURNED FOR THIS SESSION.'
            : inferences.map((r) => (
                <RecordBlock
                  key={r.inference_id}
                  id={inferenceLabel.get(r.inference_id) ?? r.inference_id}
                  fields={[
                    ['CLAIM', r.claim],
                    ['SUPPORTED BY', r.evidence_refs.map((id) => evidenceLabel.get(id) ?? id).join(' · ') || NA],
                    ['ALTERNATIVES', r.alternative_interpretations?.length ? r.alternative_interpretations.join(' / ') : 'NONE RECORDED'],
                    ['CONTRADICTIONS', r.contradictions?.length ? r.contradictions.map((c) => c.description ?? '—').join(' / ') : 'NONE RECORDED'],
                    ['ELIGIBILITY', fmt(r.eligibility).toUpperCase()],
                    ['SUPPORT', r.confidence === null || r.confidence === undefined ? NA : `${fmt(r.confidence)} (within this interaction)`],
                    ['LIMITATIONS', r.limitation_notes?.length ? r.limitation_notes.join(' ') : 'NONE RECORDED'],
                  ]}
                />
              ))}
        </EvidenceRow>

        <Connector />

        </Tier>
        <Tier number="06" title="CONSTRUCTED" level="WHAT THE SYSTEM ASSEMBLED" description="Readings and machine artifacts constructed from the interaction, not discovered truths.">
        {/* ——— 08 WHAT THE SYSTEM CONSTRUCTED ——— */}
        <EvidenceRow label="08 — WHAT THE SYSTEM CONSTRUCTED" sub="From analysis to qualitative readings.">
          {readings === 0 ? (
            'NO READINGS WERE SERIALIZED FOR THIS SESSION.'
          ) : (
            <>
              <p className="mb-3 text-parchment">
                THE SYSTEM DID NOT DISCOVER {readings} TRUTHS ABOUT YOU. IT CONSTRUCTED {readings} POSSIBLE READINGS FROM THE INTERACTION.
              </p>
              <Kv
                rows={[
                  ['READINGS CONSTRUCTED', String(readings)],
                  ['EVIDENCE PASSED TO THE READER', fmt(rows(packet.evidence_items).length)],
                  ['ELIGIBLE INFERENCES', fmt(rows(packet.eligible_inferences).length)],
                  ['EVERY READING IS', 'INFERRED · TRACED TO AT LEAST ONE EVIDENCE ITEM AND ONE INFERENCE'],
                ]}
              />
            </>
          )}
        </EvidenceRow>

        <Connector />

        {/* ——— 09 THE 27 READINGS ——— */}
        <EvidenceRow label={`09 — THE ${readings || 27} READINGS`} sub="Machine provenance of each card you were shown. Territory is the card's semantic category.">
          {readings === 0 ? (
            NA
          ) : (
            <Table
              head={['№', 'TERRITORY', 'TITLE', 'MOTIF', 'ARCHETYPE', 'EVIDENCE', 'INFERENCE', 'SELECTION']}
              body={cardRecords.map((c) => {
                const selectedAt = (pattern?.selected_card_ids ?? []).indexOf(c.card_id);
                const gold = selectedAt >= 0 ? 'text-gold' : '';
                return [
                  <span className={gold}>{pad(c.card_index)}</span>,
                  <span className={gold}>{fmt(c.semantic_anchor)}</span>,
                  <span className={gold}>{c.title}</span>,
                  fmt(c.semantic_motif),
                  fmt(c.archetype),
                  (c.provenance?.evidence_ids ?? []).map((id) => evidenceLabel.get(id) ?? id).join(' · ') || '—',
                  (c.provenance?.inference_ids ?? []).map((id) => inferenceLabel.get(id) ?? id).join(' · ') || '—',
                  <span className={gold}>{selectedAt >= 0 ? `SELECTED · ${pad(selectedAt + 1)}` : 'NOT SELECTED'}</span>,
                ];
              })}
            />
          )}
        </EvidenceRow>

        <Connector />

        </Tier>
        <Tier number="07" title="SELECTED" level="WHAT YOU CHOSE" description="Your selection and reported resonance are recorded choices, not validation or proof.">
        {/* ——— 10 WHAT YOU CHOSE ——— */}
        <EvidenceRow label="10 — WHAT YOU CHOSE" sub={reveal?.what_you_chose?.disclaimer || 'Selected by you from the cards presented.'}>
          <Kv
            rows={[
              ['CARDS PRESENTED', fmt(pattern?.total_cards_presented ?? (readings || null))],
              ['CARDS SELECTED', fmt(pattern?.selected_count)],
              ['YOUR SELECTED TERRITORIES', (pattern?.semantic_anchors ?? []).join(' · ') || NA],
            ]}
          />
          {selectedRecords.length > 0 && (
            <div className="mt-4">
              <Table
                head={['№', 'TERRITORY', 'TITLE']}
                body={selectedRecords.map((c) => [pad(c.card_index), fmt(c.semantic_anchor), c.title])}
              />
            </div>
          )}
        </EvidenceRow>

        <Connector />

        {/* ——— 11 YOUR SELECTION PATTERN ——— */}
        <EvidenceRow label="11 — YOUR SELECTION PATTERN" sub="THE MACHINE RECORDED. A selection is an observation, not proof of who you are.">
          <Kv
            rows={[
              ['SELECTION COUNT', fmt(pattern?.selected_count)],
              ['SELECTION ORDER', (pattern?.selected_card_indices ?? []).map(pad).join(' → ') || NA],
              ['SEMANTIC TERRITORIES', (pattern?.semantic_anchors ?? []).join(' · ') || NA],
              ['READING GROUPS', (pattern?.reading_groups ?? []).length ? (pattern?.reading_groups ?? []).join(' · ') : NA],
              ['INSPECTION DATA', pattern?.cards_inspected === null || pattern?.cards_inspected === undefined ? 'NOT AVAILABLE IN THIS SESSION' : fmt(pattern.cards_inspected)],
              ['RESONANCE', 'PARTICIPANT-REPORTED · VALIDATED PROVENANCE · NOT PROOF'],
            ]}
          />
        </EvidenceRow>

        <Connector />

        {/* ——— 12 INTERACTION PROFILE ——— */}
        <EvidenceRow label="12 — INTERACTION PROFILE" sub="NOT A PROFILE OF YOU. A profile of this interaction.">
          {profile ? (
            <>
            {reveal?.session_archetype && (
              <div className="mb-4 border border-gold/30 p-3">
                <div className="text-[9px] uppercase tracking-[0.18em] text-crimson/80">SESSION ARCHETYPE</div>
                <div className="mt-1 font-serif text-lg text-gold">{reveal.session_archetype.name}</div>
                <div className="mt-1 text-[10px] text-parchment-faint">Based on {reveal.session_archetype.basis}. This describes this interaction, not you.</div>
              </div>
            )}
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              {PROFILE_FIELDS.map(([label, key, suffix]) => {
                const value = profile[key];
                return (
                  <div key={key} className="border border-parchment/10 p-2">
                    <div className="text-[9px] uppercase tracking-[0.12em] text-crimson/80">{label}</div>
                    <div className="mt-1 break-words text-gold">
                      {value === null || value === undefined ? NA : `${fmt(value)}${suffix}`}
                    </div>
                  </div>
                );
              })}
            </div>
            </>
          ) : (
            NA
          )}
        </EvidenceRow>

        <Connector />

        </Tier>
        <Tier number="08" title="CANNOT KNOW" level="EXPLICIT LIMITS" description="The boundaries of what this single interaction can support or establish.">
        {/* ——— 13 WHAT THE SYSTEM CANNOT KNOW ——— */}
        <EvidenceRow label="13 — WHAT THE SYSTEM CANNOT KNOW" sub="THIS IS NOT WHO YOU ARE. THIS IS WHAT THIS INTERACTION MADE LEGIBLE.">
          {reveal?.what_we_cannot_know && reveal.what_we_cannot_know.length > 0 ? (
            <ul className="space-y-2 text-xs text-parchment-dim">
              {reveal.what_we_cannot_know.map((lim: string, i: number) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="text-crimson">✕</span>
                  <span>{lim}</span>
                </li>
              ))}
            </ul>
          ) : (
            'THE SYSTEM DID NOT REPORT ITS LIMITS FOR THIS SESSION.'
          )}
        </EvidenceRow>
        </Tier>
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
            <div className="font-mono text-[10px] tracking-[0.45em] text-crimson mb-2 uppercase">THE MEMORY CHEST</div>
            <p className="font-mono text-[11px] text-parchment-faint tracking-[0.15em] mb-8">
              Session materials available for consent. No cross-session specimens are loaded here.
            </p>

            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
              {wallSpecimens.slice(0, 11).map((s: { title: string; qualitative_reading: string; archetype?: string }, i: number) => (
                <WallTile key={i} index={i} title={s.title} text={s.qualitative_reading} archetype={s.archetype} />
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

      {/* ——— 14 CONSENT / PURGE ——— */}
      <AnimatePresence>
        {phase >= 2 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 1.2 }}
            className="max-w-3xl mx-auto mt-24 md:mt-32 mb-16 text-center border-t border-parchment/10 pt-16"
          >
            <p className="font-mono text-xs md:text-sm tracking-[0.3em] text-crimson leading-loose text-balance">
              THE CARD WAS THE EXPERIENCE.
              <br />
              THE SELECTION WAS DATA.
              <br />
              THE REVEAL IS THE MIRROR.
            </p>
            <p className="mt-16 font-mono text-sm md:text-lg tracking-[0.25em] text-parchment leading-relaxed text-balance">
              DO YOU CONSENT YOUR DATA
              <br />
              TO BE ADDED TO THE MEMORY CHEST?
            </p>
            <p className="mt-5 font-mono text-[11px] tracking-[0.2em] text-parchment-faint leading-loose max-w-xl mx-auto">
              You now know what happened behind the conversation. Therefore this consent has meaning.
              If you keep it private, your session trace will be purged completely.
            </p>
            <div className="mt-10 flex flex-col md:flex-row items-center justify-center gap-4 md:gap-8">
              <button className="brass-button px-8 py-4 min-h-[44px] min-w-[220px]" onClick={() => onConsent('private')}>
                KEEP PRIVATE
              </button>
              <button className="brass-button px-8 py-4 min-h-[44px] min-w-[220px]" onClick={() => onConsent('wall')}>
                ADD TO MEMORY CHEST
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
