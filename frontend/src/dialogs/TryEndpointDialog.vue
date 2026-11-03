<script>
import { useDashboard } from '../state/context'
import TikTokPostForm from './TikTokPostForm.vue'
export default { components: { TikTokPostForm }, setup: useDashboard }
</script>

<template>
<div class="scrim" role="dialog" aria-labelledby="try-endpoint-dialog-title" aria-modal="true" v-dialog="closeEpTry" @click.self="closeEpTry" style="place-items:stretch;justify-items:end">
      <!-- Opened from a catalog tool drawer, it stacks on top of that one: same width, and the tool it
           came from stays visible underneath (ToolDrawer's .behind), one Escape away. -->
      <div class="drawer" :class="{stack:!!drawerEp}"><div class="hd" style="padding:15px 18px;border-bottom:1px solid var(--line)"><b id="try-endpoint-dialog-title">{{isTikTokPost(epTry)?t('try.titleTikTok'):t('try.title')+' “'+epTry.id+'”'}}</b><button class="btn sm" @click="closeEpTry" :aria-label="t('common.close')">✕</button></div>
        <div class="bd" style="padding:16px 18px;overflow:auto">
          <template v-if="!isTikTokPost(epTry)">
          <p class="explain"><span class="mono">{{epTry.method||'GET'}} {{epTryDisplayPath}}</span><br>{{epTry.summary}}</p>
          <p class="sub" v-if="epTryAccess" style="margin:0 0 12px">
            <template v-if="epTryAccess.tier==='anonymous'">◎ {{epTryAccess.detail||t('try.anonymousFree')}}</template>
            <template v-else-if="epTryAccess.tier==='platform'">⚡ {{epTryAccess.detail||t('try.platformBilled')}}</template>
            <template v-else-if="epTryAccess.tier==='tool'||epTryAccess.tier==='credential'">🔑 {{ t('try.toolCredential', { provider: epTry.provider_display||epTry.provider }) }}</template>
            <!-- A routed tool: say who can serve it now in one line; the providers this example cannot
                 use, and why, are there for whoever asks rather than a paragraph above the form. -->
            <template v-else-if="epTryAccess.tier==='routed'">⚡ {{ t('try.routed', { n: (epTryAccess.plan||[]).length, s: ((epTryAccess.plan||[]).length===1?'':'s'), name: provName((epTryAccess.plan||[{}])[0].provider) }) }}
              <details v-if="(epTryAccess.dropped||[]).length" style="margin-top:6px"><summary style="cursor:pointer">{{ t('try.notUsedForExample', { n: epTryAccess.dropped.length }) }}</summary>
                <ul style="margin:6px 0 0;padding-left:18px"><li v-for="d in epTryAccess.dropped" :key="d.endpoint_id"><span class="mono">{{d.endpoint_id}}</span>: {{d.why}}</li></ul></details></template>
            <template v-else>{{epTryAccess.detail||t('try.notCallable')}}</template>
          </p>

          <div v-if="epTryShowAuthSelector" class="field auth-method-field" style="max-width:520px;margin-bottom:16px">
            <label>{{t('try.authorization')}}</label>
            <select v-model="epTryAuthMethod" @change="loadEpTryAccess">
              <option v-for="m in epTryAuthMethods" :key="m" :value="m">{{authorizationMethodLabel(epTry.provider,m)}}</option>
            </select>
          </div>

          <div class="seg" style="margin-bottom:16px">
            <button :class="{on:epTryTab==='agent'}" @click="epTryTab='agent'">{{t('try.tabAgent')}}</button>
            <button :class="{on:epTryTab==='cli'}" @click="epTryTab='cli'">CLI</button>
            <button :class="{on:epTryTab==='api'}" @click="epTryTab='api'">API</button>
            <button :class="{on:epTryTab==='manual'}" @click="epTryTab='manual'">{{t('try.tabManual')}}</button>
          </div>
          </template>

          <!-- AI AGENT — one-line setup (token embedded here only), then the prompt to run this endpoint -->
          <template v-if="epTryTab==='agent'">
            <div class="lbl">{{t('try.step1Setup')}}</div>
            <p class="sub" style="margin:4px 0 8px">{{t('try.agentSetupNote')}}</p>
            <div class="lc-codewrap"><button class="lc-cp" @click="copyStart(epTrySetupLine,'ep-setup')">{{startCopied==='ep-setup'?t('try.copied'):t('try.copy')}}</button><pre style="white-space:pre-wrap;word-break:break-all">{{epTrySetupLine}}</pre></div>
            <div class="lbl" style="margin-top:20px">{{t('try.step2Ask')}}</div>
            <p class="sub" style="margin:4px 0 8px">{{t('try.agentUseNote')}}</p>
            <div class="lc-codewrap"><button class="lc-cp" @click="copyStart(epTryAgentUse,'ep-use')">{{startCopied==='ep-use'?t('try.copied'):t('try.copy')}}</button><pre style="white-space:pre-wrap">{{epTryAgentUse}}</pre></div>
          </template>

          <!-- CLI — install, sign in, inspect, run this exact endpoint -->
          <template v-else-if="epTryTab==='cli'">
            <div class="lbl">{{t('try.cliStep1')}}</div>
            <div class="lc-codewrap"><button class="lc-cp" @click="copyStart('curl -fsSL '+proxy+'/install.sh | sh\ntreg login','ep-cli1')">{{startCopied==='ep-cli1'?t('try.copied'):t('try.copy')}}</button><pre>curl -fsSL {{proxy}}/install.sh | sh
treg login</pre></div>
            <div class="lbl" style="margin-top:18px">{{t('try.cliStep2')}}</div>
            <div class="lc-codewrap"><button class="lc-cp" @click="copyStart('treg catalog get '+epTry.id,'ep-cli2')">{{startCopied==='ep-cli2'?t('try.copied'):t('try.copy')}}</button><pre>treg catalog get {{epTry.id}}</pre></div>
            <div class="lbl" style="margin-top:18px">{{t('try.cliStep3')}}{{epTry.id==='fishaudio.voices.list'?t('try.byokServerSide'):(epTryAccess&&epTryAccess.tier==='anonymous'?t('try.noKeyNeeded'):t('try.keyInjected'))}}</div>
            <div class="lc-codewrap"><button class="lc-cp" @click="copyStart(epTryCliCall,'ep-cli3')">{{startCopied==='ep-cli3'?t('try.copied'):t('try.copy')}}</button><pre style="white-space:pre-wrap;word-break:break-all">{{epTryCliCall}}</pre></div>
          </template>

          <!-- API — the raw /call/ passthrough with the token header -->
          <template v-else-if="epTryTab==='api'">
            <p v-if="epTry.id==='fishaudio.voices.list'" class="sub" style="margin:0 0 8px">{{t('try.fishApiNote')}}</p>
            <p v-else class="sub" style="margin:0 0 8px">{{t('try.oneEndpointOneToken')}}{{epTryAccess&&epTryAccess.tier==='anonymous'?t('try.publicNoKey'):t('try.injectServerSide')}} {{t('try.relaysVerbatim')}}</p>
            <div class="lc-codewrap"><button class="lc-cp" @click="copyStart(epTryCurl,'ep-api')">{{startCopied==='ep-api'?t('try.copied'):t('try.copy')}}</button><pre style="white-space:pre-wrap;word-break:break-all">{{epTryCurl}}</pre></div>
            <p class="sub" v-if="!myToken" style="margin:8px 0 0;font-size:12px"><span class="mono">$TREG_TOKEN</span> {{t('try.tokenPlaceholder')}}</p>
          </template>

          <!-- TikTok direct post: TikTok's required post screen; opened on this tab with the tabs hidden -->
          <TikTokPostForm v-else-if="isTikTokPost(epTry)" />

          <!-- MANUAL — the live test form -->
          <template v-else>
            <!-- Not callable from here (no key connected / no treg price): don't strand the user on a
                 dead Run button — point them at the tab that DOES work. -->
            <div v-if="epTryAccess && !['anonymous','platform','tool','credential','routed'].includes(epTryAccess.tier)"
                 class="banner" style="margin:0">
              {{epTryAccess.missing_message || (mkOauth(epTry.provider) ? t('try.missingOauth', { provider: epTry.provider_display||epTry.provider }) : t('try.missingKey'))}}
              <div style="margin-top:10px">
                <button v-if="mkOauth(epTry.provider)" class="btn sm primary" @click="openProvider(epTry.provider); closeEpTry()">{{epTryAccess.action_label||endpointConnectLabel(epTry)}}</button>
                <button v-else-if="mkKnown(epTry.provider)" class="btn sm primary" @click="goByok(epTry.provider)">🔑 {{t('try.byok')}}</button>
              </div>
            </div>
            <template v-else>
              <div class="field" v-for="p in epTryVisibleParams" :key="p.name" style="max-width:520px">
                <label class="mono" style="min-width:140px">{{p.name}} <span class="muted">({{p.location}})</span><span v-if="p.required" style="color:var(--accent)"> *</span></label>
                <input v-model="p.value" :placeholder="p.required?t('try.required'):t('try.optional')"/>
              </div>
              <p v-if="!epTryVisibleParams.length && (epTry.method||'GET')==='GET'" class="sub" style="margin:0 0 12px">{{t('try.noParams')}}</p>
              <template v-if="epTryBodyType==='multipart'">
                <div class="field" v-for="p in epTryMultipart" :key="p.name" style="max-width:520px">
                  <label class="mono" style="min-width:140px">{{p.name}}<span v-if="p.required" style="color:var(--accent)"> *</span></label>
                  <input v-if="String(p.type).includes('file')" type="file" :multiple="String(p.type).startsWith('array')" @change="setEpTryFiles(p.name,$event)"/>
                  <input v-else v-model="p.value" :placeholder="p.required?t('try.required'):t('try.optional')"/>
                </div>
              </template>
              <div v-else-if="(epTry.method||'GET')!=='GET' && epTryBody!==''" class="field" style="max-width:520px;align-items:flex-start">
                <label style="min-width:140px">{{t('try.bodyJson')}}</label>
                <textarea v-model="epTryBody" rows="6" style="width:100%;font-family:var(--mono);font-size:12px"></textarea>
              </div>
              <button class="btn primary" :disabled="epTryBusy" @click="runEpTry">{{epTryBusy?t('try.running'):t('try.run')}}</button>
            </template>
            <div v-if="epTryResp" style="margin-top:14px">
              <div class="muted" style="font-size:12px;margin-bottom:6px">{{t('try.result')}}
                <span class="badge" :class="epTryStatus>=200&&epTryStatus<300?'ok':'invalid'">{{epTryStatus}}</span>
                · {{epTryMs}}ms<span v-if="epTryCost!=null"> · {{t('try.charged')}} {{money(epTryCost)}}<span v-if="epTryCost===0 && epTryStatus>=200 && epTryStatus<300" :title="epTryAccess&&epTryAccess.tier==='anonymous'?t('try.freeNoKey'):t('try.freeProviderZero')"> {{epTryAccess&&epTryAccess.tier==='anonymous'?t('try.freeNoKeyShort'):t('try.freeZeroShort')}}</span></span>
                <template v-if="epTry.id!=='fishaudio.voices.list'"> {{t('try.loggedActivity')}}</template></div>
              <audio v-if="epTryAudioUrl" :src="epTryAudioUrl" controls style="width:100%;margin:8px 0"></audio>
              <a v-if="epTryAudioUrl" class="btn sm" :href="epTryAudioUrl" :download="epTryAudioName">{{t('try.downloadAudio')}}</a>
              <pre v-if="!epTryAudioUrl" style="max-height:340px;overflow:auto">{{epTryResp}}</pre>
            </div>
            <div v-if="epTry.provider==='fishaudio'" style="margin-top:20px;border-top:1px solid var(--line);padding-top:14px">
              <div style="display:flex;justify-content:space-between;align-items:center"><b>{{fishVoicesSource==='byok'?t('try.yourFishVoices'):t('try.teamVoices')}}</b><button class="btn sm" @click="loadFishVoices">{{t('try.refresh')}}</button></div>
              <p v-if="fishVoiceNote" class="sub" style="margin:6px 0 0">{{fishVoiceNote}}</p>
              <p v-if="!fishVoices.length && !fishVoiceBusy" class="sub">{{fishVoicesSource==='byok'?t('try.noByokVoices'):t('try.noTeamVoices')}}</p>
              <p v-if="fishVoiceBusy" class="sub">{{t('try.loadingVoices')}}</p>
              <div v-for="v in fishVoices" :key="v.id" class="card" style="padding:10px;margin-top:8px">
                <div><b>{{v.display_name||t('try.untitledVoice')}}</b><div class="mono muted" style="font-size:11px">{{v.upstream_id}}</div></div>
                <div style="display:flex;gap:6px;margin-top:8px;flex-wrap:wrap">
                  <button class="btn sm" @click="useFishVoice(v)">{{t('try.useInTts')}}</button>
                  <button class="btn sm" @click="beginRenameFishVoice(v)">{{t('try.rename')}}</button>
                  <button class="btn sm danger" @click="beginDeleteFishVoice(v)">{{t('common.delete')}}</button>
                </div>
              </div>
            </div>
          </template>
        </div></div>
    </div>
</template>
