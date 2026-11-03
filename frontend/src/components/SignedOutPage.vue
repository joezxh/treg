<script>
import { useDashboard } from '../state/context'
import BrandMark from './BrandMark.vue'
import { t } from '../i18n/index'
export default { components: { BrandMark }, setup() { const ctx = useDashboard(); ctx.t = t; return ctx } }
</script>

<template>
  <div class="lp">
    <header class="lp-nav">
      <a href="/" class="brand"><BrandMark/>treg</a>
      <nav class="lp-links">
        <a href="/tutorial">{{ t('signed.docs') }}</a>
        <button class="iconbtn" @click="toggleTheme" :aria-label="theme==='dark' ? t('signed.lightTheme') : t('signed.darkTheme')">{{theme==='dark'?'◐':'◑'}}</button>
      </nav>
    </header>
    <main class="lp-hero" style="min-height:55vh">
      <template v-if="shareGate">
        <div class="lp-eyebrow">{{ t('signed.sharedWithYou') }}</div>
        <h1 class="lp-h1">{{shareGate.name}} <span style="color:var(--accent)">· {{shareGate.kind}}</span></h1>
        <p class="lp-lead">{{ t('signed.sharedLead', { kind: shareGate.kind }) }}</p>
      </template>
      <template v-else>
        <h1 class="lp-h1">{{ t('signed.signInToTreg') }}</h1>
        <p class="lp-lead">{{ t('signed.connectManage') }}</p>
      </template>
      <div class="lp-cta"><button class="btn primary lg" @click="demo.signin=true">{{ t(shareGate ? 'signed.signInToView' : 'signed.signIn') }}</button></div>
    </main>
  </div>
</template>
