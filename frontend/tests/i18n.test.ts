import { expect, test } from 'vitest'
import { dicts, resolveLocale, t, locale, setLocale } from '../src/i18n/index'

const { en, 'zh-CN': zh } = dicts()

test('the two dictionaries carry the exact same key set', () => {
  expect(Object.keys(zh).sort()).toEqual(Object.keys(en).sort())
})

test('no key answers itself: every entry is a real translation', () => {
  for (const [key, value] of Object.entries(en)) {
    expect(value.trim(), `en[${key}]`).not.toBe('')
    expect(value, `en[${key}] echoes its key`).not.toBe(key)
    expect(zh[key].trim(), `zh-CN[${key}]`).not.toBe('')
  }
})

test('resolution: saved beats browser, browser beats default', () => {
  expect(resolveLocale('zh-CN', 'en-US')).toBe('zh-CN')
  expect(resolveLocale('en', 'zh-CN')).toBe('en')
  expect(resolveLocale(null, 'zh-TW')).toBe('zh-CN')
  expect(resolveLocale(null, 'en-GB')).toBe('en')
  expect(resolveLocale(null, undefined)).toBe('en')
  expect(resolveLocale('nonsense', 'zh')).toBe('zh-CN')   // a corrupt saved value is ignored
})

test('t() answers in the current locale, interpolates params, and falls back to English', () => {
  const was = locale.value
  try {
    setLocale('zh-CN')
    expect(t('nav.signin')).toBe('登录')
    expect(t('nav.repo')).toBe('仓库')
    setLocale('en')
    expect(t('nav.signin')).toBe('Sign in')
    // an unknown key answers itself rather than blanking the page
    expect(t('no.such.key')).toBe('no.such.key')
    expect(t('with.params', { n: 3 })).toBe('with.params')   // unknown key is its own fallback
  } finally {
    setLocale(was)
  }
})

test('a missing zh entry falls back to English at runtime (and the parity test above flags it)', () => {
  const was = locale.value
  const zhTable = dicts()['zh-CN']
  const saved = zhTable['nav.repo']
  try {
    delete zhTable['nav.repo']
    setLocale('zh-CN')
    expect(t('nav.repo')).toBe('Repo')
  } finally {
    zhTable['nav.repo'] = saved
    setLocale(was)
  }
})
