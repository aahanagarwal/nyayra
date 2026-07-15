import type { Draft } from '../lib/types';

export default function DraftLibrary({
  drafts,
  onOpenDraft,
}: {
  drafts: Draft[];
  onOpenDraft: (id: string) => void;
}) {
  return (
    <div className="sb-section">
      <div className="sb-section-label">Drafts</div>
      {drafts.length === 0 ? (
        <div className="sb-empty">Drafts you create will appear here.</div>
      ) : (
        <ul className="sb-list">
          {drafts.map((d) => (
            <li key={d.id}>
              <button
                type="button"
                className="sb-row sb-draft-row"
                onClick={() => onOpenDraft(d.id)}
                title={d.title}
              >
                <svg
                  className="sb-row-icon"
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="M14 3v4a1 1 0 0 0 1 1h4" />
                  <path d="M17 21H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2Z" />
                  <path d="M9 13h6" />
                  <path d="M9 17h6" />
                </svg>
                <span className="sb-row-text">{d.title}</span>
                <span className="sb-chip">{d.kind}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
