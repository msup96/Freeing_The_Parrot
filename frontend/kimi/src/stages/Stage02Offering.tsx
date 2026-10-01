import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { transition } from '../lib/motion';
import type { Offering, OfferingChannel } from '../lib/session';

const CHANNELS: { id: OfferingChannel; label: string; sub: string }[] = [
  { id: 'write', label: 'WRITE', sub: 'a strip of paper' },
  { id: 'speak', label: 'SPEAK', sub: 'the listening chamber' },
  { id: 'show', label: 'SHOW', sub: 'a specimen under glass' },
  { id: 'look', label: 'LOOK', sub: 'the lens looks back' },
];

function downscale(file: File, max = 640): Promise<string> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const scale = Math.min(1, max / Math.max(img.width, img.height));
      const c = document.createElement('canvas');
      c.width = Math.round(img.width * scale);
      c.height = Math.round(img.height * scale);
      c.getContext('2d')!.drawImage(img, 0, 0, c.width, c.height);
      resolve(c.toDataURL('image/jpeg', 0.82));
    };
    img.onerror = reject;
    img.src = URL.createObjectURL(file);
  });
}

/* ————— WRITE — a physical paper strip ————— */
function WriteChannel({ onSubmit }: { onSubmit: (o: Offering) => void }) {
  const [text, setText] = useState('');
  const [pulled, setPulled] = useState(false);
  const submit = () => {
    if (!text.trim() || pulled) return;
    setPulled(true);
    window.setTimeout(() => onSubmit({ channel: 'write', text: text.trim(), timestamp: Date.now() }), 1050);
  };
  return (
    <motion.div
      initial={{ y: 80, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={transition('RESPOND')}
      className="w-full max-w-md mx-auto"
    >
      <motion.div
        className="paper-strip px-6 py-6 md:px-8 md:py-7 relative"
        animate={pulled ? { y: -420, rotate: -2.5, scale: 0.92, opacity: 0 } : {}}
        transition={{ duration: 0.85, ease: [0.5, 0, 0.75, 0.4] }}
        style={{
          clipPath:
            'polygon(0 0, 100% 0, 100% calc(100% - 6px), 97% 100%, 94% calc(100% - 5px), 90% 100%, 86% calc(100% - 6px), 80% 100%, 74% calc(100% - 4px), 68% 100%, 61% calc(100% - 6px), 54% 100%, 48% calc(100% - 4px), 41% 100%, 34% calc(100% - 6px), 27% 100%, 21% calc(100% - 5px), 14% 100%, 8% calc(100% - 6px), 3% 100%, 0 calc(100% - 5px))',
        }}
      >
        <div className="font-mono text-[9px] tracking-[0.3em] text-ink/50 mb-3">SPECIMEN SLIP — WRITE FREELY</div>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={4}
          placeholder="Offer the machine a thought, a secret, a sentence…"
          className="w-full bg-transparent font-serif italic text-lg md:text-xl leading-relaxed text-ink placeholder:text-ink/35 focus:outline-none resize-none"
          style={{ caretColor: '#8a744a' }}
          autoFocus
        />
        <div className="gold-rule opacity-60 mt-2" />
      </motion.div>
      <div className="mt-6 flex justify-center">
        <button
          className="brass-button px-8 py-3 min-h-[44px] disabled:opacity-40 disabled:cursor-not-allowed"
          disabled={!text.trim()}
          onClick={submit}
        >
          FEED THE MACHINE
        </button>
      </div>
    </motion.div>
  );
}

/* ————— SPEAK — the listening chamber ————— */
function SpeakChannel({ onSubmit }: { onSubmit: (o: Offering) => void }) {
  const [listening, setListening] = useState(false);
  const [done, setDone] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const barsRef = useRef<number[]>(Array.from({ length: 24 }, () => 0.15));
  const [bars, setBars] = useState<number[]>(barsRef.current);
  const streamRef = useRef<MediaStream | null>(null);
  const rafRef = useRef<number>(0);

  useEffect(() => {
    if (!listening) return;
    const iv = window.setInterval(() => setSeconds((s) => s + 1), 1000);
    let analyser: AnalyserNode | null = null;
    let ctx: AudioContext | null = null;
    navigator.mediaDevices
      ?.getUserMedia({ audio: true })
      .then((stream) => {
        streamRef.current = stream;
        ctx = new AudioContext();
        analyser = ctx.createAnalyser();
        analyser.fftSize = 64;
        ctx.createMediaStreamSource(stream).connect(analyser);
      })
      .catch(() => {});
    const tick = () => {
      const data = new Uint8Array(32);
      if (analyser) {
        analyser.getByteFrequencyData(data);
        barsRef.current = Array.from({ length: 24 }, (_, i) => 0.1 + (data[i + 2] / 255) * 0.9);
      } else {
        // mechanical measuring instrument — simulated needle drift
        barsRef.current = barsRef.current.map((v) => {
          const n = v + (Math.random() - 0.48) * 0.18;
          return Math.max(0.08, Math.min(0.9, n));
        });
      }
      setBars([...barsRef.current]);
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => {
      clearInterval(iv);
      cancelAnimationFrame(rafRef.current);
      streamRef.current?.getTracks().forEach((t) => t.stop());
      ctx?.close().catch(() => {});
    };
  }, [listening]);

  const finish = () => {
    setListening(false);
    setDone(true);
    window.setTimeout(
      () => onSubmit({ channel: 'speak', text: `[signal received — ${seconds}s]`, timestamp: Date.now() }),
      1600,
    );
  };

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={transition('RESPOND')} className="w-full max-w-md mx-auto text-center">
      <motion.div
        className="relative mx-auto w-56 h-56 md:w-64 md:h-64 rounded-full border border-brass/50 flex items-center justify-center"
        animate={done ? { scale: 0.9, opacity: 0 } : {}}
        transition={transition('ERASE')}
        style={{ background: 'radial-gradient(circle, #10160f 30%, #0b100c 70%)', boxShadow: 'inset 0 0 60px rgba(0,0,0,0.8), 0 0 0 1px rgba(0,0,0,0.6)' }}
      >
        <div className="absolute inset-3 rounded-full border border-olive-3/60" />
        <div className="absolute inset-8 rounded-full border border-olive-3/40" />
        {listening ? (
          <div className="flex items-end gap-[3px] h-20">
            {bars.map((v, i) => (
              <div key={i} className="w-[3px] bg-amber/80" style={{ height: `${v * 100}%`, transition: 'height 90ms linear' }} />
            ))}
          </div>
        ) : (
          <div className="font-mono text-[10px] tracking-[0.35em] text-parchment-faint text-center leading-loose px-8">
            {done ? 'SIGNAL RECEIVED' : 'THE CHAMBER IS OPEN'}
          </div>
        )}
        {listening && (
          <div className="absolute -bottom-8 font-mono text-[10px] tracking-[0.3em] text-amber/80">
            REC {String(Math.floor(seconds / 60)).padStart(2, '0')}:{String(seconds % 60).padStart(2, '0')}
          </div>
        )}
      </motion.div>
      <div className="mt-14 flex justify-center">
        {!done && (
          <button className="brass-button px-8 py-3 min-h-[44px]" onClick={() => (listening ? finish() : setListening(true))}>
            {listening ? 'SEAL THE CHAMBER' : 'OPEN THE CHAMBER'}
          </button>
        )}
      </div>
    </motion.div>
  );
}

/* ————— SHOW — a specimen under glass ————— */
function ShowChannel({ onSubmit }: { onSubmit: (o: Offering) => void }) {
  const [img, setImg] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [pulled, setPulled] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const submit = () => {
    if (!img || pulled) return;
    setPulled(true);
    window.setTimeout(() => onSubmit({ channel: 'show', imageDataUrl: img, media: file || undefined, filename: file?.name, timestamp: Date.now() }), 1050);
  };

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={transition('RESPOND')} className="w-full max-w-md mx-auto text-center">
      <input
        ref={fileRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={async (e) => {
          const f = e.target.files?.[0];
          if (f) {
            setFile(f);
            setImg(await downscale(f));
          }
        }}
      />
      <motion.div
        className="relative mx-auto w-64 h-64 md:w-72 md:h-72 border border-brass/50 overflow-hidden"
        animate={pulled ? { y: -420, opacity: 0, scale: 0.9 } : {}}
        transition={{ duration: 0.85, ease: [0.5, 0, 0.75, 0.4] }}
        style={{ background: 'rgba(16,22,15,0.8)', boxShadow: 'inset 0 0 50px rgba(0,0,0,0.7)' }}
      >
        {img ? (
          <>
            <img src={img} alt="specimen" className="w-full h-full object-cover" />
            {/* glass plate */}
            <div className="absolute inset-0" style={{ background: 'linear-gradient(115deg, rgba(244,236,216,0.14) 0%, transparent 35%, transparent 65%, rgba(244,236,216,0.07) 100%)' }} />
            <div className="absolute top-2 left-2 font-mono text-[9px] tracking-[0.25em] text-parchment/80 bg-ink/60 px-2 py-1">SPECIMEN — UNDER GLASS</div>
          </>
        ) : (
          <button
            onClick={() => fileRef.current?.click()}
            className="w-full h-full flex flex-col items-center justify-center gap-3 min-h-[44px]"
          >
            <div className="w-16 h-16 border border-dashed border-brass/60" />
            <span className="font-mono text-[10px] tracking-[0.35em] text-parchment-faint">PLACE AN IMAGE ON THE PLATE</span>
          </button>
        )}
        <div className="absolute top-2 right-2 w-2 h-2 border-t border-r border-gold/70" />
        <div className="absolute bottom-2 left-2 w-2 h-2 border-b border-l border-gold/70" />
        <div className="absolute bottom-2 right-2 w-2 h-2 border-b border-r border-gold/70" />
      </motion.div>
      <div className="mt-8 flex justify-center gap-4">
        {img && !pulled && (
          <>
            <button className="brass-button px-6 py-3 min-h-[44px] opacity-70" onClick={() => fileRef.current?.click()}>REPLACE</button>
            <button className="brass-button px-8 py-3 min-h-[44px]" onClick={submit}>SLIDE IT IN</button>
          </>
        )}
      </div>
    </motion.div>
  );
}

/* ————— LOOK — the lens looks back ————— */
function LookChannel({ onSubmit }: { onSubmit: (o: Offering) => void }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [state, setState] = useState<'closed' | 'open' | 'denied' | 'captured'>('closed');
  const [count, setCount] = useState<number | null>(null);
  const [img, setImg] = useState<string | null>(null);

  useEffect(() => () => streamRef.current?.getTracks().forEach((t) => t.stop()), []);

  const openLens = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } });
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
      setState('open');
      // the apparatus looks back — then captures on its own
      window.setTimeout(() => setCount(3), 900);
      window.setTimeout(() => setCount(2), 1900);
      window.setTimeout(() => setCount(1), 2900);
      window.setTimeout(capture, 3900);
    } catch {
      setState('denied');
    }
  };

  const capture = () => {
    const v = videoRef.current;
    if (!v) return;
    const c = document.createElement('canvas');
    c.width = v.videoWidth || 640;
    c.height = v.videoHeight || 480;
    const ctx = c.getContext('2d')!;
    ctx.translate(c.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(v, 0, 0);
    const url = c.toDataURL('image/jpeg', 0.82);
    setImg(url);
    setState('captured');
    streamRef.current?.getTracks().forEach((t) => t.stop());
    c.toBlob((blob) => {
      if (blob) window.setTimeout(() => onSubmit({ channel: 'look', imageDataUrl: url, media: blob, filename: 'camera.jpg', timestamp: Date.now() }), 1800);
    }, 'image/jpeg', 0.82);
  };

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={transition('RESPOND')} className="w-full max-w-md mx-auto text-center">
      <div className="relative mx-auto w-64 h-64 md:w-72 md:h-72 rounded-full overflow-hidden border border-brass/50" style={{ boxShadow: 'inset 0 0 60px rgba(0,0,0,0.85), 0 0 0 1px rgba(0,0,0,0.6)', background: '#0b100c' }}>
        {state === 'closed' && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="font-mono text-[10px] tracking-[0.35em] text-parchment-faint text-center leading-loose px-8">THE LENS IS SHUT</div>
          </div>
        )}
        {(state === 'open') && (
          <>
            <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-cover -scale-x-100" />
            {count !== null && (
              <motion.div key={count} initial={{ opacity: 0, scale: 1.4 }} animate={{ opacity: 1, scale: 1 }} className="absolute inset-0 flex items-center justify-center">
                <span className="font-display text-7xl text-parchment/90">{count}</span>
              </motion.div>
            )}
          </>
        )}
        {state === 'captured' && img && (
          <motion.img src={img} alt="capture" className="w-full h-full object-cover" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={transition('ARCHIVE')} />
        )}
        {state === 'denied' && (
          <div className="absolute inset-0 flex items-center justify-center px-8">
            <p className="font-mono text-[10px] tracking-[0.3em] text-crimson/90 text-center leading-loose">THE LENS DECLINED.<br />CHOOSE ANOTHER CHANNEL.</p>
          </div>
        )}
        {/* lens reticle */}
        <div className="absolute inset-6 rounded-full border border-olive-3/50 pointer-events-none" />
        <div className="absolute top-1/2 left-3 right-3 h-px bg-gold/20 pointer-events-none" />
        <div className="absolute left-1/2 top-3 bottom-3 w-px bg-gold/20 pointer-events-none" />
      </div>
      {state === 'captured' && (
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-6 font-mono text-[10px] tracking-[0.35em] text-amber/80">
          THE MACHINE HAS YOUR FACE
        </motion.p>
      )}
      <div className="mt-8 flex justify-center">
        {state === 'closed' && (
          <button className="brass-button px-8 py-3 min-h-[44px]" onClick={openLens}>LET IT LOOK</button>
        )}
      </div>
    </motion.div>
  );
}

/* ————— Stage 02 ————— */
export default function Stage02Offering({ onComplete }: { onComplete: (o: Offering) => void }) {
  const [channel, setChannel] = useState<OfferingChannel | null>(null);
  const [received, setReceived] = useState(false);

  const handleSubmit = (o: Offering) => {
    setReceived(true);
    window.setTimeout(() => onComplete(o), 900);
  };

  return (
    <div className="relative min-h-[100dvh] flex flex-col items-center justify-center px-5 py-24">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={transition('REVEAL')} className="text-center mb-10">
        <div className="meta-label mb-3">THE OFFERING</div>
        <h2 className="font-display text-3xl md:text-5xl tracking-[0.1em] text-balance">GIVE THE MACHINE SOMETHING</h2>
        <p className="mt-4 font-serif italic text-parchment-dim text-sm md:text-base">choose a channel — each is a different part of the same machine</p>
      </motion.div>

      {/* the four channels */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-5 w-full max-w-3xl mb-12">
        {CHANNELS.map((c, i) => {
          const active = channel === c.id;
          return (
            <motion.button
              key={c.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={transition('RESPOND', 0.15 + i * 0.12)}
              onClick={() => setChannel(c.id)}
              className={`min-h-[88px] md:min-h-[104px] px-3 py-4 border transition-colors duration-500 text-center ${
                active ? 'border-gold/80 bg-olive/40' : 'border-olive-3/60 bg-forest-2/60 hover:border-brass/60'
              }`}
            >
              <div className={`font-mono text-xs md:text-sm tracking-[0.4em] ${active ? 'text-gold' : 'text-parchment'}`}>{c.label}</div>
              <div className="mt-2 font-serif italic text-[11px] md:text-xs text-parchment-faint">{c.sub}</div>
            </motion.button>
          );
        })}
      </div>

      <div className="w-full min-h-[300px]">
        <AnimatePresence mode="wait">
          {channel === 'write' && !received && <WriteChannel key="write" onSubmit={handleSubmit} />}
          {channel === 'speak' && !received && <SpeakChannel key="speak" onSubmit={handleSubmit} />}
          {channel === 'show' && !received && <ShowChannel key="show" onSubmit={handleSubmit} />}
          {channel === 'look' && !received && <LookChannel key="look" onSubmit={handleSubmit} />}
        </AnimatePresence>
        {received && (
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={transition('SETTLE')} className="text-center font-mono text-[10px] tracking-[0.4em] text-gold">
            THE OFFERING IS RECEIVED
          </motion.p>
        )}
      </div>
    </div>
  );
}
