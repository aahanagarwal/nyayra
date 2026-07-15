import { useEffect, useRef, useState } from 'react';
import type { Chat, Draft, LangCode, Mode } from '../lib/types';
import { LANGUAGES } from '../lib/types';
import DraftLibrary from './DraftLibrary';
import './Sidebar.css';

export interface SidebarProps {
  chats: Chat[];
  activeChatId: string | null;
  onNewChat: () => void;
  onSelectChat: (id: string) => void;
  drafts: Draft[];
  onOpenDraft: (id: string) => void;
  lang: LangCode;
  onChangeLang: (code: LangCode) => void;
  mode: Mode; // 'cloud' | 'local'
  onToggleMode: () => void; // toggles offline/local mode
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}

function NyayraLogo({ size = 28 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 28 28"
      aria-hidden="true"
      focusable="false"
    >
      <circle cx="14" cy="14" r="14" fill="#0f7a5a" />
      <text
        x="14"
        y="19"
        textAnchor="middle"
        fontSize="14"
        fontWeight="700"
        fill="#ffffff"
        fontFamily="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
      >
        N
      </text>
    </svg>
  );
}

function ChevronIcon({ collapsed }: { collapsed: boolean }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ transform: collapsed ? 'rotate(180deg)' : 'none' }}
      aria-hidden="true"
    >
      <path d="M15 18l-6-6 6-6" />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg
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
      <path d="M12 5v14" />
      <path d="M5 12h14" />
    </svg>
  );
}

function GlobeIcon() {
  return (
    <svg
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
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18" />
      <path d="M12 3a15 15 0 0 1 0 18a15 15 0 0 1 0-18Z" />
    </svg>
  );
}

function LockIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="5" y="11" width="14" height="9" rx="2" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
    </svg>
  );
}

function GearIcon() {
  return (
    <svg
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
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z" />
    </svg>
  );
}

export default function Sidebar(props: SidebarProps) {
  const {
    chats,
    activeChatId,
    onNewChat,
    onSelectChat,
    drafts,
    onOpenDraft,
    lang,
    onChangeLang,
    mode,
    onToggleMode,
    collapsed = false,
    onToggleCollapse,
  } = props;

  const [langOpen, setLangOpen] = useState(false);
  const langRef = useRef<HTMLDivElement | null>(null);
  const currentLang = LANGUAGES.find((l) => l.code === lang) ?? LANGUAGES[0];

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (langRef.current && !langRef.current.contains(e.target as Node)) {
        setLangOpen(false);
      }
    }
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, []);

  if (collapsed) {
    return (
      <aside className="sidebar sidebar--collapsed" aria-label="Sidebar">
        <div className="sb-header sb-header--collapsed">
          <NyayraLogo size={28} />
          {onToggleCollapse && (
            <button
              type="button"
              className="sb-icon-btn"
              aria-label="Expand sidebar"
              onClick={onToggleCollapse}
            >
              <ChevronIcon collapsed />
            </button>
          )}
        </div>
        <button
          type="button"
          className="sb-icon-btn sb-new-chat-collapsed"
          aria-label="New chat"
          onClick={onNewChat}
        >
          <PlusIcon />
        </button>
      </aside>
    );
  }

  return (
    <aside className="sidebar" aria-label="Sidebar">
      <div className="sb-header">
        <div className="sb-brand">
          <NyayraLogo size={28} />
          <span className="sb-wordmark">Nyayra</span>
        </div>
        {onToggleCollapse && (
          <button
            type="button"
            className="sb-icon-btn"
            aria-label="Collapse sidebar"
            onClick={onToggleCollapse}
          >
            <ChevronIcon collapsed={false} />
          </button>
        )}
      </div>

      <button type="button" className="sb-new-chat" onClick={onNewChat}>
        <PlusIcon />
        <span>New chat</span>
      </button>

      <div className="sb-scroll">
        <div className="sb-section">
          <div className="sb-section-label">Recent</div>
          {chats.length === 0 ? (
            <div className="sb-empty">No conversations yet</div>
          ) : (
            <ul className="sb-list">
              {chats.map((c) => (
                <li key={c.id}>
                  <button
                    type="button"
                    className={
                      'sb-row sb-chat-row' +
                      (c.id === activeChatId ? ' sb-row--active' : '')
                    }
                    onClick={() => onSelectChat(c.id)}
                    title={c.title}
                  >
                    <span className="sb-row-text">{c.title}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <DraftLibrary drafts={drafts} onOpenDraft={onOpenDraft} />
      </div>

      <div className="sb-footer">
        <div className="sb-lang" ref={langRef}>
          <button
            type="button"
            className="sb-footer-row sb-lang-btn"
            aria-haspopup="listbox"
            aria-expanded={langOpen}
            aria-label="Change language"
            onClick={() => setLangOpen((v) => !v)}
          >
            <GlobeIcon />
            <span className="sb-row-text">{currentLang.label}</span>
          </button>
          {langOpen && (
            <ul className="sb-lang-menu" role="listbox">
              {LANGUAGES.map((l) => (
                <li key={l.code} role="option" aria-selected={l.code === lang}>
                  <button
                    type="button"
                    className={
                      'sb-lang-option' + (l.code === lang ? ' sb-lang-option--active' : '')
                    }
                    onClick={() => {
                      onChangeLang(l.code);
                      setLangOpen(false);
                    }}
                  >
                    <span>{l.label}</span>
                    <span className="sb-lang-english">{l.english}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <button
          type="button"
          className="sb-footer-row sb-mode-row"
          onClick={onToggleMode}
          aria-pressed={mode === 'local'}
        >
          <span
            className={
              'sb-switch' + (mode === 'local' ? ' sb-switch--on' : '')
            }
            aria-hidden="true"
          >
            <span className="sb-switch-knob" />
          </span>
          <span className="sb-mode-text">
            {mode === 'local' ? (
              <>
                <LockIcon />
                <span>On-device &middot; nothing leaves this phone</span>
              </>
            ) : (
              <span>Cloud</span>
            )}
          </span>
        </button>

        <button type="button" className="sb-footer-row sb-settings-row" onClick={() => {}}>
          <GearIcon />
          <span className="sb-row-text">Settings</span>
        </button>
      </div>
    </aside>
  );
}
