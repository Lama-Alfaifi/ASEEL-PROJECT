import type { RegionId } from '../data/saudiMap';

export type { RegionId };
export type RegionOrGeneral = RegionId | 'general';
export type Lang = 'en' | 'ar';
export type ThemePref = 'light' | 'dark' | 'system';

/** One knowledge-base entry returned by POST /chat in `sources`. */
export interface Source {
  region: string;
  category: string;
  domain: string;
  question: string;
  answer: string;
  relevance: number | null;
  distance: number | null;
}

export type AnswerStatus = 'grounded' | 'fallback';

/** Normalised POST /chat response. */
export interface ChatResult {
  answer: string;
  status: AnswerStatus;
  confidence: number;
  sources: Source[];
}

export interface ApiFailure {
  kind: 'network' | 'timeout' | 'http' | 'aborted' | 'parse';
  message: string;
  status?: number;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: number;
  /** user: region chosen in the composer */
  regionHint?: RegionOrGeneral | null;
  /** user: exact text sent to the API (question + region hint) */
  sent?: string;
  /** assistant: verified result metadata */
  result?: Omit<ChatResult, 'answer'>;
  /** assistant: the question this answered */
  query?: string;
  /** assistant: request failed */
  error?: ApiFailure;
}

export interface Thread {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  messages: Message[];
}

export type DiscoveryKind = 'topic' | 'city' | 'brief';

export interface Discovery {
  key: string;
  kind: DiscoveryKind;
  title: string;
  query: string;
  region: RegionOrGeneral;
  result: ChatResult;
  at: number;
  meta?: Record<string, string>;
}

export interface SavedItem {
  id: string;
  refKey: string;
  kind: 'answer' | 'source';
  title: string;
  body: string;
  region: RegionOrGeneral | null;
  category?: string;
  query?: string;
  confidence?: number;
  sources?: Source[];
  savedAt: number;
  note: string;
  tags: string[];
}

export interface Settings {
  lang: Lang;
  theme: ThemePref;
  apiBase: string;
}

export interface IndexedSource {
  key: string;
  source: Source;
  region: RegionOrGeneral;
  count: number;
  lastSeen: number;
  queries: string[];
}
