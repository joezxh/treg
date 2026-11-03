// Zero-dependency i18n for the dashboard. Two flat dictionaries (en.ts, zh-CN.ts), one reactive
// `locale`, and `t()` — plain enough that a template can call it directly and re-render on
// switch: reading `locale.value` inside the render registers the dependency. Registered as a
// global property in main.ts, so the 76 templates reach it without an import each.
//
// Persistence mirrors the theme's: `localStorage['treg-locale']`, set in index.html's inline
// script before Vue boots so the first paint is already in the right language.
import { ref } from 'vue'
import { en } from './en'
import { zh } from './zh-CN'

export type Locale = 'en' | 'zh-CN'

const DICTS: Record<Locale, Record<string, string>> = { en, 'zh-CN': zh }

/** The saved value wins; otherwise the browser language; otherwise English. Pure so tests can pin it. */
export function resolveLocale(saved: string | null, browser: string | undefined | null): Locale {
  if (saved === 'en' || saved === 'zh-CN') return saved
  return (browser ?? '').toLowerCase().startsWith('zh') ? 'zh-CN' : 'en'
}

function initial(): Locale {
  if (typeof localStorage === 'undefined') return 'en'   // vitest runs in plain node
  return resolveLocale(localStorage.getItem('treg-locale'),
                       typeof navigator === 'undefined' ? undefined : navigator.language)
}

export const locale = ref<Locale>(initial())

export function setLocale(next: Locale): void {
  locale.value = next
  if (typeof localStorage !== 'undefined') localStorage.setItem('treg-locale', next)
  if (typeof document !== 'undefined') document.documentElement.lang = next
}

/** Translate `key` in the current locale, interpolating `{name}` params; an unknown key answers
 *  itself (English first), so a missing entry is visible in the page instead of blank. */
export function t(key: string, params?: Record<string, string | number>): string {
  let s = DICTS[locale.value][key] ?? en[key] ?? key
  if (params) {
    for (const [name, value] of Object.entries(params)) {
      s = s.split(`{${name}}`).join(String(value))
    }
  }
  return s
}

export function dicts(): Record<Locale, Record<string, string>> {
  return DICTS
}
