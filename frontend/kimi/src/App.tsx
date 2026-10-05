import { useCallback, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Atmosphere, Chrome } from './components/Chrome';
import Stage01Apparatus from './stages/Stage01Apparatus';
import Stage02Offering from './stages/Stage02Offering';
import Stage03HiddenReader from './stages/Stage03HiddenReader';
import Stage04Parrot from './stages/Stage04Parrot';
import Stage06Deck from './stages/Stage06Deck';
import Stage07Break from './stages/Stage07Break';
import Stage08DataJourney from './stages/Stage08DataJourney';
import Stage09Exit from './stages/Stage09Exit';
import {
  advanceLifecycle,
  completeInput,
  endConversation,
  generateOutput,
  resetSession,
  sendChat,
  startSession,
  submitInitialMedia,
  submitInitialText,
} from './lib/api';
import { cardsFromServer } from './lib/deck';
import { emptySession, type ChatTurn, type Offering, type Session } from './lib/session';

function presentationBehaviour(value: string | undefined): string {
  const known: Record<string, string> = {
    memory_loss: 'memory-loss',
    system_glitch: 'glitch',
    help_me: 'help',
    banana: 'banana',
    mixed: 'mixed',
    mirroring: 'mirroring',
    roast: 'roast',
    absurd: 'absurd',
    understanding: 'understanding',
    listening: 'listening',
  };
  return known[value || ''] || value || 'understanding';
}

export default function App() {
  const [stage, setStage] = useState(1);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [session, setSession] = useState<Session>(emptySession);
  const [error, setError] = useState<string | null>(null);
  const broken = stage >= 7;

  const goTo = useCallback((next: number) => {
    window.scrollTo({ top: 0, behavior: 'instant' as ScrollBehavior });
    setStage(next);
  }, []);

  const handleEnter = useCallback(async () => {
    setError(null);
    try {
      const started = await startSession();
      setSessionId(started.session_id);
      goTo(2);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The apparatus could not start.');
    }
  }, [goTo]);

  const handleOffering = useCallback(async (offering: Offering) => {
    if (!sessionId) return;
    setError(null);
    try {
      const result = offering.text
        ? await submitInitialText(sessionId, offering.text)
        : offering.media
          ? await submitInitialMedia(
              sessionId,
              offering.channel === 'speak' ? 'AUDIO' : offering.channel === 'look' ? 'CAMERA' : 'IMAGE',
              offering.media,
              offering.filename || 'offering.bin',
            )
          : null;

      if (!result?.analysis_ready) {
        throw new Error('This offering was received, but its required analysis is not available yet.');
      }

      await completeInput(sessionId);
      setSession((current) => ({ ...current, offering }));
      goTo(3);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The offering could not be processed.');
    }
  }, [goTo, sessionId]);

  const handleChat = useCallback(async (text: string) => {
    if (!sessionId) throw new Error('Session identity is missing.');
    const result = await sendChat(sessionId, text);
    if (!result.response.trim()) {
      throw new Error('The machine returned an empty reply.');
    }
    return {
      text: result.response,
      behaviour: presentationBehaviour(result.parrot_behavior),
      closed: Boolean(result.closed),
    };
  }, [sessionId]);

  const handleTurns = useCallback((turns: ChatTurn[]) => {
    setSession((current) => ({ ...current, turns }));
  }, []);

  const handleDeck = useCallback(async () => {
    if (!sessionId) return;
    try {
      const closed = await endConversation(sessionId);
      const cards = cardsFromServer(closed.cards);
      if (cards.length !== 27) {
        throw new Error('This session did not return a 27-card reading.');
      }
      setSession((current) => ({ ...current, cards }));
      goTo(6);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The conversation could not close.');
    }
  }, [goTo, sessionId]);

  const handleCard = useCallback(async (card: { id: number; cardId: string }) => {
    if (!sessionId) return;
    try {
      await advanceLifecycle(sessionId, 'card_selection', {
        card_index: card.id,
        card_id: card.cardId,
      });
      setSession((current) => ({ ...current, cardId: card.id, selectedCard: card as Session['selectedCard'] }));
      goTo(7);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'That card could not be marked.');
    }
  }, [goTo, sessionId]);

  const handleReveal = useCallback(async () => {
    if (!sessionId) return;
    try {
      await advanceLifecycle(sessionId, 'reveal');
      goTo(8);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The reveal is not ready.');
    }
  }, [goTo, sessionId]);

  const handleConsent = useCallback(async (consent: 'private' | 'wall') => {
    if (!sessionId) return;
    const consentType = consent === 'wall' ? 'SHARE' : 'KEEP_PRIVATE';
    try {
      await advanceLifecycle(sessionId, 'consent', { consent_type: consentType });
      await generateOutput(sessionId);
      setSession((current) => ({ ...current, consent }));
      goTo(9);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Consent or output failed.');
    }
  }, [goTo, sessionId]);

  const restart = useCallback(async () => {
    if (sessionId && session.consent) {
      await resetSession(sessionId, session.consent === 'wall' ? 'SHARE' : 'KEEP_PRIVATE');
    }
    setSessionId(null);
    setSession(emptySession);
    setError(null);
    goTo(1);
  }, [goTo, session.consent, sessionId]);

  return (
    <div className="relative min-h-[100dvh]">
      {!broken && <Atmosphere />}
      {stage !== 9 && <Chrome stage={stage} broken={broken} />}
      {error && (
        <div className="fixed bottom-4 left-1/2 z-[80] -translate-x-1/2 max-w-[90vw] border border-crimson/60 bg-forest px-4 py-3 font-mono text-xs text-crimson">
          {error}
        </div>
      )}
      <AnimatePresence mode="wait">
        <motion.main
          key={stage}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0, transition: { duration: stage >= 7 ? 0.12 : 0.5 } }}
          transition={{ duration: stage >= 7 ? 0.12 : 0.7 }}
        >
          {stage === 1 && <Stage01Apparatus onEnter={() => void handleEnter()} />}
          {stage === 2 && <Stage02Offering onComplete={(offering) => void handleOffering(offering)} />}
          {stage === 3 && <Stage03HiddenReader offering={session.offering} onComplete={() => goTo(4)} />}
          {stage === 4 && (
            <Stage04Parrot
              turns={session.turns}
              onTurns={handleTurns}
              onChat={handleChat}
              onError={setError}
              onDeck={() => void handleDeck()}
            />
          )}
          {stage === 6 && <Stage06Deck cards={session.cards} onComplete={(card) => void handleCard(card)} />}
          {stage === 7 && session.selectedCard && <Stage07Break card={session.selectedCard} onComplete={() => void handleReveal()} />}
          {stage === 8 && <Stage08DataJourney session={session} onConsent={(consent) => void handleConsent(consent)} />}
          {stage === 9 && <Stage09Exit session={session} onRestart={() => void restart()} />}
        </motion.main>
      </AnimatePresence>
    </div>
  );
}