import type { CouncilStage } from '../lib/types';
import './Chat.css';

export interface CouncilTraceProps {
  stages?: CouncilStage[];
}

export default function CouncilTrace({ stages }: CouncilTraceProps): JSX.Element | null {
  if (!stages || stages.length === 0) return null;

  return (
    <details className="council">
      <summary className="council__summary">
        <svg
          className="council__chevron"
          width="12"
          height="12"
          viewBox="0 0 12 12"
          fill="none"
          aria-hidden="true"
        >
          <path d="M4 2l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        How Nyayra reached this — council trace
      </summary>
      <div className="council__steps">
        {stages.map((stage) => (
          <div
            key={stage.id}
            className={`council__step${stage.status === 'pending' ? ' council__step--pending' : ''}`}
          >
            <span className="council__dot" aria-hidden="true" />
            <div className="council__label">{stage.label}</div>
            <div className="council__role">{stage.role}</div>
          </div>
        ))}
      </div>
    </details>
  );
}
