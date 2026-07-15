import wweb from 'whatsapp-web.js';
import { log } from '../utils/logger.js';
import { makePdf } from '../features/pdf.js';

const { MessageMedia } = wweb;

// ---------------------------------------------------------------------------
// DEMO MODE — everything below is hardcoded for a scripted demo video.
// The bot only ever replies to DEMO_NUMBER, always sends a "processing" ack
// first, and plays out two canned flows:
//   1) Text  -> landlord eviction options -> offer to draft -> "yes" -> PDF
//   2) Audio -> Hindi answer (police seized my car in Haryana)
// ---------------------------------------------------------------------------

// Only this number gets replies. Compared as a bare-digits substring so it
// matches whatever country-code form WhatsApp hands us (e.g. 919773883337@c.us).
const DEMO_NUMBER = (process.env.DEMO_NUMBER || '9773883337').replace(/\D/g, '');

const wait = (ms) => new Promise((r) => setTimeout(r, ms));

const PROCESSING = '⏳ *Processing your query…*\nGive me a moment while I look into this. 🔎';

const EVICTION_OPTIONS = `⚖️ *Your options as a landlord*

Here's how eviction works for a residential tenancy in India. You generally *cannot* remove a tenant by force or by cutting utilities — that's illegal. You have to go through the proper route:

*1. Check your legal grounds.* Courts allow eviction for specific reasons, most commonly:
   • Non-payment of rent
   • Breach of the tenancy agreement
   • The tenant subletting without permission
   • You genuinely needing the premises for yourself
   • Property being misused or damaged

*2. Serve a written eviction / quit notice.* This is the mandatory first step. It formally tells the tenant to vacate, states your grounds, and gives a reasonable notice period (commonly 15–30 days).

*3. If they don't leave, file an eviction suit* before the Rent Controller / competent civil court under your State's Rent Control Act. The court hears both sides and passes an order.

*4. Execute the court's order* through the court bailiff if the tenant still refuses.

💡 *Fastest lawful start:* a properly drafted eviction notice. It often resolves things without going to court, and it's also required evidence if you do.

Would you like me to *draft a formal eviction notice* for you now? Reply *Yes* and I'll prepare it as a ready-to-send PDF. ✍️`;

const EVICTION_PDF_CAPTION = `✅ *Here's your eviction notice.*

I've prepared a formal "Notice to Quit and Vacate" as a PDF. Review the highlighted fields (names, address, dates, rent amount), fill in anything marked in brackets, then serve it on the tenant — keep proof of delivery.

_This is a draft for your understanding, not a substitute for a lawyer._`;

const EVICTION_NOTICE_TEXT = `NOTICE TO QUIT AND VACATE
(Under the applicable State Rent Control Act)

Date: [DD/MM/YYYY]

To,
[Tenant's Full Name]
[Full Address of the Rented Premises]

From,
[Landlord's Full Name]
[Landlord's Address]

Subject: Notice to vacate the tenanted premises

Dear [Tenant's Name],

1. I am the lawful owner/landlord of the premises situated at
   [Full Address of the Rented Premises] ("the Premises"), which were let
   out to you on a monthly tenancy at a rent of Rs. [Amount] per month.

2. You are hereby informed that I require the Premises to be vacated on the
   following ground(s): [e.g. non-payment of rent since (month/year) /
   breach of the tenancy terms / personal bona fide requirement].

3. You are therefore called upon to VACATE and hand over peaceful vacant
   possession of the Premises to me on or before [Date - allow at least 15
   to 30 days from the date of this notice], together with all arrears of
   rent and any dues outstanding up to the date of vacating.

4. Please treat your tenancy as terminated with effect from the said date.
   Should you fail to vacate within the period stated above, I shall be
   constrained to initiate appropriate legal proceedings for your eviction
   before the competent court, entirely at your risk as to cost and
   consequences.

5. This notice is issued to you without prejudice to any of my other rights
   and remedies available under law.

Kindly acknowledge receipt of this notice.

Yours faithfully,

_______________________
[Landlord's Full Name]
(Landlord)`;

const HINDI_AUDIO_ANSWER = `🎙️ *आपका सवाल:* हरियाणा में पुलिस ने मेरी गाड़ी ज़ब्त कर ली है, अब मैं क्या करूँ?

⚖️ *आपके पास ये विकल्प हैं:*

घबराइए मत। पुलिस अक्सर किसी मामले की जाँच, चालान या किसी विवाद में गाड़ी ज़ब्त (सीज़) कर लेती है, लेकिन आपको उसे वापस पाने का पूरा कानूनी हक़ है।

*1. ज़ब्ती की रसीद (Seizure Memo) लीजिए:* पुलिस को गाड़ी ज़ब्त करते समय एक सीज़र मेमो देना होता है, जिसमें गाड़ी की हालत और कारण लिखा होता है। इसकी एक कॉपी ज़रूर लें।

*2. कारण और केस नंबर पता कीजिए:* संबंधित थाने में जाकर पूछें कि गाड़ी किस FIR या केस नंबर के तहत ज़ब्त हुई है। यही जानकारी आगे काम आएगी।

*3. अदालत में "सुपुर्दगी" (Superdari) की अर्ज़ी दीजिए:* भारतीय नागरिक सुरक्षा संहिता (BNSS) की धारा 497 के तहत आप संबंधित मजिस्ट्रेट अदालत में अपनी गाड़ी की अंतरिम कस्टडी के लिए अर्ज़ी लगा सकते हैं। मालिकाना हक़ के कागज़ (RC), बीमा और आईडी साथ ले जाएँ।

*4. अगर सिर्फ़ चालान/जुर्माना है:* तो अक्सर जुर्माना भरकर या दस्तावेज़ (लाइसेंस, RC, इंश्योरेंस, PUC) दिखाकर गाड़ी तुरंत छूट जाती है।

📄 *ज़रूरी कागज़:* गाड़ी की RC, बीमा, ड्राइविंग लाइसेंस, आधार/आईडी, और सीज़र मेमो।

💡 अगर आप चाहें तो मैं आपके लिए अदालत में देने वाली *सुपुर्दगी अर्ज़ी का मसौदा* भी तैयार कर सकता हूँ।

_यह कानूनी जानकारी है, वकील की सलाह का विकल्प नहीं।_`;

function isAudio(msg) {
  if (msg.type === 'ptt' || msg.type === 'audio') return true;
  return false;
}

export function createDemoHandler(client) {
  const state = new Map(); // chatId -> { awaitingDraft: bool }

  const send = async (chatId, content, opts) => {
    try {
      await client.sendMessage(chatId, content, opts);
    } catch (e) {
      log.error('demo sendMessage failed:', e?.message);
    }
  };

  const typing = async (chatId) => {
    try {
      const chat = await client.getChatById(chatId);
      await chat.sendStateTyping();
    } catch {}
  };

  return async function onMessage(msg) {
    const chatId = msg.from;
    if (!chatId || msg.fromMe) return;
    if (chatId.endsWith('@g.us') || chatId === 'status@broadcast') return;

    // Only reply to the one demo number.
    if (!chatId.replace(/\D/g, '').includes(DEMO_NUMBER)) return;

    const body = (msg.body || '').trim();
    const s = state.get(chatId) || { awaitingDraft: false };
    state.set(chatId, s);

    try {
      // Step 1 — always acknowledge instantly so the user sees "processing".
      await send(chatId, PROCESSING);

      // ---- Flow B: audio / voice note -> Hindi answer ----
      if (msg.hasMedia && isAudio(msg)) {
        await wait(1600);
        await typing(chatId);
        await wait(2600);
        await send(chatId, HINDI_AUDIO_ANSWER);
        s.awaitingDraft = false;
        return;
      }

      // ---- Flow A, step 2: user confirmed the draft -> send the PDF ----
      if (s.awaitingDraft && /\b(yes|yeah|yep|sure|ok(ay)?|haan|haa|ha|please|kar\s?do|draft)\b/i.test(body)) {
        await wait(1500);
        await typing(chatId);
        await wait(2800);
        const pdf = makePdf(EVICTION_NOTICE_TEXT);
        const media = new MessageMedia(
          'application/pdf',
          pdf.toString('base64'),
          'Eviction-Notice.pdf'
        );
        await send(chatId, media, { caption: EVICTION_PDF_CAPTION, sendMediaAsDocument: true });
        s.awaitingDraft = false;
        return;
      }

      // ---- Flow A, step 1: any text question -> eviction options + offer ----
      await wait(1600);
      await typing(chatId);
      await wait(3000);
      await send(chatId, EVICTION_OPTIONS);
      s.awaitingDraft = true;
    } catch (err) {
      log.error('demo handler error:', err?.message || err);
    }
  };
}
