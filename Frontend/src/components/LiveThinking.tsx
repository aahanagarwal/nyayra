import { useEffect, useRef, useState } from 'react';
import type { CouncilStage } from '../lib/types';
import './LiveThinking.css';

export interface LiveThinkingProps {
  stages?: CouncilStage[];
  thinkingMs: number;
}

type Status = 'pending' | 'active' | 'done';

/**
 * Cinematic "council deliberating" panel shown while an assistant answer is
 * pending. Re-drives the incoming stages: each one goes pending → active → done,
 * evenly spaced across `thinkingMs`, so the Gemma cascade visibly lights up.
 */
export default function LiveThinking({ stages, thinkingMs }: LiveThinkingProps): JSX.Element {
  const list = stages && stages.length > 0 ? stages : FALLBACK;
  const [statuses, setStatuses] = useState<Status[]>(() => list.map(() => 'pending'));
  const [elapsed, setElapsed] = useState(0);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  useEffect(() => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
    const n = list.length;
    // Reserve a short tail so the final "done" state is visible before reveal.
    const usable = Math.max(1200, thinkingMs - 500);

    // Weighted timeline: the 26B-A4B council stages deliberate longest, and each
    // of the three takes an uneven share (advocate < opposition+bench < devil's
    // advocate). Other stages move quicker. Weights are relative, not seconds.
    const weights = list.map((s) => stageWeight(s.label));
    const total = weights.reduce((a, w) => a + w, 0) || 1;

    let acc = 0;
    for (let i = 0; i < n; i++) {
      const start = (acc / total) * usable;
      const slot = (weights[i] / total) * usable;
      acc += weights[i];
      timers.current.push(
        setTimeout(() => {
          setStatuses((prev) => {
            const next = [...prev];
            next[i] = 'active';
            return next;
          });
        }, Math.round(start)),
      );
      timers.current.push(
        setTimeout(() => {
          setStatuses((prev) => {
            const next = [...prev];
            next[i] = 'done';
            return next;
          });
        }, Math.round(start + slot * 0.82)),
      );
    }

    const started = performance.now();
    const tick = setInterval(() => {
      setElapsed(Math.min(1, (performance.now() - started) / thinkingMs));
    }, 80);
    timers.current.push(tick as unknown as ReturnType<typeof setTimeout>);

    return () => {
      timers.current.forEach(clearTimeout);
      clearInterval(tick);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [thinkingMs, list.length]);

  const activeStage = list[Math.max(0, statuses.lastIndexOf('active'))];

  return (
    <div className="live" role="status" aria-live="polite">
      <div className="live__head">
        <span className="live__spinner" aria-hidden="true" />
        <span className="live__title">Nyayra is deliberating</span>
        <span className="live__dots" aria-hidden="true"><span /><span /><span /></span>
      </div>

      <div className="live__bar" aria-hidden="true">
        <span className="live__bar-fill" style={{ width: `${Math.round(elapsed * 100)}%` }} />
      </div>

      <ol className="live__stages">
        {list.map((s, i) => (
          <li key={s.id} className={`live__stage live__stage--${statuses[i]}`}>
            <span className="live__marker" aria-hidden="true">
              {statuses[i] === 'done' ? (
                <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
                  <path d="M3.5 8.5l3 3 6-7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              ) : statuses[i] === 'active' ? (
                <span className="live__pulse" />
              ) : (
                <span className="live__idle" />
              )}
            </span>
            <span className="live__stage-text">
              <span className="live__stage-label">{s.label}</span>
              <span className="live__stage-role">{s.role}</span>
            </span>
          </li>
        ))}
      </ol>

      {activeStage && (
        <p className="live__caption">{activeStage.detail ?? activeStage.role}</p>
      )}
    </div>
  );
}

// Relative dwell time per stage, inferred from its label. The three council
// members deliberate longest and unevenly; verifier lingers a bit; the fast
// mask/router/unmask stages tick by quickly.
function stageWeight(label: string): number {
  const l = label.toLowerCase();
  if (l.includes('devil')) return 4.2;             // devil's advocate — longest
  if (l.includes('opposition') || l.includes('bench')) return 3.1;
  if (l.includes('advocate')) return 2.3;          // advocate
  if (l.includes('council')) return 2.8;           // any other generic council stage
  if (l.includes('verifier')) return 1.8;
  if (l.includes('sandbox') || l.includes('draft')) return 1.5;
  return 0.9;                                        // mask / router / unmask etc.
}

const FALLBACK: CouncilStage[] = [
  { id: 'f1', label: 'E2B · mask PII', role: 'Stripping identifiers', status: 'pending' },
  { id: 'f2', label: 'Council · 26B-A4B', role: 'Debating your case', status: 'pending' },
  { id: 'f3', label: 'E4B verifier', role: 'Checking against statute', status: 'pending' },
  { id: 'f4', label: '31B sandbox', role: 'Drafting the answer', status: 'pending' },
];
