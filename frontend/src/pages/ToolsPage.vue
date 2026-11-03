<script>
import { useDashboard } from '../state/context'
import OwnToolsHeader from '../components/OwnToolsHeader.vue'
import OwnToolCard from '../components/OwnToolCard.vue'
import FilterBox from '../components/FilterBox.vue'
import LoadFromMachine from '../components/LoadFromMachine.vue'
export default { components: { OwnToolsHeader, OwnToolCard, FilterBox, LoadFromMachine }, setup: useDashboard, mounted(){ this.loadPlatforms() } }  // the catalog size in the copy
</script>

<template>
<div class="pl own">
  <OwnToolsHeader current="tools">
    <template #actions v-if="canRegister">
      <button class="pl-btn ghost" @click="openAddSkill">{{ t('toolsPage.importSkill') }}</button>
      <span class="own-add">
        <button class="pl-btn" @click.stop="addToolMenu=!addToolMenu" aria-haspopup="true" :aria-expanded="addToolMenu">{{ t('toolsPage.addTool') }}</button>
        <div v-if="addToolMenu" class="own-add-scrim" @click="addToolMenu=false"></div>
        <div class="dropdown own-add-menu" v-if="addToolMenu" @click.stop>
          <div class="row" @click="openAddTool('endpoint')"><span><b>{{ t('toolsPage.menuEndpoint') }}</b><span class="sub">{{ t('toolsPage.menuEndpointSub') }}</span></span></div>
          <div class="row" @click="openAddTool('cli')"><span><b>{{ t('toolsPage.menuCli') }}</b><span class="sub">{{ t('toolsPage.menuCliSub') }}</span></span></div>
          <div class="row" @click="addToolMenu=false; go('catalog')"><span><b>{{ t('toolsPage.menuCatalog') }}</b><span class="sub">{{ t('toolsPage.menuCatalogSub') }}</span></span></div>
        </div>
      </span>
    </template>
  </OwnToolsHeader>

  <div v-if="orgMsg" class="banner cn-banner"><span>{{orgMsg}}</span><button class="btn sm ico" @click="orgMsg=''" :aria-label="t('common.dismiss')">✕</button></div>
  <div v-if="toolErr && !newTool" class="banner cn-banner"><span>{{toolErr}}</span></div>
  <div v-if="runNote" class="banner cn-banner">
    <span v-html="t('toolsPage.runNote', { run: runNote })"></span>
    <button class="btn sm ico" @click="runNote=''" :aria-label="t('common.dismiss')">✕</button>
  </div>

  <div class="cn-filters" v-if="hasAnyTools || q">
    <FilterBox v-model="q" :label="t('toolsPage.searchLabel')" :placeholder="t('toolsPage.searchPlaceholder')" :register="el => setElement('search', el)" />
    <div class="seg pl-seg" role="radiogroup" :aria-label="t('toolsPage.kindAria')">
      <button v-for="k in [{key:'all', label:t('toolsPage.tabAll'), n:ownToolCount}, {key:'endpoints', label:t('toolsPage.tabApisClis'), n:endpoints.length},
                           {key:'skills', label:t('toolsPage.tabIntegrationSkills'), n:skillTools.length}, {key:'recipes', label:t('toolsPage.tabSkills'), n:recipes.length}]"
              :key="k.key" role="radio" :aria-checked="toolTab===k.key" :class="{on:toolTab===k.key}" @click="toolTab=k.key">{{k.label}} <span>{{k.n}}</span></button>
    </div>
  </div>

  <section class="pl-sec" v-for="grp in toolGroups" :key="grp.key" v-show="grp.rows.length && (toolTab==='all'||toolTab===grp.key)">
    <h2 class="pl-h"><span>{{grp.label}}</span><i></i><em>{{grp.rows.length}}</em></h2>
    <p class="cat-hint">{{grp.hint}}</p>
    <div class="pl-grid pl-grid-t">
      <OwnToolCard v-for="t in grp.rows" :key="t.id" :t="t" />
    </div>
  </section>

  <section class="pl-sec" v-show="recipes.length && (toolTab==='all'||toolTab==='recipes')">
    <h2 class="pl-h"><span>{{ t('toolsPage.skillsHeading') }}</span><i></i><em>{{recipes.length}}</em></h2>
    <p class="cat-hint">{{ t('toolsPage.skillsHint') }}</p>
    <div class="pl-grid pl-grid-t">
      <OwnToolCard v-for="r in recipes" :key="r.id" :skill="r" />
    </div>
  </section>

  <p v-if="!loading && !hasAnyTools && (q || !canRegister || personalWithTeams)" class="pl-empty">{{ t(q ? 'toolsPage.emptyMatches' : 'toolsPage.emptyYet', { q }) }}<template v-if="!q && personalWithTeams">{{ t('toolsPage.emptyPersonal1') }}<b>personal</b>{{ t('toolsPage.emptyPersonal2') }}<a href="#" @click.prevent="jumpToTeam()">{{ t('toolsPage.switchToTeam') }}</a></template></p>
  <LoadFromMachine v-if="!loading && !hasAnyTools && !q && canRegister" :title="t('toolsPage.nothingTitle', { n: toolCountText || t('toolsPage.thousands') })">
    {{ t('toolsPage.emptyBody1') }}<b>$1.00 of free credit once</b>{{ t('toolsPage.emptyBody2') }}<a href="#" @click.prevent="go('catalog')">{{ t('toolsPage.emptyBodyBrowse') }}</a><br>{{ t('toolsPage.emptyBody3') }}<i>own</i>{{ t('toolsPage.emptyBody4') }}<span class="mono">.env</span>{{ t('toolsPage.emptyBody5') }}
  </LoadFromMachine>
</div>
</template>
