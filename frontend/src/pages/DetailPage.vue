<script>
import { useDashboard } from '../state/context'
export default { setup: useDashboard }
</script>

<template>

          <div class="tut-head">
            <div>
              <p class="sub" style="margin:0 0 4px"><a href="/app#tools" @click.prevent="go('tools')">← {{ t('nav.tools') }}</a></p>
              <h1 style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">{{detail.name}}
                <span class="chip">{{detail.kind==='skill' ? t('detail.chipSkill') : (detailData&&detailData.cli ? t('detail.chipEndpointCli') : t('detail.chipEndpoint'))}}</span>
                <span v-if="detailData&&detailData.owner" class="chip" :title="t('detail.sharedBy', { owner: detailData.owner })">{{detailData.owner}}</span>
              </h1>
            </div>
            <div class="tut-actions" style="position:relative">
              <template v-if="detailData && detail.kind==='skill' && (detailData.tools||[]).length">
                <button class="btn sm" @click.stop="(detailData.tools.length===1 ? tryDetailTool(detailData.tools[0]) : tryMenu=!tryMenu)" :title="t('detail.tryTitle')">▶ {{ t('detail.tryIt') }}</button>
                <div v-if="tryMenu" style="position:fixed;inset:0;z-index:29" @click="tryMenu=false"></div>
                <div class="dropdown" v-if="tryMenu" style="left:auto;right:0;top:110%;width:260px" @click.stop>
                  <div class="row" v-for="t in detailData.tools" :key="'try'+t.id" @click="tryDetailTool(t)"><span style="min-width:0"><b style="font-size:12.5px">⚒ {{t.name}}</b><span class="sub" style="display:block;font-size:11px;margin-top:1px">{{t.host||t.base_url}}</span></span></div>
                </div>
              </template>
              <template v-if="canRegister && detailData">
                <button v-if="detail.kind==='tool'" class="btn sm" @click="configureTool(detailData)" :title="t('detail.configureTitle', { type: detailData.cli ? t('detail.cli') : t('detail.endpoint'), part: detailData.cli ? t('detail.denyLocal') : t('detail.bindings') })">⚙ {{ t('detail.configure') }}</button>
                <template v-else-if="(detailData.tools||[]).length">
                  <button class="btn sm" @click.stop="(detailData.tools.length===1 ? configureTool(detailData.tools[0]) : cfgMenu=!cfgMenu)" :title="t('detail.configureSkillTitle')">⚙ {{ t('detail.configure') }}</button>
                  <div v-if="cfgMenu" style="position:fixed;inset:0;z-index:29" @click="cfgMenu=false"></div>
                  <div class="dropdown" v-if="cfgMenu" style="left:auto;right:0;top:110%;width:260px" @click.stop>
                    <div class="row" v-for="t in detailData.tools" :key="'cfg'+t.id" @click="configureTool(t)"><span style="min-width:0"><b style="font-size:12.5px">⚒ {{t.name}}</b><span class="sub" style="display:block;font-size:11px;margin-top:1px">{{t.host||t.base_url}}</span></span></div>
                  </div>
                </template>
              </template>
              <button class="btn sm" @click="copyDetail(detailShareUrl,'url')" :title="t('detail.copyLinkTitle')">{{detailCopied==='url'?t('common.copied'):t('detail.copyLink')}}</button>
              <button v-if="canAdmin && detailData" class="btn sm primary" @click="openShare" :title="t('detail.shareTitle')">{{ t('detail.share') }}</button>
            </div>
          </div>
          <div v-if="detailErr" class="banner" style="margin-top:12px">{{detailErr}}</div>
          <div v-if="detailNote" class="tut-notice" style="margin-top:12px;max-width:860px">{{detailNote}}</div>
          <p v-if="detailLoading" class="sub">{{ t('common.loading') }}</p>

          <template v-if="detailData && detail.kind==='skill'">
            <div style="max-width:860px;border:1px solid var(--line);border-radius:16px;padding:16px 18px;margin:14px 0;background:var(--panel)">
              <h3 style="margin:0 0 6px;font-size:14px">{{ t('detail.useWithAgent') }}</h3>
              <p class="sub" style="margin:0 0 10px">{{ t('detail.useWithAgentSkill1') }}<template v-if="(detailData.secrets||[]).length">{{ t('detail.cred') }}{{ detailData.secrets.length>1 ? t('detail.credStayPlural') : t('detail.credStay') }}{{ t('detail.credServer') }}</template></p>
              <pre class="code" style="white-space:pre-wrap;max-height:34vh;overflow:auto">{{detailPrompt}}</pre>
              <div style="margin-top:10px;display:flex;gap:10px;align-items:center;flex-wrap:wrap">
                <button class="btn primary" @click="copyDetail(detailPrompt,'prompt')">⧉ {{detailCopied==='prompt'?t('common.copiedAlt'):t('detail.copyPrompt')}}</button>
                <button class="btn" @click="copyDetail('treg skill install '+detail.name,'cli')" :title="t('detail.tregSkillInstall', { name: detail.name })">{{detailCopied==='cli'?t('common.copied'):t('detail.tregSkillInstall', { name: detail.name })}}</button>
              </div>
            </div>
            <div v-if="(detailData.tools||[]).length || (detailData.secrets||[]).length" style="max-width:860px;margin:0 0 14px;display:flex;gap:8px;flex-wrap:wrap;align-items:center">
              <span class="sub" style="margin:0">{{ t('detail.bundled') }}</span>
              <a v-for="t in detailData.tools" :key="'dt'+t.id" class="chip" :href="'/app/tools/'+encodeURIComponent(t.name)" @click.prevent="openDetail('tool',t.name)" style="cursor:pointer" :title="t('detail.toolChip', { host: t.host||t.base_url })">⚒ {{t.name}}</a>
              <span v-for="s in detailData.secrets" :key="'ds'+s.id" class="chip" :title="t('detail.credChip')">🔒 {{s.name||s.local_name}}</span>
            </div>
            <div style="max-width:860px;border:1px solid var(--line);border-radius:16px;overflow:hidden;display:flex;min-height:280px;background:var(--panel)">
              <div style="width:220px;flex:none;border-right:1px solid var(--line);padding:10px 0;overflow:auto;max-height:60vh">
                <div v-for="row in detailTree" :key="row.path"
                     :style="{padding:'4px 12px 4px '+(14+row.depth*14)+'px', cursor:row.dir?'default':'pointer', fontSize:'12.5px',
                              color:row.dir?'var(--muted)':'var(--ink)', background:(!row.dir&&detailFile===row.path)?'var(--panel2)':'transparent'}"
                     @click="!row.dir && (detailFile=row.path)">{{row.dir?'▸ ':'· '}}{{row.name}}</div>
              </div>
              <pre class="code" style="flex:1;margin:0;border:0;border-radius:0;white-space:pre-wrap;word-break:break-word;overflow:auto;max-height:60vh">{{detailFileContent}}</pre>
            </div>
          </template>

          <template v-if="detailData && detail.kind==='tool'">
            <div style="max-width:860px;border:1px solid var(--line);border-radius:16px;padding:16px 18px;margin:14px 0;background:var(--panel)">
              <h3 style="margin:0 0 6px;font-size:14px">{{ t('detail.useWithAgent') }}</h3>
              <p class="sub" style="margin:0 0 10px">{{ t('detail.useWithAgentTool') }}</p>
              <pre class="code" style="white-space:pre-wrap;max-height:34vh;overflow:auto">{{detailPrompt}}</pre>
              <div style="margin-top:10px;display:flex;gap:10px;align-items:center;flex-wrap:wrap">
                <button class="btn primary" @click="copyDetail(detailPrompt,'prompt')">⧉ {{detailCopied==='prompt'?t('common.copiedAlt'):t('detail.copyPrompt')}}</button>
                <button class="btn" @click="openCopy(detailData)" :title="t('detail.callSnippetsTitle')">⧉ {{ t('detail.callSnippets') }}</button>
                <button class="btn" @click="openUse(detailData)" :title="t('detail.tryHere')">▶ {{ t('detail.tryIt') }}</button>
              </div>
            </div>
            <div style="max-width:860px;border:1px solid var(--line);border-radius:16px;padding:16px 18px;background:var(--panel)">
              <div class="lbl">{{ t('detail.upstream') }}</div>
              <p style="margin:2px 0 12px"><span class="mono">{{detailData.base_url}}</span></p>
              <div class="lbl">{{ t('detail.credentials') }}</div>
              <p class="sub" style="margin:2px 0 12px" v-if="(detailData.bindings||[]).length || (detailData.cli&&(detailData.cli.inject||[]).length)"><span class="chip" v-for="(w,wi) in credChips(detailData)" :key="'dw'+wi" :class="w.kind" :title="w.title">{{w.label}}</span>{{ t('detail.injectedEveryCall') }}</p>
              <p class="sub" style="margin:2px 0 12px" v-else>{{ t('detail.noCredentialNeeded') }}</p>
              <template v-if="(detailData.examples||[]).length">
                <div class="lbl">{{ t('detail.examples') }}</div>
                <div class="exrow" style="margin:4px 0 12px"><span v-for="(ex,exi) in detailData.examples" :key="'de'+exi" class="exchip"><span class="m">{{ex.method||'GET'}}</span>{{ex.note||ex.path}}</span></div>
              </template>
              <template v-if="detailData.cli">
                <div class="lbl">{{ t('detail.cli') }}</div>
                <p class="sub" style="margin:2px 0 12px"><span class="mono">treg run {{detail.name}} -- &lt;args&gt;</span>
                  <span class="chip ok" v-if="detailData.server_runnable" :title="t('detail.serverTitle')">{{ t('own.where.server') }}</span>
                  <span class="chip" v-else :title="t('detail.localOnlyTitle')">{{ t('detail.localOnly') }}</span>
                  <span class="chip run" v-if="!detailData.cli.enabled" :title="t('detail.runOffTitle')">⌘ {{ t('detail.runOff') }}</span>
                </p>
                <template v-if="(detailData.cli.deny||[]).length">
                  <div class="lbl">{{ t('detail.guardrails') }}</div>
                  <p class="sub" style="margin:2px 0 12px">{{ t('detail.guardrailsExplain') }}<span class="mono" v-for="(p,pi) in detailData.cli.deny" :key="'dg'+pi" style="margin-right:8px">{{p}}</span></p>
                </template>
              </template>
              <template v-if="detailParentSkill">
                <div class="lbl">{{ t('detail.fromSkill') }}</div>
                <p style="margin:2px 0 0"><a :href="'/app/skills/'+encodeURIComponent(detailParentSkill.name)" @click.prevent="openDetail('skill',detailParentSkill.name)">▚ {{detailParentSkill.name}}</a>{{ t('detail.fromSkillExplain') }}</p>
              </template>
            </div>
          </template>

</template>
