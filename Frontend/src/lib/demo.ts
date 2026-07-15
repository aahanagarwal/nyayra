// Fake demo dataset for Nyayra — powers screen-recordings/demos with no backend.
// Everything here is scripted, illustrative content. Not legal advice.

import type { Chat, Message, Draft, LegalAnswer, CouncilStage, LangCode } from '../lib/types';

// ---------------------------------------------------------------------------
// Council trace builders (one per pipeline path shown in the demo)
// ---------------------------------------------------------------------------

function textCouncil(verifierDetail: string): CouncilStage[] {
  return [
    {
      id: 's1',
      label: 'E2B · mask PII + HyDE',
      role: 'Strips names/addresses, expands the query with a hypothetical answer for retrieval',
      status: 'done',
    },
    {
      id: 's2',
      label: 'Router',
      role: 'Classifies the issue area and picks relevant statutes to hand to the council',
      status: 'done',
      detail: 'Routed to: tenancy · consumer protection · procedure',
    },
    {
      id: 's3',
      label: '26B-A4B council · advocate',
      role: 'Argues the strongest case in your favour',
      status: 'done',
    },
    {
      id: 's4',
      label: "26B-A4B council · devil's advocate",
      role: 'Stress-tests the advocate\'s reasoning for weak points',
      status: 'done',
    },
    {
      id: 's5',
      label: '26B-A4B council · opposition + bench',
      role: 'Models the other side\'s likely response, then a bench view weighs both',
      status: 'done',
    },
    {
      id: 's6',
      label: 'E4B · verifier',
      role: 'Checks every claim in the draft answer against cited sources',
      status: 'done',
      detail: verifierDetail,
    },
    {
      id: 's7',
      label: '31B sandbox draft',
      role: 'Composes the final structured answer and any next-step document',
      status: 'done',
    },
    {
      id: 's8',
      label: 'E2B · unmask',
      role: 'Restores your original names/details into the final answer',
      status: 'done',
    },
  ];
}

function audioCouncil(): CouncilStage[] {
  return [
    {
      id: 's1',
      label: '12B unified · audio-native (no ASR)',
      role: 'Understands your spoken Hindi directly — no separate transcription step, so tone and urgency aren\'t lost',
      status: 'done',
    },
    {
      id: 's2',
      label: 'Router',
      role: 'Classifies the issue area and picks relevant statutes to hand to the council',
      status: 'done',
      detail: 'Routed to: tenancy · procedure',
    },
    {
      id: 's3',
      label: '26B-A4B council · advocate vs opposition',
      role: 'Runs the same multi-agent debate as the text path, seeded from the audio understanding',
      status: 'done',
    },
    {
      id: 's4',
      label: 'E4B · verifier',
      role: 'Checks every claim in the draft answer against cited sources',
      status: 'done',
      detail: '3 claims verified · 0 unsupported',
    },
    {
      id: 's5',
      label: '12B unified · spoken-style reply',
      role: 'Formats the answer for a voice-first reply, keeping sentences short',
      status: 'done',
    },
  ];
}

function documentCouncil(): CouncilStage[] {
  return [
    {
      id: 's1',
      label: 'E2B · mask PII + HyDE',
      role: 'Strips names/addresses, expands the query with a hypothetical answer for retrieval',
      status: 'done',
    },
    {
      id: 's2',
      label: '31B · document parse',
      role: 'Reads the uploaded PDF, extracts clauses, dates and party names',
      status: 'done',
      detail: 'Parsed 14 clauses · flagged 4 as one-sided',
    },
    {
      id: 's3',
      label: 'Router',
      role: 'Classifies the issue area and picks relevant statutes to hand to the council',
      status: 'done',
      detail: 'Routed to: contract law · tenancy',
    },
    {
      id: 's4',
      label: '26B-A4B council · advocate vs opposition',
      role: 'Debates which flagged clauses are actually unenforceable vs merely unfavourable',
      status: 'done',
    },
    {
      id: 's5',
      label: 'E4B · verifier',
      role: 'Checks every claim in the draft answer against cited sources',
      status: 'done',
      detail: '5 claims verified · 0 unsupported',
    },
    {
      id: 's6',
      label: 'E2B · unmask',
      role: 'Restores your original names/details into the final answer',
      status: 'done',
    },
  ];
}

function offlineCouncil(): CouncilStage[] {
  return [
    {
      id: 's1',
      label: 'E-model (E2B) · fully on-device',
      role: 'Runs entirely on your phone in offline mode — nothing leaves the device, no network call is made',
      status: 'done',
    },
    {
      id: 's2',
      label: 'E-model (E2B) · local draft',
      role: 'Composes a structured answer from the on-device statute cache, without the full cloud council',
      status: 'done',
      detail: 'Offline mode: answer will be re-verified by the full council next time you\'re online',
    },
  ];
}

// ---------------------------------------------------------------------------
// Scripted LegalAnswers
// ---------------------------------------------------------------------------

const evictionAnswerEn: LegalAnswer = {
  rights: [
    'Most state Rent Control Acts require a landlord to give written notice of a defined minimum period (commonly 15–30 days) before seeking eviction, except in narrow grounds like non-payment.',
    'A landlord cannot forcibly remove you, cut power/water, or change locks without a court order — that would itself be an offence.',
    'You have the right to contest the eviction before the Rent Controller or Civil Court if the grounds cited are invalid or the notice period was not honoured.',
  ],
  options: [
    'Reply in writing within the notice period disputing the grounds, and keep a copy — this preserves your position if it goes to court.',
    'If the notice period given is shorter than your state\'s Rent Control Act requires, you can point this out and treat the notice as defective.',
    'If eviction proceeds to court, you can seek an interim stay while the matter is heard, buying time to arrange alternate housing.',
  ],
  nextStep: [
    'Send a reply to the landlord by registered post / speed post within 7 days, referencing the notice date and stating you dispute the grounds.',
    'Keep the rent agreement, rent receipts, and this notice together as your evidence file.',
  ],
  needsLawyer: false,
};

const evictionAnswerHi: LegalAnswer = {
  rights: [
    'ज़्यादातर राज्यों के किराया नियंत्रण अधिनियम के तहत मकान मालिक को बेदखली से पहले एक तय न्यूनतम नोटिस अवधि (आमतौर पर 15–30 दिन) देनी होती है, सिवाय किराया न चुकाने जैसे कुछ खास मामलों के।',
    'मकान मालिक अदालत के आदेश के बिना ज़बरदस्ती आपको नहीं निकाल सकता, न ही बिजली-पानी काट सकता है या ताला बदल सकता है — ऐसा करना खुद एक अपराध है।',
    'यदि नोटिस के आधार गलत हैं या तय अवधि नहीं दी गई, तो आपको रेंट कंट्रोलर या सिविल कोर्ट में इसे चुनौती देने का अधिकार है।',
  ],
  options: [
    'नोटिस अवधि के भीतर लिखित जवाब भेजें और उसकी एक कॉपी अपने पास रखें — इससे अदालत में आपकी स्थिति मज़बूत रहेगी।',
    'अगर दी गई नोटिस अवधि आपके राज्य के किराया नियंत्रण अधिनियम से कम है, तो आप नोटिस को अमान्य बता सकते हैं।',
    'मामला अदालत में जाने पर, आप वैकल्पिक आवास का इंतज़ाम करने के लिए अंतरिम रोक (interim stay) की मांग कर सकते हैं।',
  ],
  nextStep: [
    '7 दिनों के भीतर रजिस्टर्ड पोस्ट / स्पीड पोस्ट से जवाब भेजें, जिसमें नोटिस की तारीख का हवाला दें और आधार को चुनौती दें।',
    'किराया अनुबंध, किराया रसीदें और यह नोटिस — सभी को सबूत के तौर पर सुरक्षित रखें।',
  ],
  needsLawyer: false,
};

const evictionReplyDraftAnswerEn: LegalAnswer = {
  rights: [
    'A written reply within the notice period is treated as evidence that you contested the eviction in time, which matters if the case reaches the Rent Controller.',
  ],
  options: [
    'Send the drafted reply below as-is, or edit the tenancy dates and grounds before sending by registered post.',
    'Keep a photocopy and the post receipt — you may need to produce both if the landlord denies receiving it.',
  ],
  nextStep: [
    'Draft ready: "Reply to eviction notice" — open it from Drafts, fill in the blanks (your name, address, tenancy start date), and send by registered post within 7 days.',
  ],
  needsLawyer: false,
};

const rentalAgreementAnswerEn: LegalAnswer = {
  rights: [
    'Under general contract law, a clause can be one-sided but still enforceable — being unfair doesn\'t automatically make it void. However, terms deemed unconscionable can be struck down by a court.',
    'A clause letting the landlord enter "at any time without notice" typically conflicts with your right to quiet enjoyment of the premises and is rarely enforced as written.',
    'A clause forfeiting your full security deposit for "any damage, however minor" is usually read down by courts to mean reasonable, itemised deductions only.',
  ],
  options: [
    'Negotiate the flagged clauses before signing — landlords in most cities will accept reasonable notice-for-entry and itemised-deduction language.',
    'If already signed, you can still rely on the Model Tenancy Act / state Rent Control Act provisions as a floor of protection that overrides one-sided private clauses.',
    'Keep dated photos of the property\'s condition at move-in to counter any inflated damage claims later.',
  ],
  nextStep: [
    'Review the 4 flagged clauses (entry-without-notice, full deposit forfeiture, unilateral rent hike, one-sided termination) and request a signed addendum before moving in.',
  ],
  needsLawyer: false,
};

const insuranceAnswerEn: LegalAnswer = {
  rights: [
    'Insurers must give a written reason for rejecting a claim under IRDAI regulations — a vague or missing reason is itself grounds to challenge the rejection.',
    'You have the right to escalate a rejected claim first to the insurer\'s internal Grievance Redressal Officer, then to the Insurance Ombudsman, free of cost.',
    'If the ombudsman route fails or the amount is contested, you can file under the Consumer Protection Act, 2019 before the District Consumer Forum.',
  ],
  options: [
    'Request the rejection letter in writing citing the specific policy clause relied upon — insurers sometimes reverse decisions once challenged formally.',
    'File with the Insurance Ombudsman (free, informal, decided within months) if the claim value is within their jurisdiction (currently up to ₹50 lakh).',
    'File a consumer complaint if you also want compensation for mental agony/deficiency in service, not just the claim amount.',
  ],
  nextStep: [
    'Draft ready: "Complaint to Insurance Ombudsman" — attach the policy copy, claim form, and rejection letter, and file within the applicable limitation period.',
  ],
  needsLawyer: true,
  lawyerNote: 'Ombudsman and consumer forum filings genuinely benefit from a lawyer\'s review, especially to frame the deficiency-of-service argument and compute compensation correctly — consider at least a paid one-time consultation before filing.',
};

const policeAnswerEn: LegalAnswer = {
  rights: [
    'Under Section 41A CrPC, police must first issue a notice to appear rather than arrest you directly for offences punishable with up to 7 years, if you cooperate.',
    'You have the right to know the grounds of the complaint against you and to have a copy of the notice.',
    'You are not obliged to make any self-incriminating statement — Article 20(3) of the Constitution protects you against this.',
  ],
  options: [
    'Appear as directed in the notice, ideally with a lawyer or at least inform a family member of the time and place before you go.',
    'If you cannot appear on the given date, you can request a reasonable adjournment in writing, citing a genuine reason.',
    'If you believe the complaint is false, you can also file a counter-representation with the same police station outlining your version.',
  ],
  nextStep: [
    'Reply in writing acknowledging the notice, confirming your appearance date, and requesting a copy of the complaint if not already provided.',
  ],
  needsLawyer: false,
};

const genericAnswerEn: LegalAnswer = {
  rights: [
    'You generally have the right to written communication before any adverse action is taken against you, along with a fair chance to respond.',
    'Most consumer, tenancy, and procedural disputes in India have a defined limitation period — acting early preserves your options.',
  ],
  options: [
    'Gather all related documents (notices, agreements, receipts) into one file before deciding your next move.',
    'Send a written reply or representation to the other party, even if only to formally record your position.',
  ],
  nextStep: [
    'Tell me a bit more — the type of notice or dispute — and I can give a more specific rights/options/next-step breakdown.',
  ],
  needsLawyer: false,
};

// ---------------------------------------------------------------------------
// Public: answerFor / voiceReply / docReply
// ---------------------------------------------------------------------------

export function answerFor(text: string, lang: LangCode): { answer: LegalAnswer; council: CouncilStage[] } {
  const q = text.toLowerCase();

  if (q.includes('evict') || q.includes('landlord')) {
    return {
      answer: lang === 'hi' ? evictionAnswerHi : evictionAnswerEn,
      council: textCouncil('3 claims verified · 0 unsupported'),
    };
  }

  if (q.includes('rental') || q.includes('agreement') || q.includes('contract')) {
    return {
      answer: rentalAgreementAnswerEn,
      council: textCouncil('4 claims verified · 0 unsupported'),
    };
  }

  if (q.includes('insurance') || q.includes('claim')) {
    return {
      answer: insuranceAnswerEn,
      council: textCouncil('4 claims verified · 1 unsupported claim rejected'),
    };
  }

  if (q.includes('police') || q.includes('fir') || q.includes('complaint')) {
    return {
      answer: policeAnswerEn,
      council: textCouncil('3 claims verified · 0 unsupported'),
    };
  }

  return {
    answer: genericAnswerEn,
    council: textCouncil('2 claims verified · 0 unsupported'),
  };
}

export const DEMO_VOICE_TRANSCRIPT =
  'मेरा मकान मालिक मुझे निकालना चाहता है, मेरे पास सिर्फ 15 दिन हैं।';

export function voiceReply(): { answer: LegalAnswer; council: CouncilStage[] } {
  return {
    answer: evictionAnswerHi,
    council: audioCouncil(),
  };
}

export const DEMO_DOC_SUMMARY =
  'This looks like a rooming/rental agreement dated 3 months ago; several clauses (entry-without-notice, full deposit forfeiture, unilateral rent hike) appear one-sided against the tenant.';

export function docReply(): { answer: LegalAnswer; council: CouncilStage[] } {
  return {
    answer: rentalAgreementAnswerEn,
    council: documentCouncil(),
  };
}

// ---------------------------------------------------------------------------
// DEMO_CHATS
// ---------------------------------------------------------------------------

function msg(partial: Omit<Message, 'id' | 'createdAt'> & { id: string; createdAt: number }): Message {
  return partial;
}

const chatEviction: Chat = {
  id: 'chat-eviction',
  title: 'Eviction notice — my rights',
  updatedAt: 1752500000000,
  messages: [
    msg({
      id: 'chat-eviction-m1',
      role: 'user',
      text: 'My landlord handed me an eviction notice yesterday saying I have to vacate in 15 days. Is that even legal? What are my rights here?',
      lang: 'en',
      createdAt: 1752499000000,
    }),
    msg({
      id: 'chat-eviction-m2',
      role: 'assistant',
      answer: evictionAnswerEn,
      council: textCouncil('3 claims verified · 0 unsupported'),
      lang: 'en',
      createdAt: 1752499060000,
    }),
    msg({
      id: 'chat-eviction-m3',
      role: 'user',
      text: 'Okay that helps. Can you draft a reply for me to send back to him?',
      lang: 'en',
      createdAt: 1752499500000,
    }),
    msg({
      id: 'chat-eviction-m4',
      role: 'assistant',
      answer: evictionReplyDraftAnswerEn,
      council: textCouncil('2 claims verified · 0 unsupported'),
      lang: 'en',
      createdAt: 1752499560000,
    }),
  ],
};

const chatEvictionHi: Chat = {
  id: 'chat-eviction-hi',
  title: 'मकान मालिक निकाल रहा है',
  updatedAt: 1752300000000,
  messages: [
    msg({
      id: 'chat-eviction-hi-m1',
      role: 'user',
      text: 'मेरा मकान मालिक मुझे निकालना चाहता है, मेरे पास सिर्फ 15 दिन हैं। मैं क्या करूं?',
      lang: 'hi',
      attachments: [{ id: 'att-voice-1', name: 'voice-note.m4a', kind: 'audio', sizeLabel: '0:42' }],
      createdAt: 1752299000000,
    }),
    msg({
      id: 'chat-eviction-hi-m2',
      role: 'assistant',
      answer: evictionAnswerHi,
      council: audioCouncil(),
      lang: 'hi',
      createdAt: 1752299060000,
    }),
  ],
};

const chatRentalDoc: Chat = {
  id: 'chat-rental-doc',
  title: 'Is my rental agreement one-sided?',
  updatedAt: 1752100000000,
  messages: [
    msg({
      id: 'chat-rental-doc-m1',
      role: 'user',
      text: 'Can you check this rental agreement before I sign it? Something feels off.',
      lang: 'en',
      attachments: [{ id: 'att-pdf-1', name: 'rental-agreement.pdf', kind: 'pdf', sizeLabel: '480 KB' }],
      createdAt: 1752099000000,
    }),
    msg({
      id: 'chat-rental-doc-m2',
      role: 'assistant',
      text: DEMO_DOC_SUMMARY,
      answer: rentalAgreementAnswerEn,
      council: documentCouncil(),
      lang: 'en',
      createdAt: 1752099060000,
    }),
  ],
};

const chatInsurance: Chat = {
  id: 'chat-insurance',
  title: 'Insurance claim rejected',
  updatedAt: 1751900000000,
  messages: [
    msg({
      id: 'chat-insurance-m1',
      role: 'user',
      text: 'My health insurance claim for a hospitalisation got rejected saying "pre-existing condition not disclosed". I disclosed everything when I bought the policy. What can I do?',
      lang: 'en',
      createdAt: 1751899000000,
    }),
    msg({
      id: 'chat-insurance-m2',
      role: 'assistant',
      answer: insuranceAnswerEn,
      council: textCouncil('4 claims verified · 1 unsupported claim rejected'),
      lang: 'en',
      createdAt: 1751899060000,
    }),
  ],
};

const chatPolice: Chat = {
  id: 'chat-police',
  title: 'Police complaint — how do I respond?',
  updatedAt: 1751700000000,
  messages: [
    msg({
      id: 'chat-police-m1',
      role: 'user',
      text: 'I just got a police notice asking me to appear at the station regarding a complaint filed against me. I was offline when I got this, using local mode. What should I do?',
      lang: 'en',
      createdAt: 1751699000000,
    }),
    msg({
      id: 'chat-police-m2',
      role: 'assistant',
      answer: policeAnswerEn,
      council: offlineCouncil(),
      lang: 'en',
      createdAt: 1751699060000,
    }),
  ],
};

export const DEMO_CHATS: Chat[] = [
  chatEviction,
  chatEvictionHi,
  chatRentalDoc,
  chatInsurance,
  chatPolice,
];

// ---------------------------------------------------------------------------
// DEMO_DRAFTS
// ---------------------------------------------------------------------------

export const DEMO_DRAFTS: Draft[] = [
  {
    id: 'draft-eviction-reply',
    title: 'Reply to eviction notice',
    kind: 'Reply letter',
    updatedAt: 1752499600000,
    preview:
      'To, [Landlord Name], Sub: Reply to your notice dated [date] regarding vacation of premises at [address]. I write to state that the notice period provided...',
  },
  {
    id: 'draft-insurance-ombudsman',
    title: 'Complaint to Insurance Ombudsman',
    kind: 'Complaint',
    updatedAt: 1751899600000,
    preview:
      'To, The Insurance Ombudsman, [City]. Sub: Complaint against [Insurer Name] regarding wrongful rejection of claim no. [claim number] dated [date]...',
  },
  {
    id: 'draft-rti-fir',
    title: 'RTI application — FIR copy',
    kind: 'Application',
    updatedAt: 1751699600000,
    preview:
      'To, The Public Information Officer, [Police Station/District]. Sub: Request for certified copy of FIR no. [FIR number] under the Right to Information Act, 2005...',
  },
  {
    id: 'draft-legal-notice-landlord',
    title: 'Legal notice to landlord',
    kind: 'Legal notice',
    updatedAt: 1751500000000,
    preview:
      'Under instructions from and on behalf of my client, [Tenant Name], residing at [address], I hereby serve upon you the following legal notice regarding...',
  },
];

// ---------------------------------------------------------------------------
// DEMO_CONFIG — filmable default deliberation duration
// ---------------------------------------------------------------------------

export interface DemoConfig {
  thinkingMs: number;
}

// Default "deliberation" animation duration per answer. Filmable default; override live with ?think=<seconds> in the URL.
export const DEMO_CONFIG: DemoConfig = { thinkingMs: 6000 };

// ---------------------------------------------------------------------------
// DEMO_SCRIPT — ordered live-demo run sheet
// ---------------------------------------------------------------------------

export interface ScriptStep {
  order: number;
  scenario: string;
  action: 'type' | 'mic' | 'attach';
  trigger: string;
  flow: 'text' | 'voice' | 'document';
  lang: LangCode;
  thinkingMs: number;
  narration: string;
  answer: LegalAnswer;
  council: CouncilStage[];
  attachmentName?: string;
}

const policeAnswerHi: LegalAnswer = {
  rights: [
    'धारा 41A CrPC के तहत, यदि आप सहयोग करते हैं तो 7 साल तक की सज़ा वाले अपराधों में पुलिस सीधे गिरफ्तार करने के बजाय पहले पेश होने का नोटिस देगी।',
    'आपको शिकायत के आधार जानने और नोटिस की एक कॉपी पाने का अधिकार है।',
    'आप किसी भी ऐसे बयान के लिए बाध्य नहीं हैं जो खुद के खिलाफ हो — संविधान का अनुच्छेद 20(3) इसकी रक्षा करता है।',
  ],
  options: [
    'नोटिस में बताई गई तारीख पर पेश हों, संभव हो तो वकील के साथ, या कम से कम परिवार के किसी सदस्य को समय और जगह बता दें।',
    'यदि तय तारीख पर पेश नहीं हो सकते, तो वाजिब कारण बताते हुए लिखित रूप से स्थगन का अनुरोध करें।',
    'यदि शिकायत झूठी लगती है, तो उसी थाने में अपना पक्ष रखते हुए प्रति-प्रतिवेदन भी दाखिल कर सकते हैं।',
  ],
  nextStep: [
    'नोटिस मिलने की पुष्टि करते हुए, पेश होने की तारीख बताते हुए और शिकायत की कॉपी मांगते हुए लिखित जवाब भेजें।',
  ],
  needsLawyer: false,
};

const step1: ScriptStep = {
  order: 1,
  scenario: 'Eviction journey (English text)',
  action: 'type',
  trigger: 'landlord served me an eviction notice',
  flow: 'text',
  lang: 'en',
  thinkingMs: 8000,
  narration: 'Watch the full council deliberate — masking, routing, debate, verification, drafting, unmasking.',
  answer: evictionAnswerEn,
  council: textCouncil('3 claims verified · 0 unsupported'),
};

const step2: ScriptStep = {
  order: 2,
  scenario: 'Eviction journey — follow-up draft',
  action: 'type',
  trigger: 'draft a reply to the landlord',
  flow: 'text',
  lang: 'en',
  thinkingMs: 5000,
  narration: 'Now it drafts the actual reply letter and saves it straight to Drafts.',
  answer: evictionReplyDraftAnswerEn,
  council: [
    {
      id: 's1',
      label: 'Router',
      role: 'Recognises this as a follow-up on the same eviction thread',
      status: 'done',
      detail: 'Routed to: tenancy · drafting',
    },
    {
      id: 's2',
      label: '31B sandbox draft',
      role: 'Composes the reply letter and files it under Drafts',
      status: 'done',
      detail: 'Saved as "Reply to eviction notice"',
    },
    {
      id: 's3',
      label: 'E4B · verifier',
      role: 'Checks every claim in the draft answer against cited sources',
      status: 'done',
      detail: '2 claims verified · 0 unsupported',
    },
  ],
};

const step3: ScriptStep = {
  order: 3,
  scenario: 'Eviction journey (Hindi voice)',
  action: 'mic',
  trigger: 'Click the mic — plays a Hindi voice note',
  flow: 'voice',
  lang: 'hi',
  thinkingMs: 6000,
  narration: 'Same question, spoken in Hindi — the 12B model understands the audio directly, no transcription step.',
  answer: evictionAnswerHi,
  council: audioCouncil(),
  attachmentName: 'voice-note.m4a',
};

const step4: ScriptStep = {
  order: 4,
  scenario: 'Rental contract review (document upload)',
  action: 'attach',
  trigger: 'Click the paperclip — attaches a rental agreement PDF',
  flow: 'document',
  lang: 'en',
  thinkingMs: 7000,
  narration: 'Upload a contract and the council parses clauses, flagging the ones that are one-sided.',
  answer: rentalAgreementAnswerEn,
  council: documentCouncil(),
  attachmentName: 'rental-agreement.pdf',
};

const step5: ScriptStep = {
  order: 5,
  scenario: 'Insurance claim rejected',
  action: 'type',
  trigger: 'my insurance claim was rejected',
  flow: 'text',
  lang: 'en',
  thinkingMs: 6000,
  narration: 'This one flags that a lawyer is genuinely worth it — the app knows when to say so.',
  answer: insuranceAnswerEn,
  council: textCouncil('4 claims verified · 1 unsupported claim rejected'),
};

const step6: ScriptStep = {
  order: 6,
  scenario: 'Police notice under Section 41A CrPC (offline mode)',
  action: 'type',
  trigger: 'i got a police notice under 41a',
  flow: 'text',
  lang: 'en',
  thinkingMs: 6000,
  narration: 'Flip to offline mode — the whole answer runs on-device, nothing leaves the phone.',
  answer: policeAnswerEn,
  council: offlineCouncil(),
};

const step7: ScriptStep = {
  order: 7,
  scenario: 'Police notice under Section 41A CrPC (Hindi, offline)',
  action: 'type',
  trigger: 'mujhe police notice mila hai 41a ke under',
  flow: 'text',
  lang: 'hi',
  thinkingMs: 6000,
  narration: 'Same offline path, this time answered in Hindi.',
  answer: policeAnswerHi,
  council: offlineCouncil(),
};

export const DEMO_SCRIPT: ScriptStep[] = [step1, step2, step3, step4, step5, step6, step7];

export function scriptedFor(
  text: string,
  lang: LangCode
): { answer: LegalAnswer; council: CouncilStage[]; thinkingMs: number } | null {
  const normalized = text.trim().toLowerCase();
  if (!normalized) return null;

  for (const step of DEMO_SCRIPT) {
    if (step.action !== 'type') continue;
    if (step.lang !== lang) continue;
    const trigger = step.trigger.toLowerCase();
    if (normalized === trigger || normalized.startsWith(trigger)) {
      return { answer: step.answer, council: step.council, thinkingMs: step.thinkingMs };
    }
  }

  return null;
}
