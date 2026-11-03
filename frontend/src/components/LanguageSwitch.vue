<script>
import { locale, setLocale, t } from '../i18n/index'
// A one-click language toggle in each navbar: it names the language you would switch TO and
// flips the whole dashboard at once — `t()` reads the same reactive locale the templates render
// with, so no reload, no re-mount. The choice persists in localStorage['treg-locale'].
export default {
  setup() {
    return {
      t,
      locale,
      toggle: () => setLocale(locale.value === 'en' ? 'zh-CN' : 'en'),
    }
  },
}
</script>

<template>
  <button type="button" class="lang-switch" :aria-label="t('lang.switch')"
          :title="t('lang.switch')" @click="toggle">
    {{ locale === 'en' ? '中文' : 'EN' }}
  </button>
</template>

<style scoped>
.lang-switch{background:none;border:0;padding:2px 6px;font-family:var(--sans);font-size:12.5px;
  font-weight:500;color:inherit;cursor:pointer;white-space:nowrap;border-radius:6px;line-height:1.4}
.lang-switch:hover{background:#0000000a}
[data-theme="dark"] .lang-switch:hover{background:#ffffff14}
</style>
