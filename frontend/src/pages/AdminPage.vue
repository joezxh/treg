<script>
import { useDashboard } from '../state/context'
export default { setup: useDashboard }
</script>

<template>

          <h1>{{ t('admin.title') }}</h1>
          <p class="sub">{{ t('admin.sub') }}</p>
          <div class="statgrid" v-if="adminStats"><div class="stat"><div class="n">{{adminStats.totals.users}}</div><div class="l">{{ t('admin.users') }}</div></div><div class="stat"><div class="n">{{adminStats.totals.orgs}}</div><div class="l">{{ t('admin.orgs') }}</div></div><div class="stat"><div class="n">{{adminStats.totals.tools}}</div><div class="l">{{ t('admin.tools') }}</div></div><div class="stat"><div class="n">{{adminStats.totals.calls}}</div><div class="l">{{ t('admin.calls') }}</div></div><div class="stat"><div class="n">{{adminStats.calls.success_rate==null?'-':Math.round(adminStats.calls.success_rate*100)+'%'}}</div><div class="l">{{ t('admin.successRate') }}</div></div></div>

          <template v-if="admHub.on">
            <div class="grp" style="margin:0 0 8px">{{ t('admin.hubListingRequests') }}</div>
            <div class="tabs" style="margin:0 0 8px">
              <button v-for="s in ['requested','approved','rejected']" :key="s" :class="{active:admHub.state===s}" @click="loadAdminHub(s)">{{ t('admin.hubState_'+s) }}</button>
            </div>
            <p v-if="!admHub.rows.length" class="sub">{{ t('admin.noneState', { state: t('admin.hubState_'+admHub.state) }) }}</p>
            <table v-else>
              <tr><th>{{ t('admin.thTool') }}</th><th>{{ t('admin.thPrice') }}</th><th>{{ t('admin.thCheck') }}</th><th>{{ t('admin.thAsked') }}</th><th></th></tr>
              <tr v-for="r in admHub.rows" :key="r.tool_id">
                <td><b>{{r.tool_id}}</b><span v-if="r.version" class="muted"> v{{r.version}} · {{r.kind}}</span>
                  <div class="sub" style="margin:2px 0 0;max-width:52ch">{{r.live ? r.summary : t('admin.noLiveVersion') }}</div>
                  <div v-if="r.reason" class="sub" style="margin:2px 0 0">{{ t('admin.reason') }}{{r.reason}}</div>
                  <div v-if="r.own_tools && r.own_tools.length" class="sub" style="margin:2px 0 0">Own tools: <span v-for="o in r.own_tools" :key="o.name"><code>{{o.name}}</code> → {{o.base_url}} </span></div>
                  <details v-if="r.script || r.steps" style="margin:4px 0 0"><summary class="sub">{{ t('admin.readThe') }} {{ t(r.script ? 'admin.script' : 'admin.steps') }}</summary><pre class="code">{{r.script || JSON.stringify(r.steps, null, 2)}}</pre></details>
                  <div class="sub" style="margin:2px 0 0">{{ t('admin.job') }}<input v-if="admHub.state!=='approved'" v-model="admHub.cap[r.tool_id]" :placeholder="r.proposed_capability||t('admin.capabilityNone')" style="width:190px" aria-label="Capability to approve"/><code v-else>{{r.capability||t('admin.capabilityNone')}}</code>
                    <span v-if="admHub.state!=='approved' && r.proposed_capability" class="muted">{{ t('admin.proposed') }}{{r.proposed_capability_description}} ({{r.proposed_capability_providers}}{{ t('admin.providers') }})</span></div></td>
                <td class="muted">{{r.price_label||'-'}}</td>
                <td class="muted">{{r.check||'-'}}</td>
                <td class="muted">{{r.requested_by}}<br>{{(r.requested_at||'').slice(0,10)}}</td>
                <td style="text-align:right;white-space:nowrap">
                  <input v-if="admHub.state!=='rejected'" v-model="admHub.reason[r.tool_id]" :placeholder="t('admin.rejectReasonPlaceholder')" style="width:160px" aria-label="Reason to reject"/>
                  <button v-if="admHub.state!=='approved'" class="btn sm primary" :disabled="admHub.busy===r.tool_id || !r.live" @click="admHubDecide(r,'approve')" style="margin-left:6px">{{ t('admin.approve') }}</button>
                  <button v-if="admHub.state!=='rejected'" class="btn sm" :disabled="admHub.busy===r.tool_id" @click="admHubDecide(r,'reject')" style="margin-left:6px">{{ admHub.state==='approved' ? t('admin.takeBack') : t('admin.reject') }}</button>
                </td>
              </tr>
            </table>
            <div class="grp" style="margin:18px 0 8px">{{ t('admin.updatesWaiting') }} <span class="muted">{{ t('admin.listedTools') }}</span></div>
            <p v-if="!admHub.updates.length" class="sub">{{ t('admin.noneWaiting') }}</p>
            <table v-else>
              <tr><th>{{ t('admin.thTool') }}</th><th>{{ t('admin.thServesNow') }}</th><th>{{ t('admin.thWouldReplace') }}</th><th></th></tr>
              <tr v-for="u in admHub.updates" :key="'u'+u.tool_id">
                <td><b>{{u.tool_id}}</b></td>
                <td class="sub">v{{u.now&&u.now.version}} · {{u.now&&u.now.price_label}}<div style="max-width:40ch">{{u.now&&u.now.summary}}</div></td>
                <td class="sub"><template v-if="u.new">v{{u.new.version}} · {{u.new.price_label}} · check {{u.new.check}}<div style="max-width:40ch">{{u.new.summary}}</div>
                    <div v-if="u.now && JSON.stringify(u.now.uses)!==JSON.stringify(u.new.uses)">uses: {{u.new.uses.join(', ')}}</div></template>
                  <div v-if="u.new_price_usd!=null"><b>{{ t('admin.newPrice') }}${{u.new_price_usd}}</b></div>
                  <div v-if="u.own_tools && u.own_tools.length" class="sub">Own tools: <span v-for="o in u.own_tools" :key="o.name"><code>{{o.name}}</code> → {{o.base_url}} </span></div>
                  <details v-if="u.code_diff" style="margin:4px 0 0"><summary class="sub">{{ t('admin.readChanged') }}</summary><pre class="code">{{u.code_diff}}</pre></details>
                  <div v-if="u.fields_lost && u.fields_lost.length" class="warn"><b>{{ t('admin.noLongerReturns') }}</b> {{u.fields_lost.join(', ')}} <span class="muted">{{ t('admin.filled') }}</span></div></td>
                <td style="text-align:right;white-space:nowrap">
                  <input v-model="admHub.reason['u:'+u.tool_id]" :placeholder="t('admin.rejectReasonPlaceholder')" style="width:160px" aria-label="Reason to reject the update"/>
                  <button class="btn sm primary" :disabled="admHub.busy===u.tool_id" @click="admHubUpdate(u,'approve')" style="margin-left:6px">{{ t('admin.approve') }}</button>
                  <button class="btn sm" :disabled="admHub.busy===u.tool_id" @click="admHubUpdate(u,'reject')" style="margin-left:6px">{{ t('admin.reject') }}</button>
                </td>
              </tr>
            </table>
            <div style="height:22px"></div>
          </template>

          <div class="grp" style="margin:0 0 8px">{{ t('admin.allOrgs') }}</div>
          <table v-if="adminOrgs.length">
            <tr><th>{{ t('admin.thOrg') }}</th><th>{{ t('admin.thMembers') }}</th><th>{{ t('admin.thTools') }}</th><th>{{ t('admin.thStatus') }}</th><th></th></tr>
            <tr v-for="o in adminOrgs" :key="o.id">
              <td><b>{{o.name}}</b></td><td>{{o.members}}</td><td>{{o.tools}}</td>
              <td><span class="badge" :class="o.suspended?'invalid':'ok'">{{o.suspended?t('admin.suspended'):t('admin.active')}}</span></td>
              <td style="text-align:right;white-space:nowrap">
                <button class="btn sm" @click="admSuspendOrg(o)" :disabled="adminBusy">{{o.suspended?t('admin.unsuspend'):t('admin.suspend')}}</button>
                <button class="btn sm" :class="{danger:confirmAdmOrg===o.id}" @click="admDeleteOrg(o)" style="margin-left:6px">{{confirmAdmOrg===o.id?t('admin.confirm'):t('admin.delete')}}</button>
              </td>
            </tr>
          </table>

          <div class="grp" style="margin:22px 0 8px">{{ t('admin.allUsers') }}</div>
          <table v-if="adminUsers.length">
            <tr><th>{{ t('admin.thEmail') }}</th><th>{{ t('admin.thOrgs') }}</th><th>{{ t('admin.thFlags') }}</th><th></th></tr>
            <tr v-for="u in adminUsers" :key="u.id">
              <td>{{u.email}}<span v-if="u.email===me" class="chip" style="margin-left:6px">{{ t('admin.you') }}</span></td>
              <td class="muted">{{u.orgs.length}}</td>
              <td>
                <span v-if="u.is_superadmin" class="badge ok">{{ t('admin.superAdmin') }}</span>
                <span v-if="u.suspended" class="badge invalid" style="margin-left:4px">{{ t('admin.suspended') }}</span>
                <span v-if="!u.is_superadmin && !u.suspended" class="muted">-</span>
              </td>
              <td style="text-align:right;white-space:nowrap">
                <template v-if="u.email!==me">
                  <button class="btn sm" @click="admGrant(u)" :disabled="adminBusy">{{u.is_superadmin?t('admin.revokeAdmin'):t('admin.makeAdmin')}}</button>
                  <button class="btn sm" @click="admSuspendUser(u)" :disabled="adminBusy" style="margin-left:6px">{{u.suspended?t('admin.unsuspend'):t('admin.suspend')}}</button>
                  <button class="btn sm" :class="{danger:confirmAdmUser===u.id}" @click="admDeleteUser(u)" style="margin-left:6px">{{confirmAdmUser===u.id?t('admin.confirm'):t('admin.delete')}}</button>
                </template>
                <span v-else class="muted">{{ t('admin.dashYou') }}</span>
              </td>
            </tr>
          </table>

</template>

<style scoped>
.warn{color:var(--amber)}
.code{max-height:320px;overflow:auto;font-size:12px;white-space:pre;background:var(--bg2, rgba(127,127,127,.08));padding:8px;border-radius:6px;max-width:60ch}
</style>
