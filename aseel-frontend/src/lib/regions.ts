import {
  Briefcase, Coffee, Gift, Handshake, House, Moon, PartyPopper, Shirt, UtensilsCrossed,
  type LucideIcon,
} from 'lucide-react';
import { CITIES, PROVINCES } from '../data/saudiMap';
import type { Lang, RegionId, RegionOrGeneral } from './types';

export interface RegionMeta { id: RegionId; en: string; ar: string }

/** Canonical ASEEL regions (see understanding.py) — "General" is handled separately. */
export const REGIONS: RegionMeta[] = [
  { id: 'central', en: 'Central', ar: 'الوسط' },
  { id: 'west', en: 'West', ar: 'الغرب' },
  { id: 'east', en: 'East', ar: 'الشرق' },
  { id: 'south', en: 'South', ar: 'الجنوب' },
  { id: 'north', en: 'North', ar: 'الشمال' },
];

export const REGION_IDS: RegionId[] = REGIONS.map((r) => r.id);

export function regionName(id: RegionOrGeneral, lang: Lang): string {
  if (id === 'general') return lang === 'ar' ? 'عام' : 'General';
  const r = REGIONS.find((x) => x.id === id)!;
  return r[lang];
}

export function regionEnglish(id: RegionOrGeneral): string {
  return id === 'general' ? 'General' : REGIONS.find((x) => x.id === id)!.en;
}

/** Map any backend region label ("South", "General", …) to an id. */
export function normalizeRegion(label: string | null | undefined): RegionOrGeneral {
  const s = (label ?? '').trim().toLowerCase();
  const hit = REGION_IDS.find((id) => s === id || s.startsWith(id));
  return hit ?? 'general';
}

export const provincesOf = (id: RegionId) => PROVINCES.filter((p) => p.region === id);

const PROVINCE_EN: Record<string, string> = {
  'ash-sharqiyah': 'Eastern Province', 'al-hudud-ash-shamaliyah': 'Northern Borders', 'al-jawf': 'Al-Jawf',
  najran: 'Najran', asir: 'Asir', jizan: 'Jazan', tabuk: 'Tabuk', 'al-madinah': 'Madinah', makkah: 'Makkah',
  'ar-riyad': 'Riyadh', 'al-quassim': 'Al-Qassim', hail: 'Hail', 'al-bahah': 'Al Bahah',
};

/** Friendly province label (dataset names are romanised differently). */
export const provinceLabel = (p: { id: string; name: string; nameAr: string }, lang: Lang) =>
  lang === 'ar' ? p.nameAr.replace('منطقة ', '').replace('المنطقة ', '') : PROVINCE_EN[p.id] ?? p.name;
export const citiesOf = (id: RegionId) => CITIES.filter((c) => c.region === id);

/** "in the South region of Saudi Arabia" — phrased so the backend's region resolver can pick it up. */
export function whereClause(region: RegionOrGeneral): string {
  return region === 'general' ? 'in Saudi Arabia' : `in the ${regionEnglish(region)} region of Saudi Arabia`;
}

export interface Topic {
  id: string;
  icon: LucideIcon;
  en: string;
  ar: string;
  hintEn: string;
  hintAr: string;
  query: (region: RegionOrGeneral) => string;
}

/**
 * Topics are only *questions* sent to the API. No cultural claims are written
 * in the frontend: every answer shown to the user comes from the knowledge base.
 */
export const TOPICS: Topic[] = [
  { id: 'greetings', icon: Handshake, en: 'Greetings', ar: 'التحية', hintEn: 'Meeting and addressing people', hintAr: 'اللقاء ومخاطبة الآخرين',
    query: (r) => `How do people greet each other, and how should I address people, ${whereClause(r)}?` },
  { id: 'hospitality', icon: House, en: 'Home visits', ar: 'زيارة البيوت', hintEn: 'Visiting and hosting at home', hintAr: 'الزيارة والاستضافة في المنزل',
    query: (r) => `What are the customs for visiting or hosting a guest at home ${whereClause(r)}?` },
  { id: 'coffee', icon: Coffee, en: 'Coffee and dates', ar: 'القهوة والتمر', hintEn: 'Serving and accepting', hintAr: 'التقديم والقبول',
    query: (r) => `What are the customs around serving and accepting Arabic coffee and dates ${whereClause(r)}?` },
  { id: 'dining', icon: UtensilsCrossed, en: 'Meals', ar: 'الولائم', hintEn: 'Dining etiquette', hintAr: 'آداب الطعام',
    query: (r) => `What is the dining and meal etiquette ${whereClause(r)}?` },
  { id: 'weddings', icon: PartyPopper, en: 'Weddings', ar: 'الأعراس', hintEn: 'Guest customs', hintAr: 'عادات الضيوف',
    query: (r) => `What are wedding customs and guest etiquette ${whereClause(r)}?` },
  { id: 'dress', icon: Shirt, en: 'Dress', ar: 'اللباس', hintEn: 'What to wear and when', hintAr: 'ماذا ترتدي ومتى',
    query: (r) => `What are the expectations around traditional and everyday dress ${whereClause(r)}?` },
  { id: 'gifts', icon: Gift, en: 'Gifts', ar: 'الهدايا', hintEn: 'Giving and receiving', hintAr: 'الإهداء والاستقبال',
    query: (r) => `What are the customs around giving and receiving gifts ${whereClause(r)}?` },
  { id: 'business', icon: Briefcase, en: 'Business meetings', ar: 'اجتماعات العمل', hintEn: 'Professional etiquette', hintAr: 'آداب المهنة',
    query: (r) => `What should I know about business meeting etiquette ${whereClause(r)}?` },
  { id: 'ramadan', icon: Moon, en: 'Ramadan and Eid', ar: 'رمضان والعيد', hintEn: 'Gatherings and observance', hintAr: 'الاجتماعات والمناسبات',
    query: (r) => `What are the customs for Ramadan and Eid gatherings ${whereClause(r)}?` },
];

export const topicName = (t: Topic, lang: Lang) => t[lang];
export const topicHint = (t: Topic, lang: Lang) => (lang === 'ar' ? t.hintAr : t.hintEn);

/* ---------- Plan-a-visit options ---------- */

export interface Option { id: string; en: string; ar: string; phrase: string }

export const OCCASIONS: Option[] = [
  { id: 'home', en: 'Visiting a home', ar: 'زيارة منزل', phrase: 'visiting a family home' },
  { id: 'meal', en: 'A meal invitation', ar: 'دعوة على وليمة', phrase: 'a meal or dinner invitation' },
  { id: 'wedding', en: 'A wedding', ar: 'حفل زفاف', phrase: 'a wedding' },
  { id: 'business', en: 'A business meeting', ar: 'اجتماع عمل', phrase: 'a business meeting' },
  { id: 'ramadan', en: 'Ramadan or Eid', ar: 'رمضان أو العيد', phrase: 'a Ramadan or Eid gathering' },
  { id: 'first', en: 'Meeting someone new', ar: 'لقاء شخص جديد', phrase: 'meeting someone for the first time' },
];

export const ROLES: Option[] = [
  { id: 'guest', en: 'Guest', ar: 'ضيف', phrase: 'a guest' },
  { id: 'host', en: 'Host', ar: 'مضيف', phrase: 'a host' },
  { id: 'visitor', en: 'New to Saudi Arabia', ar: 'زائر جديد', phrase: 'a visitor who is new to Saudi Arabia' },
  { id: 'colleague', en: 'Colleague', ar: 'زميل عمل', phrase: 'a colleague or business partner' },
];

export const FOCUS: Option[] = [
  { id: 'greetings', en: 'Greetings', ar: 'التحية', phrase: 'greetings' },
  { id: 'dress', en: 'Dress', ar: 'اللباس', phrase: 'what to wear' },
  { id: 'gifts', en: 'Gifts', ar: 'الهدايا', phrase: 'gifts' },
  { id: 'food', en: 'Food and drink', ar: 'الطعام والشراب', phrase: 'food and drink' },
  { id: 'conversation', en: 'Conversation', ar: 'الحديث', phrase: 'conversation and behaviour' },
  { id: 'timing', en: 'Timing', ar: 'المواعيد', phrase: 'timing and punctuality' },
];

export const optionName = (o: Option, lang: Lang) => o[lang];

/** Starter questions shown on Home and in the empty chat. */
export const SAMPLE_QUESTIONS = [
  'What should I bring when invited to a home in Riyadh?',
  'How is Arabic coffee served and how should I accept it?',
  'What are wedding customs in the South region?',
  'How do people greet each other in the West region?',
  'What is the dining etiquette in the East region?',
  'How should I dress for a business meeting in Jeddah?',
];
