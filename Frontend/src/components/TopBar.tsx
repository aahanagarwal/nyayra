import type { Mode } from '../lib/types';
import './TopBar.css';

export interface TopBarProps {
  title: string;              // current chat title, e.g. "New chat"
  mode: Mode;                 // 'cloud' | 'local'
  voiceOut: boolean;
  onToggleVoiceOut: () => void;
  theme: 'light' | 'dark';
  onToggleTheme: () => void;
  onToggleSidebar?: () => void;
}

function PanelIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="3" y="4" width="18" height="16" rx="2" stroke="currentColor" strokeWidth="1.8" />
      <line x1="9" y1="4" x2="9" y2="20" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

function LockIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="5" y="11" width="14" height="9" rx="2" stroke="currentColor" strokeWidth="1.8" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function CloudIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M7 18a4.5 4.5 0 0 1-.4-8.98A5.5 5.5 0 0 1 17.2 8.1 4 4 0 0 1 17 16H7Z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function SpeakerIcon({ muted }: { muted: boolean }) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M4 9.5v5h3.2L12 18.5v-13L7.2 9.5H4Z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
        fill={muted ? 'none' : 'currentColor'}
      />
      {muted ? (
        <line x1="16" y1="9" x2="21" y2="15" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      ) : (
        <path
          d="M15.5 8.5a4.5 4.5 0 0 1 0 7"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          fill="none"
        />
      )}
      {muted && (
        <line x1="21" y1="9" x2="16" y2="15" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      )}
    </svg>
  );
}

function SunIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="1.8" />
      <g stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
        <line x1="12" y1="2.5" x2="12" y2="4.5" />
        <line x1="12" y1="19.5" x2="12" y2="21.5" />
        <line x1="2.5" y1="12" x2="4.5" y2="12" />
        <line x1="19.5" y1="12" x2="21.5" y2="12" />
        <line x1="4.9" y1="4.9" x2="6.3" y2="6.3" />
        <line x1="17.7" y1="17.7" x2="19.1" y2="19.1" />
        <line x1="4.9" y1="19.1" x2="6.3" y2="17.7" />
        <line x1="17.7" y1="6.3" x2="19.1" y2="4.9" />
      </g>
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M20 14.5A8.5 8.5 0 1 1 9.5 4a6.8 6.8 0 0 0 10.5 10.5Z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function TopBar(props: TopBarProps) {
  const { title, mode, voiceOut, onToggleVoiceOut, theme, onToggleTheme, onToggleSidebar } = props;

  return (
    <header className="topbar">
      <div className="topbar-left">
        {onToggleSidebar && (
          <button
            type="button"
            className="topbar-icon-btn"
            onClick={onToggleSidebar}
            aria-label="Toggle sidebar"
            title="Toggle sidebar"
          >
            <PanelIcon />
          </button>
        )}
        <span className="topbar-title">{title}</span>
      </div>

      <div className="topbar-right">
        {mode === 'local' ? (
          <span className="topbar-mode-badge topbar-mode-badge--local">
            <LockIcon />
            Local · offline
          </span>
        ) : (
          <span className="topbar-mode-badge topbar-mode-badge--cloud">
            <CloudIcon />
            Cloud
          </span>
        )}

        <button
          type="button"
          className={`topbar-icon-btn${voiceOut ? ' topbar-icon-btn--active' : ''}`}
          onClick={onToggleVoiceOut}
          aria-pressed={voiceOut}
          aria-label="Voice replies"
          title="Voice replies"
        >
          <SpeakerIcon muted={!voiceOut} />
        </button>

        <button
          type="button"
          className="topbar-icon-btn"
          onClick={onToggleTheme}
          aria-label="Toggle theme"
          title="Toggle theme"
        >
          {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
        </button>
      </div>
    </header>
  );
}
