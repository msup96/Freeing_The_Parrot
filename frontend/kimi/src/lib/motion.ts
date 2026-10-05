import type { Transition } from 'framer-motion';

export const MECHANICAL: [number, number, number, number] = [0.85, 0, 0.15, 1];

const EASE: Record<string, [number, number, number, number]> = {
  REVEAL: [0.16, 1, 0.3, 1],
  RESPOND: [0.22, 1, 0.36, 1],
  SETTLE: [0.45, 0, 0.1, 1],
  ARCHIVE: [0.4, 0, 0.2, 1],
  ERASE: [0.5, 0, 0.75, 0.4],
  EXIT: [0.45, 0, 0.1, 1],
};

export function transition(kind: string, delay = 0): Transition {
  return {
    duration: kind === 'ERASE' ? 0.85 : 0.8,
    ease: EASE[kind] ?? MECHANICAL,
    delay,
  };
}
