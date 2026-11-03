<script>
import { useDashboard } from '../state/context'
import BrandMark from './BrandMark.vue'
import { t } from '../i18n/index'
export default {
  components: { BrandMark }, setup: useDashboard,
  data: () => ({ ssoChoices: [], ssoBusy: false, ssoMode: false }),
  methods: {
    setSsoMode(enabled) {
      this.ssoMode = enabled
      this.ssoChoices = []
      this.loginErr = ''
    },
    async ssoLogin() {
      const email = this.emailInput.trim()
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { this.loginErr = t('signin.enterWorkEmail'); return }
      this.ssoBusy = true; this.loginErr = ''; this.ssoChoices = []
      try {
        const response = await fetch('/auth/sso/discover', {
          method: 'POST', headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ email }),
        })
        const result = await response.json()
        if (!response.ok) throw new Error(result.detail || t('signin.noCompanySignin'))
        this.ssoChoices = result.teams || []
        if (this.ssoChoices.length === 1) this.ssoGo(this.ssoChoices[0].slug)
        else if (!this.ssoChoices.length) this.loginErr = t('signin.noSsoConnection')
      } catch (error) { this.loginErr = error.message || t('signin.noCompanySignin') }
      finally { this.ssoBusy = false }
    },
    ssoGo(slug) {
      this._stashNext()
      location.href = `/auth/sso/${encodeURIComponent(slug)}/start`
    },
  },
}
</script>

<template>
<div v-if="demo.signin" class="lc-scrim open" @click.self="demo.signin=false">
    <div class="lc-modal" role="dialog" aria-modal="true" :aria-label="t('nav.signin')" v-dialog="() => { demo.signin=false }">
      <button class="cls" @click="demo.signin=false" :aria-label="t('common.close')">✕</button>
      <div style="font-size:22px;line-height:1"><BrandMark/></div>
      <h2 style="margin:8px 0 2px;font-family:var(--mono)">{{oauthSignin?t('signin.titleOauth'):(invitePrefill?t('signin.titleInvite'):(shareGate?t('signin.titleShare'):(publicCatalog?t('signin.titleCatalog'):t('signin.titleDefault'))))}}</h2>
      <p v-if="oauthSignin" class="sub">{{ t('signin.oauthSub') }}</p>
      <p v-else-if="invitePrefill" class="sub">{{ t('signin.inviteSub', {email: invitePrefill}) }}</p>
      <p v-else-if="shareGate" class="sub">{{ t('signin.shareSub', {name: shareGate.name}) }}</p>
      <!-- The default line is the SANDBOX's ("bring it into a real account"), which is nonsense to
           someone who arrived on a catalog page from a search result and has no sandbox. -->
      <p v-else-if="publicCatalog" class="sub">{{ t('signin.catalogSub') }}</p>
      <p v-else class="sub">{{ t('signin.defaultSub') }}</p>
      <div v-if="!emailStage">
        <label for="sign-in-email" class="sub" style="display:block;text-align:left;margin:14px 0 4px">{{ t('signin.email') }}</label>
        <div class="field"><input id="sign-in-email" v-model="emailInput" type="email" autocomplete="email" data-captcha="email_start" placeholder="you@work.com" @input="ssoChoices=[];loginErr=''" @keyup.enter="ssoMode?ssoLogin():emailStart()"/></div>
        <button v-if="ssoMode" class="btn primary" style="width:100%;display:flex;align-items:center;justify-content:center;gap:9px" :disabled="ssoBusy" @click="ssoLogin"><img src="/media/signin/shield.svg" alt="" aria-hidden="true" style="width:17px;height:17px;filter:invert(1)"/>{{ssoBusy?t('signin.findingCompany'):t('signin.continueSso')}}</button>
        <button v-else class="btn primary" style="width:100%;display:flex;align-items:center;justify-content:center;gap:9px" @click="emailStart" :disabled="busy"><img src="/media/signin/mail.svg" alt="" aria-hidden="true" style="width:17px;height:17px;filter:invert(1)"/>{{busy?t('signin.sending'):t('signin.emailCode')}}</button>
        <div v-if="ssoChoices.length > 1" style="margin-top:10px">
          <p class="sub">{{ t('signin.chooseCompany') }}</p>
          <button v-for="team in ssoChoices" :key="team.slug" class="btn" style="width:100%;margin-top:6px;display:flex;align-items:center;justify-content:center;gap:9px" @click="ssoGo(team.slug)"><img src="/media/signin/shield.svg" alt="" aria-hidden="true" style="width:17px;height:17px"/>{{team.name}} · {{team.slug}}</button>
        </div>
      </div>
      <div v-else>
        <p class="sub" style="font-size:11px;margin:2px 0 8px">{{ t('signin.codeSentTo', {email: emailInput}) }}<span v-if="devCode"> · {{ t('signin.devCode') }} <b class="mono">{{devCode}}</b></span> · <a href="#" @click.prevent="emailStage=false">{{ t('signin.change') }}</a></p>
        <div class="field"><input v-model="codeInput" inputmode="numeric" :placeholder="t('signin.codePlaceholder')" @keyup.enter="emailVerify"/></div>
        <button class="btn primary" style="width:100%;display:flex;align-items:center;justify-content:center;gap:9px" @click="emailVerify" :disabled="busy"><img src="/media/signin/mail.svg" alt="" aria-hidden="true" style="width:17px;height:17px;filter:invert(1)"/>{{busy?t('signin.verifying'):t('nav.signin')}}</button>
      </div>
      <div class="sub" style="margin:14px 0 8px;text-align:center">{{ t('signin.orWith') }}</div>
      <button v-if="!emailStage" class="btn" style="width:100%;padding:11px;margin-bottom:8px;display:flex;align-items:center;justify-content:center;gap:9px" @click="setSsoMode(!ssoMode)"><img :src="ssoMode?'/media/signin/arrow-left.svg':'/media/signin/shield.svg'" alt="" aria-hidden="true" style="width:17px;height:17px"/>{{ssoMode?t('signin.emailSignIn'):t('signin.companySso')}}</button>
      <button v-if="meta.github" class="btn" style="width:100%;padding:11px;margin-bottom:8px;display:flex;align-items:center;justify-content:center;gap:9px" @click="githubLogin"><img src="/media/recruit/github.svg" alt="" aria-hidden="true" style="width:17px;height:17px"/>GitHub</button>
      <button v-if="meta.google" class="btn" style="width:100%;padding:11px;margin-bottom:8px;display:flex;align-items:center;justify-content:center;gap:9px" @click="googleLogin"><img src="/media/aeo/logos/google.svg" alt="" aria-hidden="true" style="width:17px;height:17px"/>Google</button>
      <details v-if="!oauthSignin" style="margin-top:12px;text-align:left">
        <summary class="sub" style="cursor:pointer;text-align:center">{{ t('signin.pasteToken') }}</summary>
        <div class="field" style="margin-top:8px"><input v-model="tokenInput" type="password" placeholder="X-Treg-Token" @keyup.enter="addToken(tokenInput)"/></div>
        <button class="btn" style="width:100%" @click="addToken(tokenInput)" :disabled="busy">{{busy?t('app.checking'):t('signin.signinWithToken')}}</button>
      </details>
      <div v-if="loginErr" class="banner" style="margin-top:12px">{{loginErr}}</div>
    </div>
  </div>
</template>
