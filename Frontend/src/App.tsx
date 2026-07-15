import { useEffect, useMemo, useState } from 'react';
import Sidebar from './components/Sidebar';
import TopBar from './components/TopBar';
import ChatView from './components/ChatView';
import { getDrafts, listChats, parseDocument, sendMessage, transcribeVoice, uid } from './lib/api';
import type { DemoFlow } from './lib/api';
import { DEMO_MODE } from './lib/api';
import { DEMO_CONFIG, answerFor, docReply, scriptedFor, voiceReply } from './lib/demo';
import { speak, spokenSummary, stopSpeaking } from './lib/tts';
import type { CouncilStage, LegalAnswer } from './lib/types';

// Optional URL override for filming: ?think=30 → 30s deliberation per answer.
function thinkOverrideMs(): number | null {
  const raw = new URLSearchParams(window.location.search).get('think');
  if (!raw) return null;
  const secs = Number(raw);
  return Number.isFinite(secs) && secs > 0 ? secs * 1000 : null;
}

// Offline / on-device mode: the whole pipeline collapses onto the local E-model,
// so the trace is short and the answer is terser.
const OFFLINE_COUNCIL: CouncilStage[] = [
  { id: 'off1', label: 'E2B · on-device mask', role: 'Identifiers stripped locally — nothing leaves the phone', status: 'done' },
  { id: 'off2', label: 'E-model · local reasoning', role: 'Rights, options and next step reasoned fully on-device', status: 'done' },
  { id: 'off3', label: 'E2B · draft + unmask', role: 'Answer composed and restored on-device', status: 'done' },
];

// Terser answer for the offline path (smaller local model → shorter reply).
function shortenAnswer(a: LegalAnswer): LegalAnswer {
  return {
    rights: a.rights.slice(0, 2),
    options: a.options.slice(0, 1),
    nextStep: a.nextStep.slice(0, 1),
    needsLawyer: a.needsLawyer,
    lawyerNote: a.lawyerNote,
  };
}
import type { Attachment, Chat, Draft, LangCode, Message, Mode } from './lib/types';
import './App.css';

export default function App() {
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [lang, setLang] = useState<LangCode>('en');
  const [mode, setMode] = useState<Mode>('cloud');
  const [voiceOut, setVoiceOut] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  const [chats, setChats] = useState<Chat[]>([]);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  // Reflect theme on <html> so theme.css tokens flip.
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  // Load initial data through the API seam (empty until backend connected).
  useEffect(() => {
    listChats().then(setChats).catch(() => setChats([]));
    getDrafts().then(setDrafts).catch(() => setDrafts([]));
  }, []);

  const activeChat = useMemo(
    () => chats.find((c) => c.id === activeChatId) ?? null,
    [chats, activeChatId],
  );
  const messages = activeChat?.messages ?? [];
  const title = activeChat?.title ?? 'New chat';

  function patchChat(id: string, updater: (c: Chat) => Chat) {
    setChats((prev) => prev.map((c) => (c.id === id ? updater(c) : c)));
  }

  function handleNewChat() {
    setActiveChatId(null);
  }

  function ensureChat(firstText: string): string {
    if (activeChatId) return activeChatId;
    const id = uid('chat');
    const newChat: Chat = {
      id,
      title: firstText.slice(0, 42) || 'New chat',
      updatedAt: Date.now(),
      messages: [],
    };
    setChats((prev) => [newChat, ...prev]);
    setActiveChatId(id);
    return id;
  }

  async function handleSend(text: string, attachments: Attachment[] = [], flow?: DemoFlow) {
    const trimmed = text.trim();
    if (!trimmed && attachments.length === 0) return;
    const chatId = ensureChat(trimmed || (attachments[0]?.name ?? 'New chat'));

    const userMsg: Message = {
      id: uid('msg'),
      role: 'user',
      text: trimmed,
      attachments,
      lang,
      createdAt: Date.now(),
    };
    const pendingId = uid('msg');

    // In demo mode we know the scripted answer up front, so we can drive the
    // live council animation for exactly `thinkingMs` and then reveal.
    if (DEMO_MODE) {
      stopSpeaking(); // cut any previous spoken reply

      const scripted: { answer: LegalAnswer; council: CouncilStage[]; thinkingMs: number } =
        flow === 'voice' ? { ...voiceReply(), thinkingMs: DEMO_CONFIG.thinkingMs }
        : flow === 'document' ? { ...docReply(), thinkingMs: DEMO_CONFIG.thinkingMs }
        : scriptedFor(trimmed, lang) ?? { ...answerFor(trimmed, lang), thinkingMs: DEMO_CONFIG.thinkingMs };

      // Offline / local mode: shorter answer, shorter trace, faster reveal.
      const offline = mode === 'local';
      const answer = offline ? shortenAnswer(scripted.answer) : scripted.answer;
      const council = offline ? OFFLINE_COUNCIL : scripted.council;
      const baseThink = offline ? Math.max(1800, Math.round(scripted.thinkingMs * 0.45)) : scripted.thinkingMs;
      const thinkingMs = thinkOverrideMs() ?? baseThink;

      // Speak the reply for mic input, or whenever voice-out is on.
      const speakLang = flow === 'voice' ? 'hi' : lang;
      const shouldSpeak = flow === 'voice' || voiceOut;

      const pendingMsg: Message = {
        id: pendingId,
        role: 'assistant',
        pending: true,
        council, // LiveThinking re-drives these stages
        thinkingMs,
        lang,
        createdAt: Date.now(),
      };
      patchChat(chatId, (c) => ({ ...c, updatedAt: Date.now(), messages: [...c.messages, userMsg, pendingMsg] }));
      setSending(true);

      window.setTimeout(() => {
        patchChat(chatId, (c) => ({
          ...c,
          messages: c.messages.map((m) =>
            m.id === pendingId
              ? { id: pendingId, role: 'assistant', answer, council, lang, createdAt: Date.now() }
              : m,
          ),
        }));
        setSending(false);
        if (shouldSpeak) speak(spokenSummary(answer), speakLang);
      }, thinkingMs);
      return;
    }

    const pendingMsg: Message = {
      id: pendingId,
      role: 'assistant',
      pending: true,
      lang,
      createdAt: Date.now(),
    };
    patchChat(chatId, (c) => ({
      ...c,
      updatedAt: Date.now(),
      messages: [...c.messages, userMsg, pendingMsg],
    }));

    setSending(true);
    try {
      const reply = await sendMessage({ chatId, text: trimmed, lang, mode, attachmentIds: attachments.map((a) => a.id) }, flow);
      patchChat(chatId, (c) => ({
        ...c,
        messages: c.messages.map((m) => (m.id === pendingId ? { ...reply, id: pendingId } : m)),
      }));
    } catch {
      patchChat(chatId, (c) => ({
        ...c,
        messages: c.messages.map((m) =>
          m.id === pendingId ? { ...m, pending: false, text: 'Could not reach Nyayra. Connect the backend to enable answers.' } : m,
        ),
      }));
    } finally {
      setSending(false);
    }
  }

  async function handleAttach(file: File) {
    const kind: Attachment['kind'] = file.type.startsWith('image/')
      ? 'image'
      : file.type === 'application/pdf'
        ? 'pdf'
        : 'audio';
    const att: Attachment = {
      id: uid('att'),
      name: file.name,
      kind,
      sizeLabel: `${Math.max(1, Math.round(file.size / 1024))} KB`,
    };
    if (DEMO_MODE) {
      // Simulate document parsing → scripted one-sided-contract answer.
      const { summary } = await parseDocument(file);
      handleSend(summary ?? 'Please review this document.', [att], 'document');
      return;
    }
    // Placeholder: surface the attachment as its own user turn (backend will parse it).
    handleSend('', [att]);
  }

  async function handleMic() {
    if (DEMO_MODE) {
      // Simulate an ASR-free voice note: transcript in, scripted Hindi answer out.
      setLang('hi');
      const { text } = await transcribeVoice(new Blob(), 'hi');
      const att: Attachment = { id: uid('att'), name: 'voice-note.m4a', kind: 'audio', sizeLabel: '38 KB' };
      handleSend(text, [att], 'voice');
      return;
    }
    // eslint-disable-next-line no-alert
    alert('Voice input will stream audio to Nyayra once the backend is connected.');
  }

  return (
    <div className="app-shell">
      <Sidebar
        chats={chats}
        activeChatId={activeChatId}
        onNewChat={handleNewChat}
        onSelectChat={setActiveChatId}
        drafts={drafts}
        onOpenDraft={() => {}}
        lang={lang}
        onChangeLang={setLang}
        mode={mode}
        onToggleMode={() => setMode((m) => (m === 'cloud' ? 'local' : 'cloud'))}
        collapsed={collapsed}
        onToggleCollapse={() => setCollapsed((v) => !v)}
      />
      <div className="app-main">
        <TopBar
          title={title}
          mode={mode}
          voiceOut={voiceOut}
          onToggleVoiceOut={() =>
            setVoiceOut((v) => {
              if (v) stopSpeaking();
              return !v;
            })
          }
          theme={theme}
          onToggleTheme={() => setTheme((t) => (t === 'light' ? 'dark' : 'light'))}
          onToggleSidebar={() => setCollapsed((v) => !v)}
        />
        <ChatView
          messages={messages}
          lang={lang}
          sending={sending}
          onSend={(t) => handleSend(t)}
          onAttach={handleAttach}
          onMic={handleMic}
        />
      </div>
    </div>
  );
}
