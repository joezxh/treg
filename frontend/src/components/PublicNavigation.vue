<script>
import { useDashboard } from '../state/context'
import BrandMark from './BrandMark.vue'
import LanguageSwitch from './LanguageSwitch.vue'
import WeChatQrDialog from './WeChatQrDialog.vue'
import { SOCIAL_LINKS } from '../state/social'
import { t } from '../i18n/index'
export default {
  components: { BrandMark, LanguageSwitch, WeChatQrDialog },
  setup() {
    const ctx = useDashboard()
    ctx.t = t
    return ctx
  },
  data: () => ({ wechatQr: false, socials: SOCIAL_LINKS }),
  methods: {
    socialLabel(platform) { return t('social.' + platform) },
    socialGo(social) {
      if (social.kind === 'qrcode') this.wechatQr = true
      else window.open(social.url, '_blank', 'noopener')
    },
  },
}
</script>

<template>
<div class="pubnav" >
      <a class="brand" href="/"><BrandMark/>treg</a>
      <nav class="pubnav-links">
        <a href="/catalog" aria-current="page">{{ t('nav.catalog') }}</a>
        <a href="/tutorial">{{ t('nav.tutorial') }}</a>
        <a href="/docs">{{ t('nav.api') }}</a>
        <template v-for="s in socials" :key="s.platform">
          <a v-if="s.kind === 'link'" class="hidem" :href="s.url" target="_blank" rel="noopener">{{ socialLabel(s.platform) }} ↗</a>
          <button v-else class="hidem as-link" type="button" @click="socialGo(s)">{{ socialLabel(s.platform) }}</button>
        </template>
        <a @click="openSignin()">{{ t('nav.signin') }}</a>
        <button class="btn primary sm" @click="openSignin()">{{ t('nav.startFree') }}</button>
        <LanguageSwitch/>
      </nav>
      <WeChatQrDialog v-if="wechatQr" @close="wechatQr=false"/>
    </div>
</template>

<style scoped>
.pubnav-links .as-link{background:none;border:0;padding:0;font:inherit;color:inherit;cursor:pointer}
</style>

