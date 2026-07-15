import './Chat.css';

export interface EmptyStateProps {
  onPick: (text: string) => void;
}

const SAMPLE_PROMPTS: string[] = [
  'A landlord served me an eviction notice — what are my rights?',
  'Is this rental agreement one-sided? (attach the document)',
  'My insurance claim was rejected. What can I do?',
  'Draft a reply to a police complaint notice.',
];

export default function EmptyState({ onPick }: EmptyStateProps): JSX.Element {
  return (
    <div className="empty-state">
      <div className="empty-state__logo" aria-hidden="true">N</div>
      <h1 className="empty-state__headline">Justice you can talk to.</h1>
      <p className="empty-state__subline">
        Describe your situation in your own language. Nyayra reads it, reasons about it, and
        hands back your rights, your options, and your next step.
      </p>
      <div className="empty-state__cards">
        {SAMPLE_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            type="button"
            className="empty-state__card"
            onClick={() => onPick(prompt)}
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
}
