<script>
import { useDashboard } from '../state/context'
import InfoTip from '../components/ui/InfoTip.vue'
import Money from '../components/ui/Money.vue'
import Avatar from '../components/ui/Avatar.vue'
import TeamShowcase from './team/TeamShowcase.vue'
import TeamAvatar from './team/TeamAvatar.vue'
import EnterpriseSSO from '../components/EnterpriseSSO.vue'
import { NO_KEY } from '../state/constants.js'
import stripeSlate from '../assets/stripe-wordmark-slate.svg'
import stripeWhite from '../assets/stripe-wordmark-white.svg'
// The new agent's check-in poll lives as long as this page (state/agents.js).
export default {
  components: { InfoTip, Money, Avatar, TeamShowcase, TeamAvatar, EnterpriseSSO },
  data: () => ({ NO_KEY, stripeSlate, stripeWhite, memberSsoReady: false }),
  setup: useDashboard,
  mounted() { this.resumeCredentialIssue(); this.resumeAgentPoll(); this.loadMemberSso() },
  watch: {
    activeOrgId() { this.loadMemberSso() },
    orgTab(tab) { if (tab === 'sso' && this.activeRole !== 'owner') this.loadMemberSso() },
  },
  methods: {
    async copyMemberSsoLink() {
      const url = new URL(`/auth/sso/${encodeURIComponent(this.activeOrg.slug)}/start`, location.origin).href
      this.orgMsg = await this.toClipboard(url) ? 'Employee sign-in link copied.' : 'Could not copy the sign-in link.'
    },
    async loadMemberSso() {
      this.memberSsoReady = false
      if (!this.activeOrgId || this.activeRole === 'owner') return
      const orgId = this.activeOrgId
      const status = await this.api(`/orgs/${orgId}/sso`).catch(() => null)
      if (this.activeOrgId !== orgId || this.activeRole === 'owner') return
      this.memberSsoReady = !!(status?.sso_ready && ['active', 'trialing', 'past_due'].includes(status.subscription_status))
      if (!this.memberSsoReady && this.orgTab === 'sso') this.orgTab = 'keys'
    },
  },
  beforeUnmount() { this.parkCredentialIssue() },
}
</script>

<template>

          <div class="tut-head">
            <Avatar v-if="activeOrg && activeOrg.avatar_url" :src="activeOrg.avatar_url" :name="activeName" :size="40" />
            <div><h1>Team: {{activeName}}<span v-if="isPersonal(activeOrg)" class="chip" style="margin-left:8px;vertical-align:middle">personal</span></h1>
              <p class="sub" style="margin:0">{{ t('team.youAre', { role: activeRole }) }} <span class="muted">{{ t('team.switchHint') }}</span></p>
              <button v-if="activeRole!=='owner' && memberSsoReady" class="btn sm" style="margin-top:8px" @click="copyMemberSsoLink">{{ t('team.copyCompanySso') }}</button></div>
          </div>
          <!-- settings for the ACTIVE team (switching lives in the sidebar) -->
          <div v-if="activeOrg" style="margin-top:20px">
            <div class="tabs" style="margin:4px 0 16px">
              <button v-if="canAdmin" :class="{active:orgTab==='members'}" @click="orgTab='members'">{{ t('team.tabMembers') }}</button>
              <button :class="{active:orgTab==='keys'}" @click="orgTab='keys'; loadApiKeys(); loadApiKeySpend()">{{ t('team.tabKeys') }}</button>
              <button v-if="canAdmin" :class="{active:orgTab==='projects'}" @click="orgTab='projects'">{{ t('team.tabProjects') }}</button>
              <button v-if="canAdmin" :class="{active:orgTab==='policy'}" @click="orgTab='policy'">{{ t('team.tabPolicy') }}</button>
              <button v-if="canAdmin" :class="{active:orgTab==='billing'}" @click="orgTab='billing'">{{ t('team.tabBilling') }}</button>
              <button v-if="canAdmin" :class="{active:orgTab==='showcase'}" @click="orgTab='showcase'">{{ t('team.tabShowcase') }}</button>
              <button v-if="activeRole==='owner' || memberSsoReady" :class="{active:orgTab==='sso'}" @click="orgTab='sso'">{{ t('team.tabSso') }}</button>
              <button :class="{active:orgTab==='danger'}" @click="orgTab='danger'; resetRenameForm()">{{ t('team.tabSettings') }}</button>
            </div>
            <p v-if="!canAdmin && !['keys','danger','sso'].includes(orgTab)" class="sub" style="margin-bottom:12px">{{ t('team.adminOnlyHint') }}</p>
            <p v-if="myUsage && myUsage.cap>=0" class="sub" style="margin:-6px 0 12px" v-html="t('team.usageToday', { used: '<b>'+myUsage.used_today+'</b>', cap: '<b>'+myUsage.cap+'</b>' })"></p>
            <div v-if="orgErr" class="banner">{{orgErr}}</div>
            <div v-if="orgMsg" class="tut-notice" style="margin-bottom:12px;display:flex;justify-content:space-between;gap:12px;align-items:flex-start">
              <span>{{orgMsg}}</span><button class="btn sm ico" @click="orgMsg=''" :aria-label="t('team.dismiss')">✕</button>
            </div>
            <EnterpriseSSO v-if="orgTab==='sso' && (activeRole==='owner' || memberSsoReady)" :org-id="activeOrg.org_id" :slug="activeOrg.slug" :owner="activeRole==='owner'" />
            <div v-if="credentialIssue" class="tut-notice" role="status" style="margin-bottom:12px">
              <template v-if="credentialIssue.status==='pending'">{{ t('team.keyReqInProgress') }}</template>
              <template v-else-if="credentialIssue.status==='checking'">{{ t('team.checkingKey') }}</template>
              <template v-else-if="credentialIssue.error">{{credentialIssue.error}}</template>
              <template v-else>{{ t('team.saveKeyHint') }}</template>
              <button v-if="credentialIssue.status==='held'" class="btn sm" @click="resumeCredentialIssue">{{ t('team.checkKeyStatus') }}</button>
              <button v-if="credentialIssue.status==='ready' && orgTab!==(credentialIssue.type==='agent'?'members':'keys')" class="btn sm" @click="orgTab=credentialIssue.type==='agent'?'members':'keys'">{{ t('team.openIssuedKey') }}</button>
              <button v-if="['failed','unavailable'].includes(credentialIssue.status)" class="btn sm" @click="dismissCredentialIssue">{{ t('team.dismiss') }}</button>
            </div>

            <template v-if="canAdmin && orgTab==='members'">
              <div v-if="agentErr" class="banner" style="margin-top:8px">{{agentErr}}</div>
          <!-- the token is shown ONCE: make that unmissable -->
          <div v-if="newAgent || snipAgent" class="card" style="margin-top:16px" :style="newAgent?'border-color:var(--accent)':''">
            <div class="lbl" style="margin-top:0;display:flex;align-items:center;gap:10px">
              <template v-if="newAgent">{{ t('team.tokenFor', {name: newAgent.name}) }}</template>
              <template v-else>{{ t('team.howToUse', {name: snipAgent.name}) }}</template>
              <button v-if="!newAgent" class="btn sm" style="margin-left:auto" @click="snipAgent=null">{{ t('team.close') }}</button>
            </div>
            <p v-if="newAgent && newAgent.rotated" class="tut-notice" style="margin:2px 0 10px" v-html="t('team.prevKeyStopped', { name: '<b>'+newAgent.name+'</b>' })"></p>
            <p v-if="newAgent" class="sub" style="margin:2px 0 10px" v-html="t('team.saveKeyBody', { name: '<b>'+newAgent.name+'</b>' })"></p>
            <p v-if="newAgent" class="sub" style="margin:2px 0 10px">
              <span v-if="agentConnected" class="chip ok" style="margin-left:8px">{{ t('team.connectedAs', {name: newAgent.name}) }}</span>
              <span v-else class="muted" style="margin-left:8px">{{ t('team.waitingCheckin') }}</span></p>
            <p v-else class="sub" style="margin:2px 0 10px">{{ t('team.serverStoresHash') }} <button class="btn sm" :disabled="!!credentialIssue" @click="rotateAgent(snipAgent,true)">⟳ {{ t('team.rotateFill') }}</button> <span class="muted">{{ t('team.oldTokenStops') }}</span></p>
            <div v-if="newAgent" class="field">
              <input :value="newAgent.token" readonly style="font-family:var(--mono)" @focus="$event.target.select()"/>
              <button class="btn primary" @click="copy(newAgent.token,'agenttok')">{{copied==='agenttok' ? t('common.copied') : t('team.copy')}}</button>
              <button class="btn" @click="dismissCredentialIssue">{{newAgent.rotated ? t('team.iveUpdated', {name:newAgent.name}) : t('team.done')}}</button>
            </div>
            <!-- a bare token is a dead end: hand over the paste-ready thing, like the Tools snippets do -->
            <div class="tabs" style="margin:14px 0 8px">
              <button :class="{active:agentSnip==='prompt'}" @click="agentSnip='prompt'">{{ t('team.giveToAgent') }}</button>
              <button :class="{active:agentSnip==='env'}" @click="agentSnip='env'">{{ t('team.environment') }}</button>
            </div>
            <div class="lc-codewrap">
              <button class="lc-cp" @click="copy(agentSnippet,'agentsnip')">{{copied==='agentsnip' ? t('common.copied') : t('team.copy')}}</button>
              <pre style="max-height:220px;overflow:auto">{{agentSnippet}}</pre>
            </div>
            <p class="sub" style="margin:6px 0 0;font-size:11.5px">{{ t('team.putWherever') }}</p>
          </div>


              <div class="lbl" style="margin-top:14px">{{ t('team.members') }}</div>
              <p class="sub" style="margin:-2px 0 8px;font-size:12px">{{ t('team.dailyCapHint') }}</p>
              <p class="sub" style="margin:-2px 0 8px;font-size:12px" v-html="t('team.toolsHint')"></p>
              <table>
                <tr><th>{{ t('team.thEmail') }}</th><th>{{ t('team.thRole') }}</th><th style="text-align:right">{{ t('team.thToday') }}</th><th>{{ t('team.thDailyCap') }}</th><th>{{ t('team.thTools') }}</th><th>{{ t('team.thLocalRun') }}</th><th></th></tr>
                <!-- An empty roster under its header read as "no members" until the request answered. -->
                <tr v-if="!orgMembersLoaded"><td colspan="7" class="muted">{{ t('team.loadingMembers') }}</td></tr>
                <template v-for="m in rosterMembers" :key="m.key">
                <tr v-if="m.is_observed">
                  <td><span style="opacity:.45">↳</span> <b>{{m.client}}</b> <span class="chip" :title="t('team.detectedTitle')">{{ t('team.detected') }}</span>
                    <div class="muted" style="font-size:11px">{{ t('team.runsAs', {member: short(m.member)}) }}</div></td>
                  <td><span class="muted" style="font-size:12px">—</span></td>
                  <td style="text-align:right" class="muted">{{m.used_today}}</td>
                  <td colspan="3"><span class="muted" style="font-size:12px">{{ t('team.calls30d', {n: m.calls_30d, when: when(m.last_seen)}) }}</span></td>
                  <td style="text-align:right"><button class="btn sm" @click="promoteObserved(m)" :title="t('team.scopeAgentTitle')">{{ t('team.scopeAgent') }}</button></td>
                </tr>
                <tr v-else>
                  <td>
                    <template v-if="m.is_agent"><span style="opacity:.45">↳</span> <b>{{m.name}}</b> <span class="chip" :title="m.email">agent</span>
                      <div class="muted" style="font-size:11px">{{m.created_by?('owned by '+short(m.created_by)):'machine identity'}}</div>
                      <div v-if="confirmAgent==='rotate-'+m.user_id" class="sub" style="font-size:11px;margin-top:5px;max-width:360px"><b>Its current key will stop immediately.</b> The next card shows the replacement once so you can update {{m.name}}.</div>
                      <div v-if="confirmAgent==='revoke-'+m.user_id" class="sub" style="font-size:11px;margin-top:5px;max-width:360px"><b>This removes the agent and revokes all its keys.</b> Activity stays for audit; restoring it means creating and configuring it again.</div></template>
                    <span v-else style="display:inline-flex;gap:8px;align-items:center"><Avatar :src="m.avatar_url" :name="m.email" :size="22" round />{{m.email}}</span>
                  </td>
                  <td>
                    <select v-if="isOwner" class="msel" :value="m.role" @change="setRole(m,$event.target.value)">
                      <option v-for="r in ['viewer','member','admin','owner']" :key="r" :value="r">{{r}}</option>
                    </select>
                    <span v-else class="role" :class="m.role">{{m.role}}</span>
                  </td>
                  <td style="text-align:right" class="muted">{{m.used_today}}</td>
                  <td><input class="msel" type="number" min="0" step="1" style="width:78px" :value="capField(m.daily_call_cap)" placeholder="No limit" @change="setCap(m,$event.target.value)" :aria-label="'Daily cap for '+(m.email||m.name)" title="Empty = no limit"/></td>
                  <td>
                    <span v-if="m.role==='owner'" class="chip">{{ t('team.all') }}</span>
                    <button v-else class="btn sm" :class="{active:editAccess===m.user_id}" @click="openAccess(m)" :title="m.tool_access===null?t('team.allToolsOpt'):t('team.nTools',{n:m.tool_access.length})">{{m.tool_access===null ? t('team.all') : t('team.nTools', {n: m.tool_access.length})}} ▾</button>
                  </td>
                  <td>
                    <label class="tgl" :title="m.role==='owner'?t('team.ownerAlwaysLocal'):(m.local_run_enabled?t('team.localOn'):t('team.localOff'))">
                      <input type="checkbox" :checked="m.local_run_enabled" :disabled="m.role==='owner'" @change="setLocalRun(m,$event.target.checked)"/>
                      <span>{{m.local_run_enabled ? t('team.on') : t('team.off')}}</span>
                    </label>
                  </td>
                  <td style="text-align:right;white-space:nowrap">
                    <template v-if="m.is_agent">
                      <span class="row-actions">                      <button class="btn sm" @click="showAgentSetup(m)" :title="t('team.setupTitle')">{{ t('team.setup') }}</button>
                      <button class="btn sm" :disabled="!!credentialIssue" :class="{danger:confirmAgent==='rotate-'+m.user_id}" @click="rotateAgent(m)" :title="t('team.rotateFill')">{{confirmAgent==='rotate-'+m.user_id ? t('team.confirmRotate') : t('team.rotate')}}</button>
                      <button class="btn sm" :class="{danger:confirmAgent==='revoke-'+m.user_id}" @click="revokeAgent(m)">{{confirmAgent==='revoke-'+m.user_id ? t('team.confirmRevoke') : t('team.revoke')}}</button></span>
                    </template>
                    <button v-else-if="m.role!=='owner'" class="btn sm" :class="{danger:confirmRemove===m.user_id}" @click="removeMember(m)">{{confirmRemove===m.user_id ? t('team.confirmRemove') : t('team.remove')}}</button>
                  </td>
                </tr>
                <tr v-if="!m.is_observed && editAccess===m.user_id">
                  <td colspan="7" style="background:color-mix(in srgb,var(--accent) 5%,transparent)">
                    <div style="padding:6px 2px">
                      <div class="sub" style="margin-bottom:6px" v-html="t('team.toolsSkillsHint', { email: '<b>'+m.email+'</b>' })"></div>
                      <div v-if="!accessNames.length" class="muted" style="font-size:12px">{{ t('team.noToolsYet') }}</div>
                      <div style="display:flex;flex-wrap:wrap;gap:6px 16px">
                        <label v-for="n in accessNames" :key="n" class="tgl" style="min-width:150px">
                          <input type="checkbox" v-model="accessDraft[n]"/><span>{{n}}</span>
                        </label>
                      </div>
                      <template v-if="projects.length">
                        <div class="sub" style="margin:12px 0 6px" v-html="t('team.projectsHint', { email: '<b>'+m.email+'</b>' })"></div>
                        <div style="display:flex;flex-wrap:wrap;gap:6px 16px">
                          <label v-for="p in projects" :key="p.id" class="tgl" style="min-width:150px">
                            <input type="checkbox" v-model="projDraft[p.id]"/><span>{{p.name}}</span>
                          </label>
                        </div>
                      </template>
                      <p v-else class="sub" style="margin:12px 0 0;font-size:12px">{{ t('team.scopeTipLead') }}<a href="#" @click.prevent="orgTab='projects'">{{ t('team.scopeTipLink') }}</a>{{ t('team.scopeTipTail') }}</p>
                      <div style="margin-top:10px;display:flex;gap:8px">
                        <button class="btn sm primary" @click="saveAccess(m)">{{ t('team.saveAccess') }}</button>
                        <button class="btn sm" @click="editAccess=null">{{ t('team.cancel') }}</button>
                        <button class="btn sm" @click="setAllAccess(true)">{{ t('team.checkAll') }}</button>
                        <button class="btn sm" @click="setAllAccess(false)">{{ t('team.uncheckAll') }}</button>
                      </div>
                    </div>
                  </td>
                </tr>
                </template>
              </table>

              <div class="lbl" style="margin-top:22px;display:flex;align-items:center;gap:10px">{{ t('team.addToTeam') }}
                <button v-if="!isPersonal(activeOrg)" class="btn sm" :class="{active:showInvite}" @click="showInvite=!showInvite; if(showInvite)showAddAgent=false">{{ t('team.addMember') }}</button>
                <button class="btn sm" :class="{active:showAddAgent}" @click="openAddAgent()">{{ t('team.addAgent') }}</button></div>
              <p class="sub" style="margin:-2px 0 8px;font-size:12px" v-html="t('team.memberVsAgent')"></p>
              <div v-show="showAddAgent">
          <div class="lbl" style="margin-top:18px">{{ t('team.newAgent') }}</div>
          <p v-if="promoteHint" class="sub" style="margin:-2px 0 6px;font-size:12px;color:var(--accent)">{{promoteHint}}</p>
          <div class="field" style="max-width:620px">
            <input v-model="agentName" placeholder="ci-bot" @keyup.enter="createAgent"/>
            <select v-model="agentRole" class="msel"><option>viewer</option><option>member</option><option v-if="isOwner">admin</option></select>
            <input :value="capField(agentCap)" @input="agentCap=capValue($event.target.value)" type="number" min="0" step="1" class="msel" style="width:96px" placeholder="No limit" :aria-label="t('team.dailyCallCap')" :title="t('team.dailyCallCap')"/>
            <button class="btn primary" @click="createAgent" :disabled="agentBusy||!!credentialIssue||!agentAccessMode">{{agentBusy ? '…' : t('team.create')}}</button>
          </div>
          <div style="max-width:620px;margin:4px 0 8px">
            <div style="display:flex;gap:16px;align-items:center;flex-wrap:wrap">
              <span class="sub" style="font-size:12px"><b>{{ t('team.toolsLabel') }}</b></span>
              <label class="tgl"><input type="radio" value="all" v-model="agentAccessMode"/><span>{{ t('team.allToolsOpt') }}</span></label>
              <label class="tgl"><input type="radio" value="choose" v-model="agentAccessMode"/><span>{{ t('team.chooseTools') }}</span></label>
              <span v-if="!agentAccessMode" class="sub" style="font-size:11px;color:var(--accent)">{{ t('team.chooseAccessFirst') }}</span>
            </div>
            <div v-if="agentAccessMode==='choose'" style="display:flex;flex-wrap:wrap;gap:6px 16px;margin-top:7px">
              <span v-if="!accessNames.length" class="muted" style="font-size:12px">{{ t('team.noToolsAgent') }}</span>
              <label v-for="n in accessNames" :key="n" class="tgl" style="min-width:150px"><input type="checkbox" v-model="agentToolSel[n]"/><span>{{n}}</span></label>
            </div>
          </div>
          <div v-if="projects.length" style="max-width:620px;margin:4px 0 0;display:flex;gap:6px 16px;flex-wrap:wrap;align-items:center">
            <span class="sub" style="font-size:12px">{{ t('team.projectsAllChecked') }}</span>
            <label v-for="p in projects" :key="p.id" class="tgl"><input type="checkbox" v-model="agentProjSel[p.id]"/><span>{{p.name}}</span></label>
          </div>
          <p class="sub" style="margin:-2px 0 0;font-size:12px">{{ t('team.emptyCapHint') }}</p>

              </div>
              <template v-if="!isPersonal(activeOrg)">
              <div v-show="showInvite">
              <div class="field" style="max-width:560px">
                <input v-model="inviteEmail" type="email" placeholder="teammate@email.com" @keyup.enter="sendInvite"/>
                <select v-model="inviteRole" class="msel"><option>viewer</option><option>member</option><option v-if="isOwner">admin</option></select>
                <button class="btn primary" @click="sendInvite" :disabled="orgBusy">{{orgBusy ? '…' : t('team.invite')}}</button>
              </div>
              <div style="max-width:560px;margin:-4px 0 4px;display:flex;gap:16px;align-items:center;flex-wrap:wrap">
                <label class="tgl"><input type="radio" :checked="!inviteCustomize" @change="inviteCustomize=false"/><span>{{ t('team.allToolsOpt') }}</span></label>
                <label class="tgl"><input type="radio" :checked="inviteCustomize" @change="openInviteCustomize()"/><span>{{ t('team.customize') }}</span></label>
                <label class="tgl"><input type="checkbox" v-model="inviteLocalRun"/><span>{{ t('team.localRunsAllowed') }}</span></label>
              </div>
              <div v-if="inviteCustomize" style="max-width:560px;margin-bottom:8px">
                <div class="sub" style="font-size:12px;margin-bottom:4px">{{ t('team.toolsMemberMayUse') }}</div>
                <div v-if="!tools.length" class="muted" style="font-size:12px">{{ t('team.noToolsYet') }}</div>
                <div style="display:flex;flex-wrap:wrap;gap:6px 16px">
                  <label v-for="n in accessNames" :key="n" class="tgl" style="min-width:150px"><input type="checkbox" v-model="inviteToolSel[n]"/><span>{{n}}</span></label>
                </div>
              </div>
              <div v-if="lastInvite" class="tut-notice" style="max-width:560px">
                <span v-html="t('team.inviteSent', { email: '<b>'+lastInvite.email+'</b>', role: lastInvite.role })"></span>
                <div style="display:flex;gap:8px;align-items:center;margin-top:6px"><code class="mono" style="word-break:break-all;font-size:11px">{{lastInvite.code}}</code><button class="btn sm" @click="copy(lastInvite.code)">{{copied ? t('common.copied') : t('team.copy')}}</button></div>
              </div>

              <div class="lbl" style="margin-top:18px">{{ t('team.pendingInvites') }}</div>
              <table v-if="orgInvites.length">
                <tr><th>{{ t('team.thEmail') }}</th><th>{{ t('team.thRole') }}</th><th>{{ t('team.thInvitedBy') }}</th><th>{{ t('team.thExpires') }}</th><th></th></tr>
                <tr v-for="inv in orgInvites" :key="inv.id">
                  <td>{{inv.email}}</td><td><span class="role" :class="inv.role">{{inv.role}}</span></td>
                  <td class="muted">{{short(inv.invited_by)}}</td><td class="muted">{{inv.expires_at?until(inv.expires_at):t('team.never')}}</td>
                  <td style="text-align:right"><button class="btn sm" @click="revokeInvite(inv)">{{ t('team.revoke') }}</button></td>
                </tr>
              </table>
              <p v-else class="sub">{{ t('team.noPendingInvites') }}</p>
              </div>
              </template>
            </template>

            <!-- API KEYS tab. Members see their own keys; admins see the full team inventory. -->
            <template v-if="orgTab==='keys'">
              <div class="tut-head" style="align-items:flex-end;margin-bottom:14px"><div><div class="lbl">{{ t('team.apiKeys') }}</div>
                <p class="sub" style="margin:2px 0 0">{{ t('team.apiKeysHint') }}</p></div></div>
              <div v-if="keyErr" class="banner">{{keyErr}}</div>
              <div v-if="keyMsg" class="tut-notice" style="margin-bottom:12px;display:flex;justify-content:space-between;gap:12px;align-items:flex-start">
                <span>{{keyMsg.text}}</span><span style="white-space:nowrap"><button v-if="keyMsg.agent" class="btn sm" @click="orgTab='members'; keyMsg=null">{{ t('team.openMembers') }}</button><button class="btn sm ico" @click="keyMsg=null" :aria-label="t('team.dismiss')">✕</button></span>
              </div>
              <div v-if="newApiKey" class="card" style="border-color:var(--accent);margin-bottom:16px">
                <div class="lbl"><template v-if="newApiKey.kind==='default_human'">{{ t('team.defaultKeyRotated') }}</template><template v-else-if="newApiKey.assigned_type==='agent'">{{ t('team.newKeyFor', {name: newApiKey.assigned_name}) }}</template><template v-else>{{ t('team.copyNow', {name: newApiKey.name}) }}</template></div>
                <p v-if="newApiKey.kind==='default_human'" class="tut-notice" style="margin:2px 0 10px">{{ t('team.prevKeyStoppedClients') }}</p>
                <p v-if="newApiKey.assigned_type==='agent' && newApiKey.rotated" class="tut-notice" style="margin:2px 0 10px" v-html="t('team.prevKeyHidden', { name: '<b>'+newApiKey.assigned_name+'</b>' })"></p>
                <p class="sub" style="margin:2px 0 10px"><template v-if="newApiKey.kind==='default_human'">{{ t('team.keyRevealable') }}</template><template v-else>{{ t('team.serverStoresHashKey') }}<template v-if="newApiKey.assigned_type==='agent'">{{ t('team.anyoneHolding', { name: newApiKey.assigned_name }) }}</template></template></p>
                <div class="field"><input :value="newApiKey.secret" readonly class="mono" @focus="$event.target.select()"/><button class="btn primary" @click="copy(newApiKey.secret,'managedkey')">{{copied==='managedkey' ? t('common.copied') : t('team.copy')}}</button><button class="btn" @click="dismissCredentialIssue">{{newApiKey.assigned_type==='agent' ? t('team.iveUpdated', {name:newApiKey.assigned_name}) : t('team.done')}}</button></div>
                <p v-if="newApiKey.kind==='default_human'" class="sub" style="margin:6px 0 0;font-size:11.5px">{{ t('team.cliLoginHint') }}</p>
                <template v-if="newApiKey.assigned_type==='agent'">
                  <p class="sub" style="margin:6px 0 0"><span v-if="agentConnected" class="chip ok">{{ t('team.connectedAs', {name: newApiKey.assigned_name}) }}</span><span v-else class="muted">{{ t('team.waitingCheckin') }}</span></p>
                  <div class="tabs" style="margin:14px 0 8px"><button :class="{active:agentSnip==='prompt'}" @click="agentSnip='prompt'">{{ t('team.giveToAgent') }}</button><button :class="{active:agentSnip==='env'}" @click="agentSnip='env'">{{ t('team.environment') }}</button></div>
                  <div class="lc-codewrap"><button class="lc-cp" @click="copy(agentSnippet,'agentsnip')">{{copied==='agentsnip' ? t('common.copied') : t('team.copy')}}</button><pre style="max-height:220px;overflow:auto">{{agentSnippet}}</pre></div>
                  <p class="sub" style="margin:6px 0 0;font-size:11.5px">{{ t('team.replaceToken', { name: newApiKey.assigned_name }) }}</p>
                </template>
              </div>
              <div v-if="activeRole!=='viewer'" class="field" style="max-width:620px;margin-bottom:18px"><input v-model="keyName" :class="{'field-invalid':keyNameInvalid}" :aria-invalid="keyNameInvalid" placeholder="New key name" maxlength="80" @input="keyNameInvalid=false" @keyup.enter="createApiKey"/><button class="btn primary" :disabled="keyBusy||!!credentialIssue" @click="createApiKey">{{keyBusy ? '…' : t('team.createKey')}}</button></div>
              <template v-for="group in apiKeyGroups" :key="group.identity">
                <div class="lbl" style="margin-top:16px">{{group.name}} <span class="chip">{{group.type}}</span><span v-if="group.type==='agent' && group.name!==group.identity" class="muted mono" style="margin-left:8px;text-transform:none">{{group.identity}}</span></div>
                <table class="key-table"><tr><th>{{ t('team.thKey') }}</th><th>{{ t('team.thStatus') }}</th><th style="text-align:right" :title="t('team.spent30Title')">{{ t('team.thSpent30') }}</th><th>{{ t('team.thCreated') }}</th><th>{{ t('team.thLastUsed') }}</th><th></th></tr>
                  <tr v-for="k in group.rows" :key="k.id">
                    <td class="key-identity"><input v-if="editKey===k.id" v-model="editKeyName" maxlength="80" class="msel" @keyup.enter="renameApiKey(k)"/><template v-else><div class="key-primary"><span v-if="group.type==='human' && k.assigned_type==='agent'" class="muted" aria-hidden="true">↳</span><b>{{group.type==='human' && k.assigned_type==='agent'?k.assigned_name:k.name}}</b><span class="chip">{{keyKind(k.kind)}}</span></div><div class="key-meta mono">{{maskedKey(k)}}</div></template>
                    </td>
                    <td><span class="badge" :class="k.state==='active'?'ok':'invalid'">{{k.state}}</span></td>
                    <td class="key-spend"><Money v-if="keySpend(k)" :micro="keySpend(k).spent_micro" /><span v-else-if="apiKeySpend && !apiKeySpend.ready" class="muted" :title="t('team.spendPreparing')">{{ t('team.preparing') }}</span><span v-else class="muted">—</span></td>
                    <td class="muted">{{k.created_at?when(k.created_at):t('team.unknown')}}</td><td class="muted">{{k.last_used_at?when(k.last_used_at):t('team.never')}}</td>
                    <td style="text-align:right;white-space:nowrap"><span v-if="editKey===k.id" class="row-actions"><button class="btn sm primary" @click="renameApiKey(k)">{{ t('team.save') }}</button><button class="btn sm" @click="editKey=null">{{ t('team.cancel') }}</button></span><span v-else class="row-actions">
                      <button class="btn sm" @click="showKeyActivity(k)">{{ t('team.activity') }}</button><button v-if="k.can_rotate" class="btn sm" :disabled="!!credentialIssue" @click="requestKeyAction(k,'rotate')">{{ t('team.rotate') }}</button><button v-if="keyHasMore(k)" class="btn sm ico" aria-haspopup="menu" :aria-expanded="keyMenu&&keyMenu.key.id===k.id" :aria-label="t('team.moreActions', {name: k.name})" @click.stop="toggleKeyMenu(k,$event)">⋮</button>
                    </span></td>
                  </tr>
                </table>
              </template>
              <template v-if="apiKeySpend && apiKeySpend.ready && apiKeySpend.unattributed && apiKeySpend.unattributed.spent_micro && apiKeys.length">
                <div class="lbl" style="margin-top:16px">{{NO_KEY.title}} <InfoTip :title="NO_KEY.title" :text="NO_KEY.text" /></div>
                <table class="key-table"><tr><td class="key-identity"><span class="muted">{{ t('team.chargesNoKey') }}</span></td><td class="key-spend"><Money :micro="apiKeySpend.unattributed.spent_micro" /></td></tr></table>
              </template>
              <p v-if="apiKeySpend && !apiKeySpend.ready && apiKeys.length" class="sub">{{ t('team.spendPreparing') }}</p>
              <p v-if="!keyBusy && !apiKeys.length" class="sub">{{ t('team.noKeysAvailable') }}</p>
            </template>

            <!-- BILLING. Balance + top-ups + auto top-up for the ACTIVE team. Admin-gated like the
                 rest of the team tabs. Hidden entirely when the deployment has no Stripe key
                 (self-hosters don't sell balance) - `billing.configured` says so. -->
            <template v-if="canAdmin && orgTab==='billing'">
              <div v-if="billing" style="margin-top:4px">
                <div class="card" style="padding:16px">
                  <div style="display:flex;gap:12px;align-items:flex-start;flex-wrap:wrap">
                    <div style="flex:1;min-width:220px">
                      <div class="lbl">{{ t('team.balance') }}</div>
                      <div style="font-size:28px;font-weight:700;color:var(--accent);font-family:var(--mono)">{{money(billing.balance_micro)}}</div>
                    </div>
                    <!-- Stripe's hosted portal: card, billing address, tax ID and the invoice archive.
                         Hidden until the team has a Stripe customer, which its first payment creates. -->
                    <button v-if="billing.portal" class="btn sm" :disabled="billingBusy" @click="openPortal()"
                            :title="t('team.manageBillingTitle')">
                      {{billingBusy ? t('team.opening') : t('team.manageBilling')}}
                    </button>
                  </div>
                  <p v-if="!billing.configured" class="sub" style="margin:12px 0 0">{{ t('team.topupsNotConfigured') }}</p>

                  <template v-if="billing.configured">
                    <div style="margin-top:12px">
                      <!-- A team that arrived through someone's link does not know a bonus exists.
                           This is the one screen where saying so changes what they do, and the
                           MINIMUM is the part that matters: the first preset ($5) is below it, so
                           without this the most-clicked button silently forfeits the reward. -->
                      <div v-if="billing.referral_offer" style="margin-top:8px;padding:9px 12px;font-size:12.5px;
                           border:1px solid var(--green);border-radius:8px;
                           background:color-mix(in srgb,var(--green) 12%,transparent)">
                        <!-- The referrer is MASKED (`j•••@domain`): a referral link is public, so
                             the full address would be published to every stranger who signs up
                             through an influencer's link. The domain is what a real friend
                             recognises. Falls back to "to treg" if we somehow have no address. -->
                        {{ t('team.referralInvited') }}
                        <template v-if="billing.referral_offer.referrer_masked">{{ t('team.referralBy', { masked: '<b>'+billing.referral_offer.referrer_masked+'</b>' }) }}</template>
                        <template v-else>{{ t('team.referralToTreg') }}</template>
                        {{ t('team.referralAdd') }}
                        <!-- Once they have paid something, ask for the REMAINDER. Repeating the
                             full amount reads as though the money they already added did not
                             count, and it does: the threshold is cumulative. -->
                        <b>{{money(billing.referral_offer.remaining_micro)}}</b>
                        <template v-if="billing.referral_offer.topped_up_micro"> {{ t('team.referralMore') }}</template>
                        <template v-else> {{ t('team.referralOrMore') }}</template>
                        <!-- "straight away" is load-bearing. The referee has no Referrals page, so
                             the balance is their ONLY feedback; promising a bonus without saying
                             when is what made a correct payout look like a failure. -->
                        <span v-html="t('team.referralPayout', { referred: '<b>'+money(billing.referral_offer.referred_micro)+'</b>', referrer: money(billing.referral_offer.referrer_micro), days: billing.referral_offer.hold_days })"></span>
                      </div>
                      <!-- The amounts live in a modal (openTopup), not inline: choosing a size,
                           seeing the bonus it earns and deciding on auto top-up are one decision,
                           and the mandate text has to sit next to the Pay button it authorizes. -->
                      <button class="btn primary" :disabled="billingBusy" @click="openTopup()">{{ t('team.topUp') }}</button>
                    </div>

                    <!-- `no_card` is not a failure: consent was recorded (usually from the top-up
                         modal) and the policy arms itself when a payment saves a card. Showing it in
                         the red "switched itself off" banner made an abandoned Checkout look broken. -->
                    <p v-if="billing.autotopup.disabled_reason==='no_card'" class="sub" style="margin:14px 0 0">
                      {{ t('team.autoTopupNoCard') }}
                    </p>
                    <div v-else-if="billing.autotopup.disabled_reason" class="banner"
                         :class="{'auth-warning':billing.autotopup.disabled_reason==='authentication_required'}"
                         style="margin:14px 0 0">
                      <template v-if="billing.autotopup.disabled_reason==='stripe_unconfirmed'">
                        {{ t('team.autoTopupStripeUnconfirmed') }}
                      </template>
                      <template v-else-if="billing.autotopup.disabled_reason==='authentication_required'">
                        {{ t('team.autoTopupAuthRequired') }}
                        <button class="btn primary" style="margin-left:10px" :disabled="billingBusy" @click="openTopup()">{{ t('team.makeManualTopup') }}</button>
                      </template>
                      <template v-else>
                        {{ t('team.autoTopupOff', { reason: billing.autotopup.disabled_reason }) }}
                      </template>
                    </div>
                    <div v-else-if="billing.autotopup.enabled&&billing.autotopup.cap_reached" class="banner" style="margin:14px 0 0">
                      {{ t('team.autoTopupCapReached', { limit: money(billing.autotopup.monthly_cap_micro) }) }}
                      <button class="btn primary" style="margin-left:10px" :disabled="billingBusy" @click="openTopup()">{{ t('team.makeManualTopup') }}</button>
                    </div>
                    <div style="margin-top:16px;border-top:1px solid var(--line);padding-top:14px">
                      <label style="display:flex;gap:10px;align-items:center;cursor:pointer">
                        <span class="tswitch"><input type="checkbox" :checked="billing.autotopup.enabled||autoOpen" :disabled="billingBusy" @change="autoToggled"/><span class="knob"></span></span>
                        <span class="lbl" style="margin:0">{{ t('team.autoTopup') }}</span>
                        <span v-if="billing.card_on_file" class="sub saved-card-label">
                          <svg class="saved-card-check" viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="m4 10 4 4 8-8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                          <span>{{ t('team.cardSavedWith') }}</span>
                          <img class="stripe-wordmark stripe-wordmark-slate" :src="stripeSlate" alt="Stripe">
                          <img class="stripe-wordmark stripe-wordmark-white" :src="stripeWhite" alt="Stripe">
                        </span>
                      </label>
                      <p class="sub" style="margin:8px 0 0">
                        <template v-if="billing.autotopup.enabled">{{ t('team.autoTopupOn', { amount: money(billing.autotopup.amount_micro), threshold: money(billing.autotopup.threshold_micro), perHour: billing.autotopup.per_hour, spent: money(billing.autotopup.month_spend_micro), limit: money(billing.autotopup.monthly_cap_micro) }) }}
                          <a href="#" @click.prevent="autoOpen=!autoOpen;autoConsent=false">{{autoOpen ? t('team.cancel') : t('team.autoTopupEdit')}}</a></template>
                        <template v-else>{{ t('team.autoTopupOffDesc') }}</template>
                      </p>
                      <!-- The same panel edits a running policy (Edit link above) and arms a new one:
                           either way the numbers change, so the mandate is re-agreed and re-stamped. -->
                      <div v-if="autoOpen" style="margin-top:12px;background:var(--panel2);border:1px solid var(--line);border-radius:var(--rb);padding:12px 14px;max-width:560px">
                        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
                          <span class="sub" style="margin:0">{{ t('team.add') }}</span>
                          <input class="msel" style="width:70px" type="number" min="5" v-model.number="autoAmount"/>
                          <span class="sub" style="margin:0">{{ t('team.below') }}</span>
                          <input class="msel" style="width:70px" type="number" min="5" v-model.number="autoThreshold"/>
                          <span class="sub" style="margin:0">, {{ t('team.upTo') }}</span>
                          <input class="msel" style="width:56px" type="number" min="1" max="60" v-model.number="autoPerHour"/>
                          <span class="sub" style="margin:0">{{ t('team.timesPerHour') }}</span>
                        </div>
                        <label style="display:flex;gap:8px;align-items:flex-start;margin-top:12px;cursor:pointer">
                          <input type="checkbox" v-model="autoConsent" style="margin-top:3px"/>
                          <!-- The mandate text. Not decoration: an off-session charge with no recorded
                               agreement to THESE numbers is an unauthorized charge under PSD2/SCA. -->
                          <span class="sub" style="margin:0">{{ t('team.autoMandate', { amount: autoAmount, threshold: autoThreshold, perHour: autoPerHour }) }}</span>
                        </label>
                        <div style="margin-top:12px">
                          <button class="btn primary" :disabled="!autoConsent||billingBusy" @click="setAuto(true)">{{billingBusy ? '…' : (billing.autotopup.enabled ? t('team.save') : t('team.turnOnAuto'))}}</button>
                        </div>
                      </div>
                    </div>

                    <div style="margin-top:16px;border-top:1px solid var(--line);padding-top:14px">
                      <div class="lbl">{{ t('team.paymentHistory') }}</div>
                      <p class="sub" style="margin:8px 0 0">{{ t('team.paymentHistoryHint') }}</p>
                      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:12px" role="group" aria-label="Filter payments">
                        <button v-for="filter in [{id:'all',label:t('team.filterAll')},{id:'manual',label:t('team.filterManual')},{id:'auto',label:t('team.filterAuto')},{id:'subscription',label:t('team.filterSubs')}]"
                                :key="filter.id" class="btn sm" :class="{primary:bhistFilter===filter.id}"
                                :aria-pressed="bhistFilter===filter.id" @click="setBillingHistoryFilter(filter.id)">{{filter.label}}</button>
                      </div>
                      <p v-if="bhist.loading" class="sub" style="margin:8px 0 0">{{ t('team.loading') }}</p>
                      <p v-else-if="bhist.error" class="sub" style="margin:8px 0 0">{{ t('team.couldNotLoadHistory') }} <button class="btn sm" @click="loadBillingHistory()">{{ t('team.tryAgain') }}</button></p>
                      <p v-else-if="!bhist.items.length" class="sub" style="margin:8px 0 0">{{ t('team.noPayments') }}</p>
                      <template v-else>
                        <!-- Top-up amounts come from our ledger; subscription invoices come from Stripe. -->
                        <div style="overflow-x:auto">
                        <table style="width:100%;min-width:440px;max-width:700px;margin-top:8px;border-collapse:collapse">
                          <thead><tr class="sub" style="text-align:left">
                            <th scope="col" style="padding:8px 10px 8px 0;font-weight:500">{{ t('team.thDate') }}</th>
                            <th scope="col" style="padding:8px 10px 8px 0;font-weight:500">{{ t('team.thAmount') }}</th>
                            <th scope="col" style="padding:8px 10px 8px 0;font-weight:500">{{ t('team.thPayment') }}</th>
                            <th scope="col" style="padding:8px 0;text-align:right;font-weight:500">{{ t('team.thDocuments') }}</th>
                          </tr></thead>
                          <tbody>
                          <tr v-for="i in bhist.items" :key="i.id" style="border-top:1px solid var(--line)">
                            <td style="padding:8px 10px 8px 0;white-space:nowrap">{{bhistDate(i.created_at)}}</td>
                            <td style="padding:8px 10px 8px 0;font-family:var(--mono);white-space:nowrap">{{money(i.amount_micro)}}</td>
                            <td style="padding:8px 10px 8px 0;white-space:nowrap" class="sub">
                              {{i.kind==='subscription' ? t('team.subSso') : i.kind==='auto' ? t('team.subAuto') : t('team.subManual')}} ·
                              <span :style="i.status==='paid'?'color:var(--green)':''">{{i.status==='paid' ? t('team.paid') : i.status==='open' ? t('team.paymentDue') : (i.status || t('team.pending2'))}}</span>
                              <span v-if="i.kind==='subscription'&&i.number" class="muted"> · {{i.number}}</span>
                              <span v-if="i.bonus_micro" style="color:var(--green)"> +{{money(i.bonus_micro)}} {{ t('team.bonus') }}</span>
                            </td>
                            <td style="padding:8px 0;text-align:right;white-space:nowrap">
                              <a v-if="i.invoice_pdf||i.hosted_invoice_url" :href="i.invoice_pdf||i.hosted_invoice_url" target="_blank" rel="noopener">{{ t('team.invoice') }}</a>
                              <span v-if="(i.invoice_pdf||i.hosted_invoice_url)&&i.receipt_url" class="muted"> · </span>
                              <a v-if="i.receipt_url" :href="i.receipt_url" target="_blank" rel="noopener">{{ t('team.receipt') }}</a>
                              <span v-if="!(i.invoice_pdf||i.hosted_invoice_url||i.receipt_url)" class="muted">—</span>
                            </td>
                          </tr>
                          </tbody>
                        </table>
                        </div>
                      </template>
                      <p v-if="!bhist.ok && bhist.items.length" class="sub" style="margin:8px 0 0">{{ t('team.someDocUnavailable') }}</p>
                      <p v-if="!bhist.invoicesOk" class="sub" style="margin:8px 0 0">{{ t('team.subsInvoiceUnavailable') }} <button class="btn sm" @click="loadBillingHistory()">{{ t('team.tryAgain') }}</button></p>
                      <div v-if="!bhist.error && (bhistPage>0 || bhist.nextCursor)" style="display:flex;justify-content:flex-end;gap:8px;align-items:center;margin-top:14px">
                        <button class="btn sm" :disabled="bhistPage===0||bhist.loading" @click="previousBillingHistoryPage()">{{ t('team.previous') }}</button>
                        <span class="sub" style="margin:0">{{ t('team.page', { n: bhistPage+1 }) }}</span>
                        <button class="btn sm" :disabled="!bhist.nextCursor||bhist.loading" @click="nextBillingHistoryPage()">{{ t('team.next') }}</button>
                      </div>
                    </div>
                  </template>

                </div>
              </div>
              <p v-else class="sub">{{ t('team.loading') }}</p>
            </template>

            <template v-if="canAdmin && orgTab==='projects'">
              <div class="lbl" style="margin-top:14px">{{ t('team.projects') }}</div>
              <p class="sub" style="margin:-2px 0 8px;font-size:12px">{{ t('team.projectsHint2') }}</p>
              <div class="field" style="max-width:560px">
                <input v-model="projectName" placeholder="Apollo" @keyup.enter="createProject"/>
                <button class="btn primary" @click="createProject" :disabled="projBusy">{{projBusy ? '…' : t('team.addProject')}}</button>
              </div>
              <p v-if="!projects.length" class="muted" style="font-size:12px;margin-top:8px">{{ t('team.noProjects') }}</p>
              <table v-else style="margin-top:8px">
                <tr><th>{{ t('team.thProject') }}</th><th>{{ t('team.thSlug') }}</th><th style="text-align:right">{{ t('team.thTools') }}</th><th></th></tr>
                <template v-for="p in projects" :key="p.id">
                <tr>
                  <td><b>{{p.name}}</b></td>
                  <td class="muted" style="font-family:var(--mono);font-size:12px">{{p.slug}}</td>
                  <td style="text-align:right">
                    <button class="btn sm" :class="{active:editProj===p.id}" @click="openProjTools(p)">{{ t('team.nProjectTools', { n: p.tool_count, s: p.tool_count===1?'':'s' }) }} ▾</button>
                  </td>
                  <td style="text-align:right">
                    <button class="btn sm" :class="{danger:confirmProj===p.id}" @click="deleteProject(p)" :title="t('team.deleteHint', { n: p.tool_count })">{{confirmProj===p.id ? t('team.confirmDelete') : t('team.delete')}}</button>
                  </td>
                </tr>
                <tr v-if="editProj===p.id">
                  <td colspan="4" style="background:color-mix(in srgb,var(--accent) 5%,transparent)">
                    <div style="padding:6px 2px">
                      <div class="sub" style="margin-bottom:6px" v-html="t('team.toolsInProject', { name: '<b>'+p.name+'</b>' })"></div>
                      <div v-if="!tools.length" class="muted" style="font-size:12px">{{ t('team.noToolsYet') }}</div>
                      <div style="display:flex;flex-wrap:wrap;gap:6px 16px">
                        <label v-for="t in tools" :key="t.id" class="tgl" style="min-width:190px">
                          <input type="checkbox" v-model="projToolDraft[t.id]"/><span>{{t.name}}</span>
                          <span v-if="t.project_id && t.project_id!==p.id" class="chip" style="margin-left:4px" :title="'currently in '+projName(t.project_id)">{{projName(t.project_id)}}</span>
                        </label>
                      </div>
                      <div style="margin-top:10px;display:flex;gap:8px">
                        <button class="btn sm primary" @click="saveProjTools(p)" :disabled="projToolBusy">{{projToolBusy ? '…' : t('team.save2')}}</button>
                        <button class="btn sm" @click="editProj=null">{{ t('team.cancel') }}</button>
                      </div>
                    </div>
                  </td>
                </tr>
                </template>
              </table>

            </template>

            <!-- POLICY tab -->
            <template v-if="canAdmin && orgTab==='policy'">
              <div class="lbl" style="margin-top:14px">{{ t('team.policy') }}</div>
              <p class="sub" style="margin:-2px 0 8px;font-size:12px">{{ t('team.policyHint') }}</p>
              <div class="field" style="max-width:720px;flex-wrap:wrap">
                <input v-model="denyForm.host" :placeholder="t('team.phHost')" style="min-width:190px"/>
                <input v-model="denyForm.path_prefix" :placeholder="t('team.phPath')" style="min-width:140px"/>
                <select v-model="denyForm.method" class="msel"><option value="">{{ t('team.anyMethod') }}</option><option>GET</option><option>POST</option><option>PUT</option><option>PATCH</option><option>DELETE</option></select>
                <select v-model="denyForm.user_id" class="msel" :title="t('team.whoApplies')">
                  <option :value="null">{{ t('team.wholeTeam') }}</option>
                  <option v-for="m in rosterMembers.filter(x=>!x.is_observed)" :key="m.user_id" :value="m.user_id">{{m.is_agent?('agent: '+(m.name||m.email)):m.email}}</option>
                </select>
                <select v-if="projects.length" v-model="denyForm.project_id" class="msel" :title="t('team.whoApplies')">
                  <option :value="null">{{ t('team.anyProject') }}</option>
                  <option v-for="p in projects" :key="p.id" :value="p.id">{{p.name}}</option>
                </select>
                <input v-model="denyForm.note" :placeholder="t('team.phWhy')" style="min-width:170px"/>
                <button class="btn primary" @click="addDeny" :disabled="denyBusy">{{denyBusy ? '…' : t('team.block')}}</button>
              </div>
              <p v-if="!denyRules.length" class="muted" style="font-size:12px;margin-top:8px">{{ t('team.noRules') }}</p>
              <table v-else style="margin-top:8px">
                <tr><th>{{ t('team.thMethod') }}</th><th>{{ t('team.thHost') }}</th><th>{{ t('team.thPath') }}</th><th>{{ t('team.thAppliesTo') }}</th><th v-if="projects.length">{{ t('team.thProject') }}</th><th>{{ t('team.thNote') }}</th><th></th></tr>
                <tr v-for="r in denyRules" :key="r.id">
                  <td><span class="chip">{{r.method||t('team.any')}}</span></td>
                  <td style="font-family:var(--mono);font-size:12px">{{r.host||t('team.any')}}</td>
                  <td style="font-family:var(--mono);font-size:12px">{{r.path_prefix||t('team.any')}}</td>
                  <td>{{r.scope==='org' ? t('team.wholeTeam') : (denyWho(r.user_id))}}</td>
                  <td v-if="projects.length">{{r.project_id?projName(r.project_id):t('team.any')}}</td>
                  <td class="muted" style="font-size:12px">{{r.note}}</td>
                  <td style="text-align:right"><button class="btn sm" :class="{danger:confirmDeny===r.id}" @click="removeDeny(r)">{{confirmDeny===r.id ? t('team.confirmRemove') : t('team.remove')}}</button></td>
                </tr>
              </table>

              <!-- Tool-level argv blocks — the OTHER deny layer, surfaced read-only so the whole
                   "what is blocked" picture lives on one screen. -->
              <template v-if="cliDeny.length">
                <div class="lbl" style="margin-top:22px">{{ t('team.perToolCliBlocks') }} <span class="chip" style="margin-left:6px">{{ t('team.readOnly') }}</span></div>
                <p class="sub" style="margin:-2px 0 8px;font-size:12px">{{ t('team.cliBlocksHint') }}</p>
                <table>
                  <tr><th>{{ t('team.thTools') }}</th><th>{{ t('team.thBlockedPatterns') }}</th></tr>
                  <tr v-for="c in cliDeny" :key="c.tool">
                    <td><b>{{c.tool}}</b><span v-if="!c.enabled" class="chip" style="margin-left:6px" :title="t('team.localOff')">{{ t('team.off') }}</span></td>
                    <td><span v-for="pat in c.patterns" :key="pat.pattern" class="chip" style="margin:2px 6px 2px 0;font-family:var(--mono);font-size:11px" :title="pat.source==='skill' ? t('team.fromSkill') : t('team.fromCatalog')">{{pat.pattern}}<span class="muted" style="margin-left:4px">· {{pat.source}}</span></span></td>
                  </tr>
                </table>
              </template>
            </template>

            <!-- SHOWCASE: the team's apps on the public showcase (apply, edit, withdraw) -->
            <TeamShowcase v-if="canAdmin && orgTab==='showcase'" />

            <!-- TEAM SETTINGS: just the danger zone (new/join/switch team live in the sidebar
                 picker). Visible to every role — leaving a team is self-service, not admin. -->
            <template v-if="orgTab==='danger'">
            <!-- DAILY SPEND CAP. A team-level setting, so it lives here rather than under Billing.
                 It was invisible entirely before this, which meant a team first met it as an
                 unexplained 429; and it matters MOST when auto top-up is on, because a balance that
                 refills itself is no longer a ceiling and this becomes the only thing bounding a
                 runaway agent. `capCfg` is loaded by loadBilling(), which runs on every Team-page
                 load — NOT per tab — so it is populated by the time this renders.
                 NB the name: `orgSettings` is already a METHOD on this component (the ⚙ in the team
                 picker), and data and methods share one namespace. -->
            <div v-if="capCfg" style="margin-top:18px;border-top:1px solid var(--line);padding-top:14px">
                  <span class="lbl" style="margin:0">{{ t('team.dailySpendLimit') }}</span>
                  <p class="sub" style="margin:4px 0 8px;font-size:12px">{{ t('team.dailySpendHint') }}</p>
                  <div class="field" style="max-width:560px">
                    <input v-model="capUsd" type="number" min="0" step="0.5" :placeholder="t('team.noLimit')" style="max-width:140px"/>
                    <button class="btn primary" :disabled="capBusy" @click="saveCap">{{capBusy ? '…' : t('team.save')}}</button>
                    <span class="sub" style="margin:0">
                      {{ t('team.usdDay', { now: capCfg.daily_cap_micro ? money(capCfg.daily_cap_micro) : t('team.noLimit') }) }}<template v-if="!capCfg.daily_cap_set_by_team"> {{ t('team.ourDefault') }}</template>
                    </span>
                  </div>
                  <p v-if="capErr" class="banner" style="margin:10px 0 0">{{capErr}}</p>
                  <p class="muted" style="font-size:12px;margin-top:8px">{{ t('team.anyAmount') }}</p>
                </div>

                <!-- THE ARCHIVE. A team-level privacy setting (docs/context/architecture/archive.md,
                     "Opting out"): off means no call is answered from or recorded into treg's archive.
                     Erasing what was stored is a separate act (team deletion, or on request). -->
                <div v-if="capCfg" style="margin-top:22px;border-top:1px solid var(--line);padding-top:14px">
                  <span class="lbl" style="margin:0">{{ t('team.archive') }}</span>
                  <p class="sub" style="margin:4px 0 8px;font-size:12px">{{ t('team.archiveHint') }}</p>
                  <div class="field" style="max-width:560px;align-items:center">
                    <label class="tgl" :title="!canAdmin ? t('team.adminOnlyTitle') : (capCfg.archive ? t('team.archiveOn') : t('team.archiveOff'))">
                      <input type="checkbox" :checked="capCfg.archive" :disabled="archiveBusy || !canAdmin" @change="setArchive($event.target.checked)"/>
                      <span>{{capCfg.archive ? t('team.on') : t('team.off')}}</span>
                    </label>
                    <span v-if="!canAdmin" class="sub" style="margin:0">{{ t('team.adminsChange') }}</span>
                  </div>
                  <p v-if="archiveErr" class="banner" style="margin:10px 0 0">{{archiveErr}}</p>
                </div>

                <!-- PER-TAG BUDGETS. What a team reselling treg sets on ITS OWN customers. Only
                     DECLARED dimensions are enforced on the call path, so the key is a picker over
                     those rather than a free-text box — the API refuses a limit on anything else
                     precisely because a stored-but-unenforced budget looks like protection and isn't. -->
                <div v-if="capCfg" style="margin-top:22px;border-top:1px solid var(--line);padding-top:14px">
                  <span class="lbl" style="margin:0">{{ t('team.perCustomerLimits') }}</span>
                  <p class="sub" style="margin:4px 0 8px;font-size:12px">{{ t('team.perCustomerHint') }}</p>
                  <div class="field" style="max-width:680px;flex-wrap:wrap">
                    <!-- Every tag the team SENDS, not only the ones already budgeted. Setting a
                         limit declares the dimension, so offering only the declared list made the
                         common path a hidden two-step: you can see `feature` in Usage, so you expect
                         to be able to cap it. -->
                    <select class="msel" v-model="budDim" style="max-width:160px">
                      <option v-for="k in budDims" :key="k" :value="k">{{k}}</option>
                    </select>
                    <input v-model="budVal" placeholder="cust_8123 — blank = default for all" style="max-width:230px"/>
                    <input v-model="budDaily" type="number" min="0" step="0.5" placeholder="USD/day" style="max-width:120px"/>
                    <button class="btn primary" :disabled="budBusy" @click="saveBudget()">{{budBusy ? '…' : (budVal ? t('team.setLimit') : t('team.setDefault'))}}</button>
                  </div>
                  <p v-if="budErr" class="banner" style="margin:10px 0 0">{{budErr}}</p>
                  <template v-for="dim in (capCfg.budget_dims||[])" :key="dim">
                    <table style="margin-top:10px">
                      <tr><th>{{dim}}</th><th style="text-align:right">{{ t('team.thDailyLimit') }}</th><th>{{ t('team.thStatus') }}</th><th></th></tr>
                      <!-- The default first: everything under it is an exception to it. Rendered even
                           when unset, so "no limit" is something you can SEE rather than infer from
                           an empty table. -->
                      <tr>
                        <td><b>{{ t('team.everyDim', { dim }) }}</b> <span class="muted">{{ t('team.default') }}</span></td>
                        <td style="text-align:right">{{defaultFor(dim)?fmtCap(defaultFor(dim)):t('team.noLimit')}}</td>
                        <td><span class="muted">—</span></td>
                        <td style="text-align:right"><button v-if="defaultFor(dim)" class="btn sm" @click="removeBudget(defaultFor(dim))">{{ t('team.clear') }}</button></td>
                      </tr>
                      <tr v-for="b in overridesFor(dim)" :key="b.val">
                        <td style="padding-left:22px"><span class="chip">{{b.val}}</span></td>
                        <!-- EFFECTIVE, never a dash: an override with no cap really is unlimited, and
                             showing "—" would hide that it is exempt from the default. -->
                        <td style="text-align:right">{{fmtCap(b)}}</td>
                        <td><span class="badge" :class="b.status==='blocked'?'invalid':'ok'">{{b.status}}</span></td>
                        <td style="text-align:right;white-space:nowrap">
                          <button class="btn sm" @click="toggleBlock(b)">{{b.status==='blocked' ? t('team.unblock') : t('team.block')}}</button>
                          <button class="btn sm" @click="removeBudget(b)">{{ t('team.remove') }}</button>
                        </td>
                      </tr>
                      <tr v-if="!overridesFor(dim).length"><td colspan="4" class="muted" style="font-size:12px">{{ t('team.noExceptions', { dim }) }}</td></tr>
                    </table>
                  </template>
                </div>


            <TeamAvatar v-if="canAdmin" />

            <!-- TEAM NAME + SLUG. Admin+. The old slug stays an alias server-side, so copied keys,
                 ~/.treg and MCP pins keep working; the CLI just needs `treg org use <new-slug>`. -->
            <div v-if="canAdmin && !isPersonal(activeOrg)" style="margin-top:18px;border-top:1px solid var(--line);padding-top:14px">
              <span class="lbl" style="margin:0">{{ t('team.teamNameSlug') }}</span>
              <p class="sub" style="margin:4px 0 8px;font-size:12px">
                {{ t('team.nameSlugHint', { slug: renameSlug.trim()||activeSlugNow }) }}
              </p>
              <div class="field" style="max-width:560px">
                <input v-model="renameName" :placeholder="t('team.teamName')" maxlength="80" style="max-width:220px"/>
                <input v-model="renameSlug" :placeholder="t('team.slug')" maxlength="40" style="max-width:180px"/>
                <button class="btn primary" :disabled="renameBusy || !renameDirty" @click="renameOrg">{{renameBusy ? '…' : t('team.save')}}</button>
              </div>
              <p v-if="renameErr" class="sub" style="color:var(--red);margin:4px 0 0;font-size:12px">{{renameErr}}</p>
            </div>

            <template v-if="!isPersonal(activeOrg)">
            <div class="lbl" style="margin-top:14px;color:var(--red)">{{ t('team.dangerZone') }}</div>
            <div style="display:flex;gap:22px;flex-wrap:wrap;align-items:flex-start">
              <div>
                <button class="btn sm" :class="{danger:confirmLeave}" @click="leaveOrg">{{confirmLeave ? t('team.confirmLeave') : t('team.leaveOrg')}}</button>
                <a v-if="confirmLeave" href="#" @click.prevent="confirmLeave=false" class="sub" style="margin-left:8px;font-size:12px">{{ t('team.cancel2') }}</a>
              </div>
              <div v-if="isOwner" class="field" style="margin:0">
                <input v-model="confirmDel" :placeholder="t('team.typeToDelete', { slug: activeSlugNow })" style="min-width:230px"/>
                <button class="btn sm danger" :disabled="confirmDel!==activeSlugNow" @click="deleteOrg">{{ t('team.deleteOrg') }}</button>
              </div>
            </div>
            </template>
            <p v-else class="sub" style="margin-top:14px;font-size:12px">{{ t('team.personalCannotLeave') }}</p>
            </template>
          </div>

</template>

<style>
.saved-card-label { display:inline-flex; align-items:center; gap:5px; margin-left:auto; white-space:nowrap; }
.saved-card-check { width:15px; height:15px; color:var(--green); flex:none; }
.stripe-wordmark { width:38px; height:auto; display:block; }
.stripe-wordmark-slate { display:none; }
[data-theme="light"] .stripe-wordmark-slate { display:block; }
[data-theme="light"] .stripe-wordmark-white { display:none; }
</style>
