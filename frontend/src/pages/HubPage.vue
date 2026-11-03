<script>
import { useDashboard } from '../state/context'
export default { setup: useDashboard }
</script>

<template>
          <template v-if="!hub.tool">
            <h1>{{ t('hubPage.title', { name: activeName }) }}</h1>
            <p class="sub">{{ t('hubPage.lede') }}</p>
            <p v-if="hub.err" class="err">{{hub.err}}</p>
            <p v-if="hub.note" class="sub">{{hub.note}}</p>
            <div class="statgrid" style="margin:12px 0;grid-template-columns:repeat(auto-fit,minmax(150px,1fr))">
              <div class="stat"><div class="n">{{hubLive()}}</div><div class="l">{{ t('hubPage.statLiveTools') }}</div></div>
              <div class="stat"><div class="n">{{money(hubEarned30())}}</div><div class="l">{{ t('hubPage.statEarned30') }}</div></div>
              <div class="stat"><div class="n">{{hubRuns30()}}</div><div class="l">{{ t('hubPage.statRuns30') }}</div></div>
              <div class="stat"><div class="n">{{hubFailing()}}</div><div class="l">{{ t('hubPage.statFailing') }}</div></div>
            </div>
            <p class="sub">{{ t('hubPage.createFrom') }}<code>treg hub init &lt;name&gt; --script</code> · <code>hub_create</code> {{ t('hubPage.overMcp') }}</p>
            <p v-if="hub.loading" class="sub">{{ t('hubPage.loading') }}</p>
            <p v-else-if="!hubNewest().length" class="sub">{{ t('hubPage.noTools') }}</p>
            <table v-else>
              <tr><th>{{ t('hubPage.thTool') }}</th><th>{{ t('hubPage.thVer') }}</th><th>{{ t('hubPage.thStatus') }}</th><th>{{ t('hubPage.thKind') }}</th><th>{{ t('hubPage.thPrice') }}</th><th>{{ t('hubPage.thHealth') }}</th><th style="text-align:right">{{ t('hubPage.thRuns30d') }}</th><th style="text-align:right">{{ t('hubPage.thEarned30d') }}</th></tr>
              <tr v-for="t in hubNewest()" :key="t.tool_id" class="act-row" @click="openHubTool(t)">
                <td><b>{{t.tool_id}}</b><div class="muted" style="font-size:11px;max-width:52ch;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{t.summary}}</div></td>
                <td>{{t.version}}</td>
                <td><span :class="{ok:t.status==='live', warn:t.status==='failed', muted:t.status==='retired'}">{{t.status}}</span></td>
                <td>{{t.kind}}</td>
                <td :title="t.price_label">{{t.price_range||t.price_label||('$'+t.price_usd+'/run')}}<span v-if="t.price_samples" class="muted"> · {{t.price_samples}} {{ t(t.price_samples===1 ? 'hubPage.runOne' : 'hubPage.runMany') }}</span></td>
                <td><span :class="{ok:t.health==='ok', warn:t.health==='failing', muted:t.health==='unknown'}">{{t.health}}</span><span v-if="t.fails_in_a_row" class="muted"> · {{t.fails_in_a_row}} {{ t('hubPage.failedInRow') }}</span></td>
                <td style="text-align:right">{{t.runs_30d}}</td>
                <td style="text-align:right">{{money(t.earned_30d_micro)}}</td>
              </tr>
            </table>
          </template>

          <template v-else>
            <div style="margin-bottom:8px"><button class="btn sm" @click="closeHubTool()">← {{ t('hubPage.allTools') }}</button></div>
            <h1>{{hub.tool.tool_id.split('.').slice(1).join('.')}} <span class="muted" style="font-size:13px">v{{hub.tool.version}} · {{hub.tool.status}} · {{hub.tool.kind}}</span></h1>
            <p class="sub" style="margin:0 0 8px"><code>{{hub.tool.tool_id}}</code> · <a :href="hubPage(hub.tool)" target="_blank" rel="noopener">{{ t('hubPage.publicPage') }} ↗</a></p>
            <p v-if="hub.err" class="err">{{hub.err}}</p>
            <p v-if="hub.note" class="sub">{{hub.note}}</p>
            <div style="display:flex;gap:8px;flex-wrap:wrap;margin:8px 0 4px">
              <button class="btn sm" @click="copyText(hubCallLine(hub.tool), t('hubPage.copyCallLine'))">Copy call line</button>
              <button class="btn sm" @click="copyText(hubPage(hub.tool), t('hubPage.copyShareUrl'))">Copy share URL</button>
              <button v-if="hub.tool.status==='live' && canRegister" class="btn sm" :class="{danger:hub.confirmRetire===hub.tool.tool_id}" @click="retireHubTool()">{{ t(hub.confirmRetire===hub.tool.tool_id ? 'hubPage.confirmRetire' : 'hubPage.retireTool') }}</button>
            </div>
            <div class="tabs" style="margin:10px 0 4px">
              <button :class="{active:hub.tab==='overview'}" @click="hub.tab='overview'">{{ t('hubPage.tabOverview') }}</button>
              <button :class="{active:hub.tab==='versions'}" @click="hub.tab='versions'">{{ t('hubPage.tabVersions') }}</button>
              <button :class="{active:hub.tab==='price'}" @click="hub.tab='price'">{{ t('hubPage.tabPrice') }}</button>
              <button :class="{active:hub.tab==='listing'}" @click="hub.tab='listing'">{{ t('hubPage.tabListing') }}</button>
              <button :class="{active:hub.tab==='earnings'}" @click="hub.tab='earnings'; loadHubEarnings()">{{ t('hubPage.tabEarnings') }}</button>
              <button :class="{active:hub.tab==='runs'}" @click="hub.tab='runs'; loadHubHealth()">{{ t('hubPage.tabRuns') }}</button>
              <button :class="{active:hub.tab==='health'}" @click="hub.tab='health'; loadHubHealth()">{{ t('hubPage.tabHealth') }}</button>
            </div>

            <template v-if="hub.tab==='overview'">
              <div class="statgrid" style="margin:12px 0;grid-template-columns:repeat(auto-fit,minmax(150px,1fr))">
                <div class="stat"><div class="n">{{hubRunCost(hub.tool)}}</div><div class="l">{{ hub.tool.price_samples ? t('hubPage.runCostSamples', { n: hub.tool.price_samples, run: t(hub.tool.price_samples===1 ? 'hubPage.runOne' : 'hubPage.runMany') }) : t('hubPage.runCostNone') }}</div></div>
                <div class="stat"><div class="n sm">{{hub.tool.price_label}}</div><div class="l">{{ t('hubPage.yourPrice') }}</div></div>
                <div class="stat"><div class="n">{{hub.tool.runs_30d}}</div><div class="l">{{ t('hubPage.runsOthers30') }}</div></div>
                <div class="stat"><div class="n">{{money(hub.tool.earned_30d_micro)}}</div><div class="l">{{ t('hubPage.earned30') }}</div></div>
                <div class="stat"><div class="n">{{hub.tool.health}}</div><div class="l">{{ t('hubPage.health') }}</div></div>
              </div>
              <div class="lbl">{{ t('hubPage.summary') }} <span class="muted">({{ t('hubPage.summarySub') }})</span></div>
              <p class="sub">{{hub.tool.summary}}</p>
              <div class="lbl">{{ t('hubPage.inputs') }}</div>
              <table><tr><th>{{ t('hubPage.thName') }}</th><th>{{ t('hubPage.thType') }}</th><th>{{ t('hubPage.thDefault') }}</th><th>{{ t('hubPage.thNote') }}</th></tr>
                <tr v-for="(v,k) in hub.tool.inputs" :key="k"><td><code>{{k}}</code></td><td>{{v.type}}<span v-if="v.max!==undefined"> ≤ {{v.max}}</span></td><td>{{v.default!==undefined?JSON.stringify(v.default): t('hubPage.required')}}</td><td class="muted">{{v.note||''}}</td></tr>
              </table>
              <div class="lbl" style="margin-top:12px">{{ t('hubPage.uses') }} <span class="muted">({{ t('hubPage.usesSub') }})</span></div>
              <p class="sub"><code v-for="u in hub.tool.uses" :key="u" style="margin-right:8px">{{u}}</code></p>
              <div class="lbl">{{ t('hubPage.output') }}</div>
              <p class="sub"><code>{{(hub.tool.output&&hub.tool.output.fields)?hub.tool.output.fields.join(', '):Object.keys(hub.tool.output||{}).join(', ')}}</code></p>
              <template v-if="hub.tool.data"><div class="lbl">{{ t('hubPage.data') }}</div>
              <p class="sub">{{hub.tool.data.rows.toLocaleString()}} {{ t('hubPage.rows') }} · {{(hub.tool.data.bytes/1024).toFixed(0)}} KB {{ t('hubPage.uploadedWithVersion') }}</p></template>
              <div class="lbl">{{ t('hubPage.callIt') }}</div>
              <pre style="white-space:pre-wrap;word-break:break-all">{{hubCallLine(hub.tool)}}
POST {{proxy}}/call/{{hub.tool.tool_id}}    X-Treg-Token · JSON body of inputs</pre>
              <p class="sub">{{ t('hubPage.filesReadOnly') }}(<code>treg hub publish .</code>) {{ t('hubPage.orAgent') }}(<code>hub_update</code>).</p>
            </template>

            <template v-if="hub.tab==='versions'">
              <p class="sub">{{ t('hubPage.newestLive') }}<code>@N</code>{{ t('hubPage.pinnedOld') }}</p>
              <table><tr><th>{{ t('hubPage.thVer') }}</th><th>{{ t('hubPage.thStatus') }}</th><th>{{ t('hubPage.thPublished') }}</th><th>{{ t('hubPage.thBy') }}</th><th>{{ t('hubPage.thCheck') }}</th><th>{{ t('hubPage.thHealth') }}</th></tr>
                <tr v-for="v in hubVersions(hub.tool.tool_id)" :key="v.version"><td>{{v.version}}</td><td>{{v.status}}</td><td>{{(v.created_at||'').slice(0,16).replace('T',' ')}}</td><td>{{v.created_by}}</td>
                  <td>{{v.check_result?v.check_result.status:'-'}}<span v-if="v.check_result&&v.check_result.charged_micro" class="muted"> · {{v.check_result.charged_micro}} µ$</span></td><td>{{v.health}}</td></tr>
              </table>
            </template>

            <template v-if="hub.tab==='price'">
              <!-- Display only. Pricing is a block in recipe.json with three modes and optional bounds,
                   so a form here would cover one mode and silently flatten the others. The maker's
                   agent edits the block and publishes; the check gates the new version. -->
              <div class="statgrid" style="margin:12px 0;grid-template-columns:repeat(auto-fit,minmax(180px,1fr))">
                <div class="stat"><div class="n sm">{{hub.tool.price_label}}</div><div class="l">{{ t('hubPage.yourPrice') }}</div></div>
                <div class="stat"><div class="n">{{hubRunCost(hub.tool)}}</div><div class="l">{{ hub.tool.price_samples ? t('hubPage.whatRunCost', { n: hub.tool.price_samples, run: t(hub.tool.price_samples===1 ? 'hubPage.runOne' : 'hubPage.runMany') }) : t('hubPage.noRunsYet') }}</div></div>
              </div>
              <p class="sub">{{hubPriceExplain(hub.tool)}} {{ t('hubPage.priceExplain') }}</p>
              <div class="lbl">{{ t('hubPage.pricingBlock') }}<span class="muted">({{ t('hubPage.version') }} {{hub.tool.version}})</span></div>
              <pre style="white-space:pre-wrap">{{JSON.stringify(hub.tool.pricing||{}, null, 2)}}</pre>
              <div class="lbl" style="margin-top:12px">{{ t('hubPage.changeIt') }}</div>
              <p class="sub">{{ t('hubPage.askAgent') }}<span class="mono">pricing</span>{{ t('hubPage.askAgent2') }}<span class="mono">@{{hub.tool.version}}</span>{{ t('hubPage.askAgent3') }}</p>
              <pre style="white-space:pre-wrap">{{hubPricePrompt(hub.tool)}}</pre>
              <button class="btn primary sm" @click="copyText(hubPricePrompt(hub.tool), t('hubPage.copyPrompt'))">Copy prompt for your agent</button>
            </template>

            <template v-if="hub.tab==='listing'">
              <p class="sub">{{ t('hubPage.listingLede') }}</p>
              <div style="margin:14px 0 4px">
                <div class="lbl">{{ t('hubPage.inCatalogSearch') }}</div>
                <p class="sub" style="margin:4px 0;max-width:70ch">
                  <b :class="{ok:hubListing(hub.tool)==='approved', warn:hubListing(hub.tool)==='rejected'}">{{hubListingWords(hub.tool)}}</b>
                  <template v-if="hubListing(hub.tool)==='rejected' && hub.tool.listing.reason">{{ t('hubPage.reason') }}{{hub.tool.listing.reason}}</template>
                  <template v-if="hubListing(hub.tool)==='requested' && hub.tool.listing.reason">{{ t('hubPage.lastRejected') }}{{hub.tool.listing.reason}}</template>
                </p>
                <p class="sub" style="margin:4px 0;max-width:70ch">
                  <template v-if="hubListing(hub.tool)==='approved' && hub.tool.listing.capability">{{ t('hubPage.besideProviders') }}<code>{{hub.tool.listing.capability}}</code>{{ t('hubPage.besideProviders2') }}</template>
                  <template v-else-if="hub.tool.capability">{{ t('hubPage.proposedJob') }}<code>{{hub.tool.capability}}</code>{{ t('hubPage.proposedJob2') }}</template>
                  <template v-else>{{ t('hubPage.noJobNamed') }}<code>"capability"</code>{{ t('hubPage.noJobNamed2') }}</template>
                </p>
                <p v-if="hub.tool.listing && hub.tool.listing.update" class="sub" style="margin:4px 0;max-width:70ch">
                  <template v-if="hub.tool.listing.update.state==='pending'"><b class="warn">{{ t('hubPage.updateWaits') }}</b>
                    <template v-if="hub.tool.listing.update.version"> {{ t('hubPage.version') }} {{hub.tool.listing.update.version}}</template><template v-if="hub.tool.listing.update.version && hub.tool.listing.update.pricing">{{ t('hubPage.updateAnd') }}</template>
                    <template v-if="hub.tool.listing.update.pricing">{{ t('hubPage.thePrice') }}${{hub.tool.listing.update.pricing.price_usd}}</template>{{ t('hubPage.callersKeep') }}</template>
                  <template v-else><b class="warn">{{ t('hubPage.updateRejected') }}</b> {{hub.tool.listing.update.reason}}{{/[.!?]$/.test(hub.tool.listing.update.reason)?'':'.'}}{{ t('hubPage.approvedStillServes') }}</template>
                </p>
                <button v-if="['none','rejected','unlisted'].includes(hubListing(hub.tool))" class="btn sm primary" :disabled="hub.flagSaving||!canRegister||hub.tool.status!=='live'" @click="setHubFlag('listed',true)">{{ t(hubListing(hub.tool)==='rejected' ? 'hubPage.askAgain' : hubListing(hub.tool)==='unlisted' ? 'hubPage.listAgain' : 'hubPage.askToList') }}</button>
                <button v-else class="btn sm" :disabled="hub.flagSaving||!canRegister" @click="setHubFlag('listed',false)">{{ t(hubListing(hub.tool)==='approved' ? 'hubPage.unlist' : 'hubPage.withdrawRequest') }}</button>
                <p class="sub" style="margin:6px 0 0;max-width:70ch">{{ t('hubPage.listedNote1') }}<code>catalog_search</code>{{ t('hubPage.listedNote2') }}</p>
              </div>
              <div style="margin:14px 0 4px">
                <label class="tgl" style="font-size:13.5px"><input type="checkbox" :checked="hub.tool.public_log!==false" :disabled="hub.flagSaving||!canRegister||hub.tool.status!=='live'" @change="setHubFlag('public_log',$event.target.checked)"/><span><b>{{ t('hubPage.publicRunLog') }}</b></span></label>
                <p class="sub" style="margin:4px 0 0 21px;max-width:70ch">{{ t('hubPage.runLogExplain') }}</p>
              </div>
              <p class="sub">{{ t('hubPage.fromTerminal') }}<code>treg hub list {{hub.tool.tool_id}}</code> · <code>treg hub unlist {{hub.tool.tool_id}}</code> · <code>treg hub log {{hub.tool.tool_id}} --public off</code></p>
            </template>

            <template v-if="hub.tab==='earnings'">
              <p v-if="!hub.earnings" class="sub">{{ t('hubPage.loading') }}</p>
              <template v-else>
                <div class="statgrid" style="margin:12px 0;grid-template-columns:repeat(auto-fit,minmax(150px,1fr))">
                  <div class="stat"><div class="n">{{money(hub.earnings.earned_micro)}}</div><div class="l">{{ t('hubPage.earned90') }}</div></div>
                  <div class="stat"><div class="n">{{hub.earnings.runs}}</div><div class="l">{{ t('hubPage.runsByOthers') }}</div></div>
                  <div class="stat"><div class="n">{{hub.earnings.by_day.reduce((a,d)=>a+d.ok,0)}} / {{hub.earnings.by_day.reduce((a,d)=>a+d.failed,0)}}</div><div class="l">{{ t('hubPage.okFailed') }}</div></div>
                </div>
                <p class="sub"><a :href="'/hub/tools/'+encodeURIComponent(hub.tool.tool_id)+'/earnings?days=90&format=csv'" target="_blank">{{ t('hubPage.downloadCsv') }}</a> · {{ t('hubPage.countsAmounts') }}</p>
                <table><tr><th>{{ t('hubPage.thDay') }}</th><th style="text-align:right">{{ t('hubPage.thRuns') }}</th><th style="text-align:right">{{ t('hubPage.thOK') }}</th><th style="text-align:right">{{ t('hubPage.thFailed') }}</th><th style="text-align:right">{{ t('hubPage.thEarned') }}</th></tr>
                  <tr v-for="d in hub.earnings.by_day" :key="d.day"><td>{{d.day}}</td><td style="text-align:right">{{d.runs}}</td><td style="text-align:right">{{d.ok}}</td><td style="text-align:right">{{d.failed}}</td><td style="text-align:right">{{money(d.earned_micro)}}</td></tr>
                </table>
              </template>
            </template>

            <template v-if="hub.tab==='runs'">
              <p class="sub">{{ t('hubPage.lastRuns') }}</p>
              <p v-if="!hub.health" class="sub">{{ t('hubPage.loading') }}</p>
              <table v-else><tr><th>{{ t('hubPage.thWhen') }}</th><th>{{ t('hubPage.thRun') }}</th><th>{{ t('hubPage.thKind') }}</th><th>{{ t('hubPage.thStatus') }}</th><th style="text-align:right">{{ t('hubPage.thSteps') }}</th><th style="text-align:right">{{ t('hubPage.thStepsCost') }}</th><th style="text-align:right">{{ t('hubPage.thPrice') }}</th><th style="text-align:right">{{ t('hubPage.thMs') }}</th></tr>
                <template v-for="r in hub.health.runs" :key="r.run_id">
                  <tr class="act-row" @click="toggleHubRun(r)"><td>{{(r.at||'').slice(5,16).replace('T',' ')}}</td><td><code>{{r.run_id.slice(0,10)}}…</code></td><td>{{r.kind}}</td><td><span :class="{ok:r.status==='ok', warn:r.status!=='ok'}">{{r.status}}</span><span v-if="r.error" class="muted"> · {{r.error}}</span></td><td style="text-align:right">{{r.steps}}</td><td style="text-align:right">{{r.cost_micro}} µ$</td><td style="text-align:right">{{money(r.price_micro)}}</td><td style="text-align:right">{{r.ms}}</td></tr>
                  <tr v-if="hub.runOpen===r.run_id"><td colspan="8">
                    <div v-if="!r.detail" class="muted">{{ t('hubPage.loading') }}</div>
                    <div v-else style="font-size:12px;line-height:1.6">
                      <div><span class="muted">inputs</span> <code>{{JSON.stringify(r.detail.inputs)}}</code></div>
                      <div v-for="(s,i) in (r.detail.trace||[])" :key="i"><span class="muted">trace</span> wave {{s.wave}} · {{s.name}} · <code>{{s.call}}</code> · {{s.outcome}} {{s.status||''}} · {{s.cost_micro}} µ$ · {{s.key||''}} key · {{s.ms}} ms<span v-if="s.error" class="warn"> · {{String(s.error).slice(0,300)}}</span></div>
                      <div v-for="(l,i) in (r.detail.log||[])" :key="'l'+i"><span class="muted">log</span> {{l}}</div>
                      <div v-if="r.detail.error&&r.detail.error.message"><span class="muted">error</span> {{r.detail.error.error||''}} {{r.detail.error.message}}</div>
                    </div>
                  </td></tr>
                </template>
              </table>
            </template>

            <template v-if="hub.tab==='health'">
              <p v-if="!hub.health" class="sub">{{ t('hubPage.loading') }}</p>
              <template v-else>
                <div class="card" style="max-width:640px"><b :class="{ok:hub.health.health==='ok', warn:hub.health.health==='failing'}">{{hub.health.health}}</b>
                  <span class="muted"> · {{hub.health.fails_in_a_row}} {{ t('hubPage.failedInRow') }} · {{ t('hubPage.lastRun') }} {{(hub.health.last_run_at||'-').slice(0,16).replace('T',' ')}}</span>
                  <div v-if="hub.health.last_check" class="sub" style="margin-top:6px">{{ t('hubPage.lastCheck') }}{{hub.health.last_check.status}}<span v-if="hub.health.last_check.scheduled">{{ t('hubPage.scheduled') }}</span>{{ t('hubPage.at') }}{{(hub.health.last_check.checked_at||'').slice(0,16).replace('T',' ')}}<span v-if="hub.health.last_check.error"> · {{hub.health.last_check.error.error||''}} {{hub.health.last_check.error.message||''}}</span></div>
                </div>
                <p class="sub" style="margin-top:10px" v-html="t('hubPage.healthFailing')"></p>
              </template>
            </template>
          </template>
</template>

<style scoped>
/* the hub's state words (live / failing / an error line), on these pages only */
.ok{color:var(--green)} .warn{color:var(--amber)} p.err{color:var(--red)}
</style>
