import { useRef, useState, type ChangeEvent, type KeyboardEvent } from 'react';
import './Chat.css';

export interface ComposerProps {
  onSend: (text: string) => void;
  onAttach: (file: File) => void;
  onMic: () => void;
  sending: boolean;
}

function PaperclipIcon(): JSX.Element {
  return (
    <svg width="18" height="18" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path
        d="M13.5 6.5l-6 6a2.5 2.5 0 0 0 3.5 3.5l6.5-6.5a4 4 0 1 0-5.66-5.66l-6.5 6.5a5.5 5.5 0 1 0 7.78 7.78"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function MicIcon(): JSX.Element {
  return (
    <svg width="18" height="18" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <rect x="7.5" y="2.5" width="5" height="9" rx="2.5" stroke="currentColor" strokeWidth="1.4" />
      <path d="M4.5 10a5.5 5.5 0 0 0 11 0" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      <path d="M10 15.5V18" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}

function StopIcon(): JSX.Element {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <rect x="5" y="5" width="10" height="10" rx="2" fill="currentColor" />
    </svg>
  );
}

function SendIcon(): JSX.Element {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M8 13V3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M3.5 7.5L8 3l4.5 4.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function Composer({ onSend, onAttach, onMic, sending }: ComposerProps): JSX.Element {
  const [value, setValue] = useState('');
  const [recording, setRecording] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function handleMicClick(): void {
    if (recording) {
      // Second click: stop "recording" and send the voice prompt.
      setRecording(false);
      onMic();
    } else {
      // First click: enter recording state (red square).
      setRecording(true);
    }
  }

  const canSend = value.trim().length > 0 && !sending;

  function autoGrow(el: HTMLTextAreaElement): void {
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }

  function handleChange(e: ChangeEvent<HTMLTextAreaElement>): void {
    setValue(e.target.value);
    autoGrow(e.target);
  }

  function submit(): void {
    const trimmed = value.trim();
    if (!trimmed || sending) return;
    onSend(trimmed);
    setValue('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>): void {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  function handleFileChange(e: ChangeEvent<HTMLInputElement>): void {
    const file = e.target.files?.[0];
    if (file) onAttach(file);
    e.target.value = '';
  }

  return (
    <div>
      <div className="composer">
        <button
          type="button"
          className="composer__icon-btn"
          aria-label="Attach a file"
          onClick={() => fileInputRef.current?.click()}
        >
          <PaperclipIcon />
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*,application/pdf"
          onChange={handleFileChange}
          style={{ display: 'none' }}
        />

        <textarea
          ref={textareaRef}
          className="composer__textarea"
          placeholder="Message Nyayra…"
          rows={1}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          aria-label="Message Nyayra"
        />

        <button
          type="button"
          className={`composer__icon-btn${recording ? ' composer__icon-btn--recording' : ''}`}
          aria-label={recording ? 'Stop recording and send' : 'Use microphone'}
          aria-pressed={recording}
          onClick={handleMicClick}
        >
          {recording ? <StopIcon /> : <MicIcon />}
        </button>

        <button
          type="button"
          className="composer__send"
          aria-label="Send message"
          disabled={!canSend}
          onClick={submit}
        >
          <SendIcon />
        </button>
      </div>
      <p className="composer__disclaimer">
        Nyayra gives legal understanding, not legal advice. It flags when you need a lawyer.
      </p>
    </div>
  );
}
