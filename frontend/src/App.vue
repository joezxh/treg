<script>
import controller from './state/controller.js'
import { pages, dialogs } from './views'
import SignedOutPage from './components/SignedOutPage.vue'
import BrandMark from './components/BrandMark.vue'
import PublicNavigation from './components/PublicNavigation.vue'
import LandingNavigation from './components/LandingNavigation.vue'
import DashboardNavigation from './components/DashboardNavigation.vue'
import SignInDialog from './components/SignInDialog.vue'
// The shell (navigation, sign-in) is bundled with the entry; pages and dialogs load on demand (views.ts).
const {
  catalog: CatalogPage, connections: ConnectionsPage, find: SearchPage, provider: ProviderPage, platform: PlatformPage, tools: ToolsPage,
  detail: DetailPage, secrets: SecretsPage, resources: TeamResourcesPage, orgs: TeamPage, activity: ActivityPage,
  admin: AdminPage, start: GettingStartedPage, referrals: ReferralsPage, hub: HubPage, run: HubRunPage, help: HelpPage,
} = pages
export default { ...controller, components: { ...controller.components, ...dialogs, TeamResourcesPage, CatalogPage, ConnectionsPage, ProviderPage, PlatformPage, ToolsPage, DetailPage, SecretsPage, TeamPage, ActivityPage, AdminPage, GettingStartedPage, ReferralsPage, HelpPage, SearchPage, HubPage, HubRunPage, SignedOutPage, BrandMark, PublicNavigation, LandingNavigation, DashboardNavigation, SignInDialog } }
</script>

<template>
<div>
<main v-if="bootFailed" class="boot-status" aria-live="polite">
  <a href="/" class="brand"><BrandMark/>treg</a>
  <p role="alert">{{ t('app.bootFailed') }}</p>
  <button class="btn" @click="reloadApp()">{{ t('common.tryAgain') }}</button>
</main>
<!-- Continues index.html's loader on the page's own clock, so mounting does not restart it. -->
<main v-else-if="!bootReady" class="boot-status" aria-busy="true" :style="{'--boot-t': -Math.round(bootStartedAt)+'ms'}">
  <span class="boot-bar" aria-hidden="true"></span>
  <p role="status" style="position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap">{{ t('app.loading') }}</p>
</main>
<div v-else :class="{redesign:authed && !publicCatalog}">
  <!-- Focused sign-in entry after session initialization. -->
  <SignedOutPage v-if="!authed && !publicCatalog" />

  <template v-else>
    <a href="#maincontent" class="skip">{{ t('app.skipToContent') }}</a>
    <!-- A public catalog visitor is reading a WEBSITE, not operating an app: the workspace chrome
         (org switcher, global tool search, member nav) is furniture for a job they have not started.
         They get the marketing site's nav instead, so /catalog reads as part of treg.to rather than
         as a dashboard someone forgot to lock. -->
    <LandingNavigation v-if="view==='find'" />
    <PublicNavigation v-else-if="publicCatalog" />
    <DashboardNavigation v-else />
    <img v-if="authed && !publicCatalog && view==='start'" class="rd-background" src="/media/redesign/ascii-background.jpg" alt="" aria-hidden="true">
    <div v-if="startCopyError" class="rd-copy-error" role="alert">{{startCopyError}}<br><button class="btn sm" @click="startCopyError=''">{{ t('common.dismiss') }}</button></div>
    <span class="rd-sr-only" role="status">{{startCopied ? t('app.copiedToClipboard') : ''}}</span>
    <div class="layout" :class="{solo:publicCatalog}">
      <main id="maincontent" tabindex="-1" :class="{flush:view==='find'}">
        <div v-if="err" class="banner">{{err}}</div>
        <div v-if="pendingInvites.length" class="banner" style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
          <span>{{ t('app.invited') }}</span>
          <span v-for="inv in pendingInvites" :key="inv.id" style="display:inline-flex;align-items:center;gap:6px">
            <b>{{inv.name}}</b> <span class="role" :class="inv.role">{{inv.role}}</span>
            <button class="btn sm primary" @click="acceptInvite(inv)">{{ t('common.accept') }}</button>
          </span>
        </div>

        <!-- CATALOG: every platform, by category -->
        <CatalogPage v-if="view==='catalog'" />

        <!-- CONNECTIONS: the team's own accounts and keys, and every provider one can be added for -->
        <ConnectionsPage v-if="view==='connections'" />

        <!-- FIND: /search, a described job answered over the platform pile -->
        <SearchPage v-if="view==='find'" />

        <!-- CATALOG: one integration -->
        <ProviderPage v-if="view==='provider' && (mkProvider || mkPaused)" />

        <!-- CATALOG: one platform, from the endpoint catalog -->
        <PlatformPage v-if="view==='platform'" />

        <ToolsPage v-if="view==='tools'" />

        <!-- DETAIL (shareable deep links: /app/skills/<name> + /app/tools/<name>) -->
        <DetailPage v-if="view==='detail' && detail" />

        <SecretsPage v-if="view==='secrets'" />

        <TeamResourcesPage v-if="view==='resources'" />

        <TeamPage v-if="view==='orgs'" />

        <ActivityPage v-if="view==='activity'" />

        <AdminPage v-if="view==='admin'" />

        <GettingStartedPage v-if="view==='start'" />

        <!-- REFERRALS — a person's link and everyone who used it. A top-level view (never nested):
             a view inside a view renders nowhere, and the nav button would look dead. -->
        <ReferralsPage v-if="view==='referrals'" />
        <HubPage v-if="view==='hub'" />
        <HubRunPage v-if="view==='run'" />

        <HelpPage v-if="view==='help'" />
      </main>
    </div>

    <div v-if="keyMenu" class="key-actions-menu" role="menu" :style="{top:keyMenu.top+'px',right:keyMenu.right+'px'}" @click.stop>
      <p v-if="credentialIssue" id="key-action-blocked" class="sub" style="max-width:240px;margin:0;padding:6px 10px" role="status">{{keyActionBlockReason()}}</p>
      <button v-if="keyMenu.key.can_rename" role="menuitem" @click="editKey=keyMenu.key.id; editKeyName=keyMenu.key.name; keyMenu=null">{{ t('key.rename') }}</button>
      <button v-if="keyMenu.key.can_disable" role="menuitem" :disabled="!!credentialIssue" :aria-describedby="credentialIssue?'key-action-blocked':null" @click="requestKeyAction(keyMenu.key,'disable')">{{ t('key.disable') }}</button>
      <button v-if="keyMenu.key.can_enable" role="menuitem" :disabled="!!credentialIssue" :aria-describedby="credentialIssue?'key-action-blocked':null" @click="requestKeyAction(keyMenu.key,'enable')">{{ t('key.enable') }}</button>
      <button v-if="keyMenu.key.can_revoke" class="danger" role="menuitem" :disabled="!!credentialIssue" :aria-describedby="credentialIssue?'key-action-blocked':null" @click="requestKeyAction(keyMenu.key,'revoke')">{{ t('key.revoke') }}</button>
      <button v-if="keyMenu.key.can_hide && keyMenu.key.state==='revoked'" role="menuitem" :disabled="!!credentialIssue" :aria-describedby="credentialIssue?'key-action-blocked':null" @click="requestKeyAction(keyMenu.key,'hide')">{{ t('key.hide') }}</button>
    </div>

    <div v-if="keyConfirm" class="scrim" role="dialog" aria-modal="true" aria-labelledby="key-confirm-title" v-dialog="() => { keyConfirm=null }" @click.self="keyConfirm=null">
      <div class="modal" style="width:min(470px,94vw);padding:18px 20px">
        <h3 id="key-confirm-title" style="margin:0">{{ t('key.'+keyConfirm.action) }} “{{keyConfirm.key.name}}”？</h3>
        <p v-if="keyConfirm.action==='rotate'" class="sub" style="margin:12px 0 0"><template v-if="keyConfirm.key.kind==='default_human'">{{ t('key.rotateDefaultHumanNote') }}</template><template v-else>{{ t('key.rotateNote') }}</template></p>
        <p v-else-if="keyConfirm.action==='disable'" class="sub" style="margin:12px 0 0">{{ t('key.disableNote') }}</p>
        <p v-else-if="keyConfirm.action==='revoke'" class="sub" style="margin:12px 0 0"><template v-if="keyConfirm.key.kind==='agent'">{{ t('key.revokeAgentNote') }}</template><template v-else>{{ t('key.revokeNote') }}</template></p>
        <p v-else class="sub" style="margin:12px 0 0">{{ t('key.hideNote') }}</p>
        <p v-if="credentialIssue" class="banner" role="alert" style="margin-top:12px">{{keyActionBlockReason()}}</p>
        <div class="row-actions" style="display:flex;justify-content:flex-end;margin-top:20px"><button class="btn sm" @click="keyConfirm=null">{{ t('common.cancel') }}</button><button class="btn sm" :class="{danger:keyConfirm.action!=='hide'}" :disabled="keyBusy||!!credentialIssue" @click="confirmKeyAction">{{keyBusy?'…':t('common.confirmAction', {action: t('key.'+keyConfirm.action)})}}</button></div>
      </div>
    </div>

    <!-- Catalog dialogs. App-ROOT level, like every other dialog: nested inside the catalog
         view's template they do not render on an integration page. -->
    <ConnectTokenDialog v-if="tokenAsk" />

    <!-- TOP UP. Four presets + Other, the bonus each earns, and auto top-up as a toggle that is
         ON by default for a team with no mandate yet. The toggle IS the consent control: its label
         is the PSD2/SCA mandate text (amount, threshold), and Pay records it through
         /billing/autotopup BEFORE opening Checkout — so the card Checkout saves arms auto top-up
         from the setup webhook with numbers a human agreed to. Off = plain one-off top-up. -->
    <TopUpDialog v-if="topupOpen&&billing" />

    <AgentGuideDialog v-if="capAsk" />

    <ConnectionMethodDialog v-if="methodAsk" />

    <ResourcePickerDialog v-if="resPick" />

    <ExtraCredentialDialog v-if="newSkill" />

    <EditToolDialog v-if="newTool" />

    <!-- JOIN BY CODE -->
    <div class="scrim" role="dialog" aria-labelledby="join-team-title" aria-modal="true" v-if="showJoin" v-dialog="() => { showJoin=false }" @click.self="showJoin=false">
      <div class="modal" style="width:min(460px,92vw)"><div class="hd"><b id="join-team-title">{{ t('app.joinTitle') }}</b><button class="btn sm" @click="showJoin=false" :aria-label="t('common.close')">✕</button></div>
        <div style="padding:18px"><p class="sub" style="margin-top:0">{{ t('app.joinBody', {email: me}) }}</p>
          <div class="field"><input v-model="joinCode" :placeholder="t('app.joinCodePlaceholder')" @keyup.enter="joinByCode"/></div>
          <button class="btn primary" @click="joinByCode" :disabled="joinBusy">{{joinBusy?t('app.joining'):t('common.join')}}</button>
          <div v-if="joinErr" class="banner" style="margin-top:12px">{{joinErr}}</div>
        </div></div>
    </div>

    <!-- INVITED: accept pending invites (multi-select, all checked, the clicked link's team first).
         Opens on first run (no team yet) AND whenever an invite link lands (?invite_org=), even for
         users already in other teams. Decline → create-your-own (first run) or just close. -->
    <AcceptInvitesDialog v-if="inviteChoice && pendingInvites.length" />

    <!-- FIRST-RUN WELCOME: pick your agent → the setup line → a first prompt (the team is already made) -->
    <WelcomeDialog v-if="welcome.on" />

    <!-- CREATE TEAM -->
    <div class="scrim" role="dialog" aria-labelledby="new-team-title" aria-modal="true" v-if="newOrg" v-dialog="() => { newOrg=false }" @click.self="newOrg=false">
      <div class="modal" style="width:min(440px,92vw)"><div class="hd"><b id="new-team-title">{{ t('app.createTeamTitle') }}</b><button class="btn sm" @click="newOrg=false" :aria-label="t('common.close')">✕</button></div>
        <div style="padding:18px"><p class="sub" style="margin-top:0">{{ t('app.createTeamBody') }}</p>
          <div class="field"><input v-model="newOrgName" :placeholder="t('app.teamNamePlaceholder')" @keyup.enter="createOrg"/></div>
          <button class="btn primary" @click="createOrg" :disabled="orgBusy">{{orgBusy?t('app.creating'):t('common.create')}}</button>
          <div v-if="orgErr" class="banner" style="margin-top:12px">{{orgErr}}</div>
        </div></div>
    </div>

    <!-- ADD ORG -->
    <div class="scrim" role="dialog" aria-labelledby="add-org-title" aria-modal="true" v-if="addOrg" v-dialog="() => { addOrg=false }" @click.self="addOrg=false">
      <div class="modal" style="width:min(440px,92vw)"><div class="hd"><b id="add-org-title">{{ t('app.addOrgTitle') }}</b><button class="btn sm" @click="addOrg=false" :aria-label="t('common.close')">✕</button></div>
        <div style="padding:18px"><p class="sub" style="margin-top:0">{{ t('app.addOrgBody') }}</p>
          <div class="field"><input v-model="tokenInput" type="password" placeholder="X-Treg-Token"/></div>
          <button class="btn primary" @click="addToken(tokenInput, true)" :disabled="busy">{{busy?t('app.checking'):t('common.add')}}</button>
          <div v-if="loginErr" class="banner" style="margin-top:12px">{{loginErr}}</div>
        </div></div>
    </div>

    <CopyToolDialog v-if="copyTool" />

    <!-- INSTALL A RECIPE (recipe-only bundle: how to install/use, no proxy call) -->
    <div class="scrim" role="dialog" aria-labelledby="install-recipe-title" aria-modal="true" v-if="copyRecipe" v-dialog="() => { copyRecipe=null }" @click.self="copyRecipe=null">
      <div class="modal"><div class="hd"><b id="install-recipe-title">Install “{{copyRecipe.name}}”</b><button class="btn sm ico" @click="copyRecipe=null" aria-label="Close">✕</button></div>
        <div style="padding:16px 18px">
          <div class="tabs"><button v-for="t in ['CLI','Claude Code']" :key="t" :class="{active:recipeTab===t}" @click="recipeTab=t">{{t}}</button></div>
          <p class="explain">{{ t('app.recipeExplain') }}</p>
          <pre class="code" v-html="recipeSnip.html"></pre>
          <div style="margin-top:12px"><button class="btn primary" @click="copy(recipeSnip.text)">⧉ {{copied?t('common.copiedAlt'):t('common.copy')}}</button></div>
        </div></div>
    </div>

    <!-- AGENT SETUP GUIDE (an instruction to paste into a coding agent) -->
    <div class="scrim" role="dialog" aria-labelledby="agent-guide-title" aria-modal="true" v-if="agentGuide" v-dialog="() => { agentGuide=null }" @click.self="agentGuide=null">
      <div class="modal" style="width:min(680px,95vw)"><div class="hd"><b id="agent-guide-title">{{agentGuide==='admin'?t('app.agentGuideAdminTitle'):t('app.agentGuideTitle')}}</b><button class="btn sm ico" @click="agentGuide=null" :aria-label="t('common.close')">✕</button></div>
        <div style="padding:16px 18px">
          <p class="explain">{{ t('app.agentGuideExplain') }}</p>
          <pre class="code" style="white-space:pre-wrap;max-height:44vh;overflow:auto">{{agentPromptText}}</pre>
          <div style="margin-top:12px;display:flex;gap:10px;align-items:center"><button class="btn primary" @click="copyAgentPrompt">⧉ {{agentGuideCopied?t('common.copiedAlt'):t('common.copy')}}</button></div>
        </div></div>
    </div>

    <!-- LIST AS VENDOR (an instruction the vendor pastes into THEIR coding agent; it raises the PR) -->
    <ImportSkillDialog v-if="vendorAsk" />

    <!-- REQUEST A TOOL (a "the catalog doesn't have X" report — saved server-side, steers what gets keyed next) -->
    <RequestToolDialog v-if="reqAsk" />

    <!-- SHARE A DETAIL PAGE (invite someone new; they land right here after sign-in) -->
    <ShareDialog v-if="share.on && detail" />

    <!-- VIEW A RECIPE (the SKILL.md content) -->
    <RecipeDialog v-if="viewRecipe" />

    <!-- USE drawer: one entry point, two verbs — API call (proxy) / CLI run (server) -->
    <RunToolDialog v-if="tryTool" />

    <!-- Activity → one call. The archive's copy of what was asked and what came back (metered
         platform calls only — own-key and own-tool calls are relayed without being stored). -->
    <CallDetailsDialog v-if="callView" />
    <!-- Try a catalog endpoint right here. Same relay as any call - served by the org's own
         key when one exists, else by a verified public upstream route when declared, else treg's
         key billed to the team balance - and logged in Activity exactly like a CLI call. -->
    <TryEndpointDialog v-if="epTry" />
    <UserAvatarDialog v-if="avatarDialog" />

    <!-- Toasts, bottom right: a newer dashboard build is live, and the access reminder (fired when
         a new tool is registered while some members have customized access). -->
    <div v-if="newVersion" class="app-toast" role="status">
      <p>{{ t('app.newVersion') }}</p>
      <div class="app-toast-a"><button class="btn sm" @click="newVersion=false">{{ t('common.later') }}</button><button class="btn sm primary" @click="reloadApp()">{{ t('app.refreshNow') }}</button></div>
    </div>
    <div v-if="accessNote" class="app-toast" role="status">
      <p>{{accessNote}}</p>
      <div class="app-toast-a"><button class="btn sm" @click="accessNote=''">{{ t('common.dismiss') }}</button><button class="btn sm primary" @click="go('org')">{{ t('app.openTeam') }}</button></div>
    </div>
  </template>

  <!-- SIGN-IN MODAL - a SIBLING of both branches, so the public catalog (which renders the app
       shell, not the logged-out landing) can sign anyone in without navigating away. -->
  <FishVoiceDialog v-if="fishVoiceDialog" />
  <SignInDialog  />
</div>
</div>
</template>

