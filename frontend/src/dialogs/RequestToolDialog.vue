<script>
import { useDashboard } from '../state/context'
export default { setup: useDashboard }
</script>

<template>
<div class="scrim" role="dialog" aria-labelledby="request-tool-dialog-title" aria-modal="true" v-dialog="() => { reqAsk=false;reqErr='' }" @click.self="reqAsk=false;reqErr=''">
      <div class="modal" style="width:min(520px,95vw)"><div class="hd"><b id="request-tool-dialog-title">{{t('req.title')}}</b><button class="btn sm ico" @click="reqAsk=false;reqErr=''" :aria-label="t('common.close')">✕</button></div>
        <div style="padding:16px 18px">
          <template v-if="!reqDone">
            <p class="explain" style="margin-top:0">{{ t('req.intro') }}</p>
            <div class="lbl" style="margin-top:14px">{{ t('req.whatsMissing') }}</div>
            <div class="field" style="margin:0"><input v-model="reqForm.capability" maxlength="200" :placeholder="t('req.capabilityPlaceholder')" @keyup.enter="submitToolRequest"/></div>
            <div class="lbl" style="margin-top:14px">{{ t('req.details') }} <span style="text-transform:none;letter-spacing:0;color:var(--muted2)">{{ t('req.detailsOptional') }}</span></div>
            <div class="field" style="margin:0"><textarea v-model="reqForm.note" maxlength="2000" rows="3" :placeholder="t('req.notePlaceholder')" style="resize:vertical;min-width:0"></textarea></div>
            <template v-if="!me">
              <div class="lbl" style="margin-top:14px">{{ t('req.contact') }} <span style="text-transform:none;letter-spacing:0;color:var(--muted2)">{{ t('req.contactOptional') }}</span></div>
              <div class="field" style="margin:0"><input v-model="reqForm.contact" maxlength="200" :placeholder="t('req.contactPlaceholder')"/></div>
            </template>
            <div v-if="reqErr" class="banner" style="margin-top:12px">{{reqErr}}</div>
            <div style="display:flex;align-items:center;gap:12px;margin-top:18px">
              <button class="btn primary" @click="submitToolRequest" :disabled="reqBusy">{{reqBusy?t('req.sending'):t('req.sendRequest')}}</button>
              <span class="sub" style="font-size:11.5px;margin:0">{{ t('req.takesSeconds') }}</span>
            </div>
          </template>
          <template v-else>
            <div style="text-align:center;padding:18px 6px 8px">
              <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="var(--accent, currentColor)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/></svg>
              <p style="margin:12px 0 4px;font-weight:600">{{ t('req.thanks') }}</p>
              <p class="sub" style="margin:0 0 16px">{{ t('req.thanksSub') }}</p>
              <button class="btn" @click="reqAsk=false">{{ t('common.close') }}</button>
            </div>
          </template>
        </div></div>
    </div>
</template>
