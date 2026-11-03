// The ONE list of treg's social accounts. Every surface that shows social links — the three
// navigations, the marketing pages (src/treg/web/social.json, kept in the same shape) — reads
// from here, so adding or renaming an account is a one-line change in this file.
//
// `kind: 'link'` opens the URL; `kind: 'qrcode'` (WeChat has no web profile) opens the QR dialog.
// The China-platform and Facebook URLs below are PLACEHOLDERS: replace each with the real
// profile URL the day the account is opened. Nothing else needs to change.
export type SocialLink = { platform: string; url: string; kind: 'link' | 'qrcode' }

export const SOCIAL_LINKS: SocialLink[] = [
  { platform: 'github', url: 'https://github.com/superdesigndev/treg', kind: 'link' },
  { platform: 'discord', url: 'https://discord.gg/6mQYYfFMAn', kind: 'link' },
  { platform: 'x', url: 'https://x.com/treg_ai', kind: 'link' },
  { platform: 'facebook', url: 'https://www.facebook.com/treg', kind: 'link' },          // placeholder
  { platform: 'weibo', url: 'https://weibo.com/treg', kind: 'link' },                    // placeholder
  { platform: 'xiaohongshu', url: 'https://www.xiaohongshu.com/user/treg', kind: 'link' }, // placeholder
  { platform: 'douyin', url: 'https://www.douyin.com/@treg', kind: 'link' },             // placeholder
  { platform: 'wechat', url: '', kind: 'qrcode' },
]
