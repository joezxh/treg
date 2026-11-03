<script>
import { useDashboard } from '../state/context'
import { t as __t } from '../i18n/index'

// One of the team's own tools or skills, on Your own tools: the card is Connections' credential card,
// so the two halves of "whose key" read alike. The card opens the shareable page; the buttons act.
export default {
  props: {
    t: { type: Object, default: null },      // a tool (endpoint or CLI)
    skill: { type: Object, default: null },  // or a knowledge skill (a recipe-only bundle)
  },
  setup: useDashboard,
  computed: {
    name() { return (this.t || this.skill).name },
    href() { return this.t ? this.rowHref(this.t) : '/app/skills/'+encodeURIComponent(this.skill.name) },
    // Where a call runs is the one fact that changes what a member may do with it.
    where() {
      const t = this.t
      if (!t) return { label: this.tt('own.where.skill'), tone: 'quiet', title: this.tt('own.where.skillTitle') }
      if (!t.cli) return { label: this.tt('own.where.api'), tone: 'quiet', title: this.tt('own.where.apiTitle') }
      if (t.server_runnable) return { label: this.tt('own.where.server'), tone: 'ok', title: this.tt('own.where.serverTitle') }
      return { label: this.tt('own.where.local'), tone: 'warn', title: this.tt('own.where.localTitle') }
    },
    creds() { return this.t ? this.credChips(this.t).map(w => w.label).join(', ') : '' },
  },
  methods: {
    // Alias for the translator so the card's own `t` prop (the tool) does not shadow it.
    tt(k, p) { return _tt(k, p) },
    open() { this.t ? this.rowOpen(this.t) : this.openDetail('skill', this.skill.name) },
  },
}
</script>

<template>
<div class="pl-card cn-card own-card" :class="'cn-'+where.tone" role="link" tabindex="0"
     :title="tt('own.openPage')" @click="open" @keydown.enter.self="open">
  <div class="cn-top">
    <span class="pl-logo lg gen" :style="{background:platTileBg(name)}" aria-hidden="true"><span class="pt-i">{{platInitial({label:name})}}</span></span>
    <span class="cn-id">
      <a :href="href" @click.prevent.stop="open"><b>{{name}}</b></a>
      <span class="pl-meta" :title="t ? t.base_url : ''">{{t ? t.host : tt('own.skillInstall')+' '+name}}</span>
    </span>
    <span class="cn-st" :title="where.title">{{where.label}}</span>
  </div>

  <p v-if="t" class="cn-what">
    {{t.cli ? tt('own.cliPrefix')+' '+(t.cli.bin||t.name) : tt('own.httpEndpoint')}} · {{creds ? creds+' '+tt('own.credential') : tt('own.noCredential')}}<template v-if="t.owner"> · {{tt('own.addedBy')}} {{short(t.owner)}}</template>
  </p>

  <div v-if="t" class="cn-acts" @click.stop>
    <button class="pl-btn sm" @click="openUse(t)" :title="tt('own.tryItTitle')">{{tt('own.tryIt')}}</button>
    <button class="pl-btn sm ghost" @click="openCopy(t)" :title="tt('own.copySnippetTitle')">{{tt('own.copySnippet')}}</button>
    <span class="cn-links">
      <button v-if="t.cli && canRegister" @click="toggleLocalRun(t)" :title="localRunTitle(t)">{{tt('own.localRuns')}} {{t.cli.enabled?tt('own.on'):tt('own.off')}}</button>
      <button v-if="canRegister" @click="openEditTool(t)">{{tt('own.edit')}}</button>
      <button v-if="canRegister" class="cn-del" :class="{armed:confirmDelTool===t.id}" @click="deleteTool(t)">
        {{confirmDelTool===t.id ? tt('own.deleteConfirm') : tt('own.delete')}}</button>
    </span>
  </div>
  <div v-else class="cn-acts" @click.stop>
    <button class="pl-btn sm" @click="openRecipeCopy(skill)">{{tt('own.install')}}</button>
    <span class="cn-links">
      <button @click="openRecipeView(skill)">{{tt('own.viewSkillMd')}}</button>
      <button v-if="canRegister" class="cn-del" :class="{armed:confirmDelBundle===skill.id}" @click="deleteRecipe(skill)">
        {{confirmDelBundle===skill.id ? tt('own.deleteConfirm') : tt('own.delete')}}</button>
    </span>
  </div>
</div>
</template>
