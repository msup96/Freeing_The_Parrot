import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Apparatus } from './Stage01Apparatus';
import { transition } from '../lib/motion';
import type { ChatTurn } from '../lib/session';

type ParrotState = 'IDLE' | 'LISTENING' | 'THINKING' | 'RESPONDING' | 'UNCERTAIN' | 'UNSTABLE' | 'GLITCHING';

const STATE_GLOW: Record<ParrotState, string> = {
  IDLE: 'radial-gradient(circle, rgba(232,163,61,0.8) 0%, rgba(232,163,61,0.2) 40%, transparent 70%)',
  LISTENING: 'radial-gradient(circle, rgba(232,163,61,1) 0%, rgba(232,163,61,0.35) 40%, transparent 70%)',
  THINKING: 'radial-gradient(circle, rgba(201,162,39,0.7) 0%, rgba(201,162,39,0.15) 40%, transparent 70%)',
  RESPONDING: 'radial-gradient(circle, rgba(244,236,216,0.9) 0%, rgba(232,163,61,0.3) 45%, transparent 70%)',
  UNCERTAIN: 'radial-gradient(circle, rgba(143,134,114,0.7) 0%, transparent 60%)',
  UNSTABLE: 'radial-gradient(circle, rgba(166,58,43,0.75) 0%, rgba(232,163,61,0.25) 45%, transparent 70%)',
  GLITCHING: 'radial-gradient(circle, rgba(166,58,43,0.95) 0%, rgba(166,58,43,0.3) 40%, transparent 70%)',
};

function stateForBehaviour(b: string): ParrotState {
  if (b === 'roast' || b === 'banana') return 'UNSTABLE';
  if (b === 'glitch' || b === 'memory-loss' || b === 'mixed') return 'GLITCHING';
  if (b === 'absurd' || b === 'help') return 'UNCERTAIN';
  return 'RESPONDING';
}

/** A parrot utterance — text emerges from the machine; behaviour bends the typography */
function ParrotLine({ turn }: { turn: ChatTurn }) {
  const b = turn.behaviour;
  const style: React.CSSProperties = {};
  if (b === 'absurd') style.letterSpacing = '0.06em';
  if (b === 'tender') style.fontStyle = 'italic';
  return (
    <motion.div
      initial={{ opacity: 0, y: 12, filter: 'blur(2px)' }}
      animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
      transition={transition('RESPOND')}
      className="max-w-[92%] md:max-w-[85%]"
    >
      <motion.p
        className={`whitespace-pre-wrap font-serif text-base md:text-lg leading-relaxed ${
          b === 'roast' || b === 'banana'
            ? 'text-parchment'
            : b === 'glitch' || b === 'memory-loss' || b === 'mixed'
              ? 'font-mono text-sm text-crimson/90'
              : 'text-parchment'
        }`}
        style={style}
        animate={b === 'glitch' ? { x: [0, -2, 3, -1, 0] } : {}}
        transition={b === 'glitch' ? { duration: 0.3, repeat: 2 } : {}}
      >
        {turn.text}
      </motion.p>
    </motion.div>
  );
}

/** Stage 04 + 05 — The Parrot steps out, then becomes strange */
export default function Stage04Parrot({
  turns,
  onTurns,
  onChat,
  onError,
  onDeck,
}: {
  turns: ChatTurn[];
  onTurns: (t: ChatTurn[]) => void;
  onChat: (text: string) => Promise<{ text: string; behaviour: string; closed: boolean }>;
  onError?: (message: string) => void;
  onDeck: () => void;
}) {
  const [state, setState] = useState<ParrotState>('IDLE');
  const [input, setInput] = useState('');
  const [emerged, setEmerged] = useState(false);
  const [deckReady, setDeckReady] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const participantTurns = turns.filter((t) => t.role === 'participant').length;

  // Emergence is presentation only; backend readiness is established before this stage.
  useEffect(() => {
    const t1 = window.setTimeout(() => setState('UNCERTAIN'), 1400);
    const t2 = window.setTimeout(() => {
      setEmerged(true);
      setState('RESPONDING');
    }, 2200);
      const t3 = window.setTimeout(() => setState('IDLE'), 3200);
      return () => [t1, t2, t3].forEach(clearTimeout);
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [turns, state]);

  const send = async () => {
    const text = input.trim();
    if (!text || state === 'THINKING') return;
    const next: ChatTurn[] = [...turns, { role: 'participant', text }];
    onTurns(next);
    setInput('');
    setState('THINKING');

      try {
        const reply = await onChat(text);
        setState(stateForBehaviour(reply.behaviour));
        onTurns([...next, { role: 'parrot', text: reply.text, behaviour: reply.behaviour }]);
        window.setTimeout(() => setState('IDLE'), 2600);
        if (reply.closed) setDeckReady(true);
      } catch (cause) {
        setState('IDLE');
        onTurns(next);
        onError?.(cause instanceof Error ? cause.message : 'The machine did not answer.');
      }

      // The deck control is only a presentation affordance; the backend
      // authorizes the actual transition when it is pressed.
      if (participantTurns + 1 >= 5) setDeckReady(true);
  };

  return (
    <div className="relative min-h-[100dvh] flex flex-col md:flex-row items-stretch overflow-hidden">
      {/* the machine dominates the composition */}
      <div className="relative md:w-[46%] flex items-center justify-center pt-20 md:pt-0 px-6">
        <motion.div
          className="w-[min(52vw,240px)] md:w-[min(34vw,400px)]"
          initial={{ opacity: 0, x: -40, filter: 'brightness(0.2)' }}
          animate={{ opacity: 1, x: 0, filter: 'brightness(1)' }}
          transition={{ duration: 1.6, ease: [0.45, 0, 0.1, 1] }}
        >
          <div className="relative">
            <Apparatus intensity={1.2} awakened={emerged} />
            {/* behaviour-driven lens state */}
            <motion.div
              className="absolute z-30 rounded-full pointer-events-none"
              style={{ left: '30%', top: '4%', width: '22%', aspectRatio: '1', background: STATE_GLOW[state], mixBlendMode: 'screen' }}
              animate={state === 'GLITCHING' ? { opacity: [1, 0.2, 1, 0.4, 1] } : state === 'LISTENING' || state === 'THINKING' ? { opacity: [0.6, 1, 0.6] } : {}}
              transition={state === 'GLITCHING' ? { duration: 0.4, repeat: Infinity } : { duration: 1.1, repeat: Infinity }}
            />
          </div>
        </motion.div>

        {/* state readout — the only instrument visible */}
        <motion.div
          className="absolute bottom-6 md:bottom-10 left-1/2 -translate-x-1/2 font-mono text-[10px] tracking-[0.45em]"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1, color: state === 'GLITCHING' || state === 'UNSTABLE' ? '#A63A2B' : '#8F8672' }}
        >
          {emerged
            ? `${state}${turns.some((turn) => turn.role === 'parrot') ? ` · ${turns.filter((turn) => turn.role === 'parrot').at(-1)?.behaviour?.replace(/-/g, ' ').toUpperCase()}` : ''}`
            : 'CAGED'}
        </motion.div>
      </div>

      {/* conversation emerges from the machine */}
      <div className="flex-1 flex flex-col min-h-0 md:max-h-[100dvh] px-5 md:px-10 pt-6 md:pt-24 pb-4">
        <div ref={scrollRef} className="flex-1 overflow-y-auto min-h-[180px] space-y-5 md:space-y-7 pr-1 md:pr-4">
          {turns.map((t, i) =>
            t.role === 'parrot' ? (
              <ParrotLine key={i} turn={t} />
            ) : (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={transition('RESPOND')}
                className="flex justify-end"
              >
                <div className="paper-strip max-w-[85%] md:max-w-[70%] px-4 py-2.5 md:px-5 md:py-3">
                  <p className="font-serif italic text-sm md:text-base text-ink">{t.text}</p>
                </div>
              </motion.div>
            ),
          )}
          {state === 'THINKING' && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="font-mono text-[10px] tracking-[0.4em] text-parchment-faint">
              THE MACHINE HESITATES …
            </motion.div>
          )}
        </div>

        {/* input — or the deck invitation */}
        <div className="pt-4 pb-16 md:pb-8">
          <AnimatePresence mode="wait">
            {deckReady ? (
              <motion.div key="deck" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={transition('REVEAL')} className="flex justify-center">
                <button className="brass-button px-8 py-4 min-h-[44px]" onClick={onDeck}>
                  TAKE THE DECK
                </button>
              </motion.div>
            ) : (
              <motion.div key="input" exit={{ opacity: 0 }} className="flex gap-3 items-end">
                <div className="flex-1 border-b border-brass/50 focus-within:border-gold transition-colors duration-500">
                  <input
                    value={input}
                    onChange={(e) => {
                      setInput(e.target.value);
                      if (emerged && state === 'IDLE') setState('LISTENING');
                    }}
                    onKeyDown={(e) => e.key === 'Enter' && send()}
                    placeholder={emerged ? 'Say something true…' : '…'}
                    disabled={!emerged}
                    className="w-full bg-transparent font-serif italic text-base md:text-lg text-parchment placeholder:text-parchment-faint/60 focus:outline-none py-3 min-h-[44px]"
                    style={{ caretColor: '#C9A227' }}
                  />
                </div>
                <button
                  className="brass-button px-5 md:px-7 py-3 min-h-[44px] disabled:opacity-40"
                  onClick={send}
                  disabled={!input.trim() || !emerged || state === 'THINKING'}
                >
                  OFFER
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
