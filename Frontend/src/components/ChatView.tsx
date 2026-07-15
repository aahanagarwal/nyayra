import { useEffect, useRef } from 'react';
import type { LangCode, Message } from '../lib/types';
import EmptyState from './EmptyState';
import MessageItem from './MessageItem';
import Composer from './Composer';
import './Chat.css';

export interface ChatViewProps {
  messages: Message[];
  lang: LangCode;
  sending: boolean;
  onSend: (text: string) => void;
  onAttach: (file: File) => void;
  onMic: () => void;
}

export default function ChatView({
  messages,
  sending,
  onSend,
  onAttach,
  onMic,
}: ChatViewProps): JSX.Element {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages]);

  return (
    <div className="chat-view">
      <div className="chat-view__scroll">
        <div className="chat-view__col">
          {messages.length === 0 ? (
            <EmptyState onPick={(text) => onSend(text)} />
          ) : (
            <>
              {messages.map((message) => (
                <MessageItem key={message.id} message={message} />
              ))}
              <div ref={bottomRef} />
            </>
          )}
        </div>
      </div>

      <div className="chat-view__composer-dock">
        <div className="chat-view__composer-col">
          <Composer onSend={onSend} onAttach={onAttach} onMic={onMic} sending={sending} />
        </div>
      </div>
    </div>
  );
}
