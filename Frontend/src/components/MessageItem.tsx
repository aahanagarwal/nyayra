import type { Attachment, Message } from '../lib/types';
import CouncilTrace from './CouncilTrace';
import LiveThinking from './LiveThinking';
import './Chat.css';

export interface MessageItemProps {
  message: Message;
}

function AttachmentIcon({ kind }: { kind: Attachment['kind'] }): JSX.Element {
  if (kind === 'image') {
    return (
      <svg width="12" height="12" viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <rect x="2" y="2.5" width="12" height="11" rx="1.5" stroke="currentColor" strokeWidth="1.3" />
        <circle cx="5.5" cy="6" r="1.1" fill="currentColor" />
        <path d="M3 11.5l3.3-3.3a1 1 0 0 1 1.4 0L13 13" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }
  if (kind === 'pdf') {
    return (
      <svg width="12" height="12" viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <path d="M4 1.5h5.5L12.5 4.5V14.5H4z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
        <path d="M9.5 1.5V4.5H12.5" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
      </svg>
    );
  }
  return (
    <svg width="12" height="12" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <rect x="6" y="1.5" width="4" height="8" rx="2" stroke="currentColor" strokeWidth="1.3" />
      <path d="M3.5 8a4.5 4.5 0 0 0 9 0" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      <path d="M8 12.5v2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
}

function PendingIndicator(): JSX.Element {
  return (
    <div className="msg__pending">
      <span className="msg__pending-dots" aria-hidden="true">
        <span />
        <span />
        <span />
      </span>
      Nyayra is deliberating…
    </div>
  );
}

export default function MessageItem({ message }: MessageItemProps): JSX.Element {
  if (message.role === 'user') {
    return (
      <div className="msg msg--user">
        <div>
          <div className="msg__bubble">
            {message.text}
          </div>
          {message.attachments && message.attachments.length > 0 && (
            <div className="msg__attachments">
              {message.attachments.map((att) => (
                <span key={att.id} className="msg__chip">
                  <AttachmentIcon kind={att.kind} />
                  {att.name}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="msg msg--assistant">
      <div className="msg__assistant-content">
        {message.pending && (
          message.council && message.council.length > 0
            ? <LiveThinking stages={message.council} thinkingMs={message.thinkingMs ?? 6000} />
            : <PendingIndicator />
        )}

        {!message.pending && message.answer && (
          <div className="answer answer--reveal">
            <div className="answer__block">
              <p className="answer__heading">Your rights</p>
              <ul className="answer__list">
                {message.answer.rights.map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </div>
            <div className="answer__block">
              <p className="answer__heading">Your options</p>
              <ul className="answer__list">
                {message.answer.options.map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </div>
            <div className="answer__block">
              <p className="answer__heading">Your next step</p>
              <ul className="answer__list">
                {message.answer.nextStep.map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </div>
            {message.answer.needsLawyer && (
              <div className="answer__lawyer">
                <span aria-hidden="true">⚖</span>
                <div>
                  <p className="answer__lawyer-title">A human lawyer is genuinely recommended here</p>
                  {message.answer.lawyerNote && (
                    <p className="answer__lawyer-note">{message.answer.lawyerNote}</p>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {!message.pending && !message.answer && message.text && (
          <div className="msg__text">{message.text}</div>
        )}

        {!message.pending && message.council && (
          <CouncilTrace stages={message.council} />
        )}
      </div>
    </div>
  );
}
