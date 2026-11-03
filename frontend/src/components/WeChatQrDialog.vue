<script>
import { t } from '../i18n/index'
// WeChat has no web profile: the account is a QR code. Shown from every surface's social list
// (state/social.ts, kind 'qrcode'). The parent owns visibility (`v-if` + @close); the image is a
// placeholder until the account exists — swap /media/wechat-qr.svg in one place.
export default {
  emits: ['close'],
  methods: { t },
}
</script>

<template>
  <div class="scrim" role="dialog" aria-modal="true" :aria-label="t('social.wechatQrTitle')"
       v-dialog="() => $emit('close')" @click.self="$emit('close')">
    <div class="modal" style="width:min(360px,92vw);text-align:center">
      <div class="hd"><b>{{ t('social.wechatQrTitle') }}</b><button class="btn sm" @click="$emit('close')" :aria-label="t('common.close')">✕</button></div>
      <div style="padding:18px">
        <img src="/media/wechat-qr.svg" :alt="t('social.wechatQrHint')" style="width:220px;height:220px;border-radius:10px;background:#fff"/>
        <p class="sub" style="margin:12px 0 0">{{ t('social.wechatQrHint') }}</p>
      </div>
    </div>
  </div>
</template>
