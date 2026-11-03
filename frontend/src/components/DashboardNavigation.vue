<script>
import { useDashboard } from '../state/context'
import BrandMark from './BrandMark.vue'
import Avatar from './ui/Avatar.vue'
import LanguageSwitch from './LanguageSwitch.vue'
import WeChatQrDialog from './WeChatQrDialog.vue'
import { SOCIAL_LINKS } from '../state/social'
import { t } from '../i18n/index'
export default {
  components: { BrandMark, Avatar, LanguageSwitch, WeChatQrDialog },
  setup() {
    const ctx = useDashboard()
    ctx.t = t
    return ctx
  },
  data: () => ({ meAvatarBroken: false, wechatQr: false, socials: SOCIAL_LINKS }),
  watch: { meAvatar() { this.meAvatarBroken = false } },
  methods: {
    socialLabel(platform) { return t('social.' + platform) },
    socialGo(social) {
      if (social.kind === 'qrcode') { this.wechatQr = true; this.elements.accountMenu.open = false }
      else window.open(social.url, '_blank', 'noopener')
    },
  },
}
</script>

<template>
<header class="rd-top" >
      <div class="rd-identity">
        <a class="rd-brand brand" href="/" aria-label="treg home"><BrandMark/>treg</a>
        <div class="orgblock" v-if="authed">
          <div class="orgmain" :ref="el => setElement('orgmain', el)" @click="toggleOrgMenu" role="button" tabindex="0" @keydown.enter="toggleOrgMenu" @keydown.space.prevent="toggleOrgMenu" aria-haspopup="true" :aria-expanded="orgMenu" aria-label="Teams">
            <span class="role" :class="activeRole">{{activeRole}}</span>
            <Avatar v-if="activeOrg && activeOrg.avatar_url" :src="activeOrg.avatar_url" :name="activeName" :size="20" />
            <b class="orgname">{{activeName}}</b>
            <span class="orgcaret">▾</span>
          </div>
          <div class="dropdown" v-if="orgMenu" :style="orgMenuStyle" @click.stop>
            <div class="grp" style="margin:4px 10px 6px">{{ t('dash.yourTeams') }}</div>
            <div class="orgrow" v-for="o in myOrgs" :key="o.slug" :class="{off:!connected(o.slug)}">
              <Avatar :src="o.avatar_url" :name="o.name||o.slug" :size="26" />
              <div class="orgrow-main">
                <div class="orgrow-name">{{o.name}}</div>
                <div class="orgrow-meta"><span class="role" :class="o.role">{{o.role}}</span><span v-if="isPersonal(o)" class="chip">{{ t('dash.personal') }}</span><span v-if="o.demo" class="chip demo">{{ t('dash.demo') }}</span></div>
              </div>
              <button class="orgrow-btn" @click.stop="orgSettings(o)" :title="t('dash.teamSettings')" :aria-label="t('dash.teamSettings')">⚙</button>
              <span v-if="o.slug===activeSlugNow" class="orgrow-active">✓ {{ t('dash.active') }}</span>
              <button v-else-if="sessionMode || connected(o.slug)" class="orgrow-btn" @click.stop="switchTo(o)">{{ t('dash.switch') }}</button>
              <button v-else class="orgrow-btn" @click.stop="addOrg=true; orgMenu=false">{{ t('dash.token') }}</button>
            </div>
            <div class="orgrow-sep"></div>
            <button type="button" class="row" v-if="sessionMode" @click="newOrg=true; newOrgName=''; orgMenu=false"><span>＋ {{ t('dash.newTeam') }}</span></button>
            <button type="button" class="row" v-if="sessionMode" @click="showJoin=true; joinCode=''; joinErr=''; orgMenu=false"><span>⤷ {{ t('dash.joinByCode') }}</span></button>
            <button type="button" class="row" v-if="!sessionMode" @click="addOrg=true; orgMenu=false"><span>＋ {{ t('dash.addTeamWithToken') }}</span></button>
          </div>
        </div>


      </div>
      <nav class="rd-navs" aria-label="Primary navigation"><button v-if="authed" class="rd-nav" :class="{active:view==='start'}" :aria-current="(view==='start')?'page':null" @click="go('start')">{{ t('nav.gettingStarted') }}</button>
<button v-if="canRegister" class="rd-nav" :class="{active:view==='catalog'}" :aria-current="(view==='catalog')?'page':null" @click="go('catalog')">{{ t('nav.catalog') }}</button>
<button v-if="authed" class="rd-nav" :class="{active:view==='connections'||view==='provider'}" :aria-current="(view==='connections'||view==='provider')?'page':null" @click="go('connections')">{{ t('nav.connections') }}</button>
<button v-if="authed" class="rd-nav" :class="{active:view==='tools'||view==='secrets'||view==='resources'}" :aria-current="(view==='tools'||view==='secrets'||view==='resources')?'page':null" @click="go('tools')">{{ t('nav.yourTools') }}</button>
<button v-if="authed" class="rd-nav" :class="{active:view==='activity'}" :aria-current="(view==='activity')?'page':null" @click="go('activity')">{{ t('nav.activity') }}</button>
<button v-if="authed && hubOn" class="rd-nav" :class="{active:view==='hub'||view==='run'}" :aria-current="(view==='hub'||view==='run')?'page':null" @click="go('hub')">{{ t('nav.hub') }}</button>
<button v-if="authed" class="rd-nav" :class="{active:view==='orgs'}" :aria-current="(view==='orgs')?'page':null" @click="go('orgs')">{{ t('nav.team') }}</button></nav>
      <div class="rd-account">
        <a v-if="authed" class="rd-referral" href="#referrals" @click.prevent="go('referrals')" :aria-current="view==='referrals'?'page':null" :title="refEntryTitle()" :aria-label="'Referral: '+refEntryTitle()"><img src="/media/redesign/referral-gift.svg" alt=""><span>{{ t('dash.referral') }}</span></a>
        <button v-if="billing" class="rd-balance" :title="'Balance: '+money(billing.balance_micro)" @click="orgTab='billing'; go('orgs')"><span>{{ t('dash.balance') }}</span><b>{{moneyGlance(billing.balance_micro)}}</b></button>
        <LanguageSwitch/>
        <details class="rd-account-menu" :ref="el => setElement('accountMenu', el)">
          <summary :aria-label="'Account: '+me"><span class="rd-avatar" style="overflow:hidden"><img v-if="meAvatar && !meAvatarBroken" :src="meAvatar" alt="" style="width:100%;height:100%;object-fit:cover" @error="meAvatarBroken=true"><template v-else>{{initials}}</template></span></summary>
          <div class="rd-account-panel">
            <p class="rd-email">{{me}}</p>
            <button @click="avatarDialog=true; elements.accountMenu.open=false">{{ t('dash.yourAvatar') }}</button>
            <button @click="toggleTheme">{{ theme==='dark' ? t('dash.lightAppearance') : t('dash.darkAppearance') }}</button>
            <button v-if="billing" @click="orgTab='billing'; go('orgs'); elements.accountMenu.open=false">{{ t('dash.billing') }}</button>
            <button v-if="isAdmin" @click="go('admin'); elements.accountMenu.open=false">{{ t('dash.admin') }}</button>
            <a href="/tutorial">{{ t('nav.tutorial') }}</a>
            <template v-for="s in socials" :key="s.platform">
              <a v-if="s.kind === 'link'" :href="s.url" target="_blank" rel="noopener">{{ socialLabel(s.platform) }}</a>
              <button v-else type="button" @click="socialGo(s)">{{ socialLabel(s.platform) }}</button>
            </template>
            <button @click="logout">{{ t('nav.signout') }}</button>
          </div>
        </details>
      </div>
    </header>
    <WeChatQrDialog v-if="wechatQr" @close="wechatQr=false"/>
</template>
