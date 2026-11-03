<script>
import { useDashboard } from '../state/context'
import ProviderLogo from '../components/ProviderLogo.vue'
import ConnectionCard from '../components/ConnectionCard.vue'
import FilterBox from '../components/FilterBox.vue'

// Every account and key the team holds, then every provider one can be added for. The catalog says
// what an agent can call; this page says whose credential it calls with. A provider key saved as a
// secret named for the provider is listed here too, since the credential ladder treats it the same.
export default {
  components: { ProviderLogo, ConnectionCard, FilterBox },
  setup: useDashboard,
  watch: {
    // The one place a "Bring your own key" jump scrolls: when it lands, and again if the provider list
    // arrives after it did.
    byokFocus() { this.focusProvider() },
    'providers.length'() { this.focusProvider() },
  },
  mounted() { this.focusProvider() },
  methods: {
    focusProvider() {
      if (!this.byokFocus) return
      this.$nextTick(() => document.getElementById('prov-'+this.byokFocus)?.scrollIntoView({block:'center', behavior:'smooth'}))
    },
  },
}
</script>

<template>
<div class="pl cn">
  <header class="pl-hero">
    <h1>{{t('connPage.title')}}</h1>
    <p class="pl-lede">{{t('connPage.lede')}}</p>
  </header>

  <div v-if="connErr || secretErr" class="banner cn-banner"><span>{{connErr || secretErr}}</span><button class="btn sm ico" @click="connErr=''; secretErr=''" :aria-label="t('common.dismiss')">✕</button></div>

  <section v-if="connAccounts.length" class="pl-sec">
    <h2 class="pl-h"><span>{{t('connPage.connected')}}</span><i></i><em>{{connAccounts.length}}</em></h2>
    <div class="pl-grid pl-grid-t">
      <ConnectionCard v-for="a in connAccounts" :key="a.id" :a="a" manage />
    </div>
  </section>

  <section class="pl-sec">
    <h2 class="pl-h"><span>{{t('connPage.addConnection')}}</span><i></i><em>{{connectable.length}}</em></h2>
    <div class="cn-filters">
      <FilterBox v-model="connQ" :label="t('connPage.filterLabel')" :placeholder="t('connPage.filterPlaceholder')" />
      <!-- Logging in with an account you already have and pasting a key are different errands:
           someone holding a Google Ads login is not scanning for API-key vendors. -->
      <div class="seg cn-kinds" role="radiogroup" :aria-label="t('connPage.howYouConnect')">
        <button v-for="k in connKinds" :key="k.key" role="radio" :aria-checked="connKind===k.key"
                :class="{on:connKind===k.key}" :title="k.hint" @click="connKind=k.key">{{k.label}} <span>{{k.n}}</span></button>
      </div>
    </div>
    <div v-for="g in providerGroups" :key="g.category" class="cn-group">
      <h3 class="pl-h pl-h-quiet"><span>{{g.category}}</span><em>{{g.items.length}}</em></h3>
      <div class="pl-grid pl-grid-t">
        <!-- One line per provider: someone here is looking for an account they already hold, by name.
             The card opens the provider's page (its permissions, its tools); the button connects from here. -->
        <div v-for="{p, pasted, n} in g.items" :key="p.service" :id="'prov-'+p.service" class="pl-card pl-tool cn-prov" :class="{on:byokFocus===p.service}"
             role="button" tabindex="0" :aria-label="t('provider.open', { name: p.display_name })" :title="p.summary"
             @click="openProvider(p.service)" @keydown.enter.self="openProvider(p.service)">
          <ProviderLogo :service="p.service" large />
          <span class="pl-tool-b"><b>{{p.display_name}}</b>
            <span class="pl-meta">{{authLabel(p)}}<template v-if="n"> · {{n}} connected</template></span></span>
          <span class="cn-prov-a" @click.stop>
            <button class="pl-btn sm ghost" :disabled="connBusy"
                    @click="startConnect(p)" :title="pasted ? t('provider.pasteOwn', { name: p.display_name }) : t('provider.loginApprove', { name: p.display_name })">
              {{connectLabel(p, n)}}</button>
          </span>
        </div>
      </div>
    </div>
    <p v-if="connQ && !providerGroups.length" class="pl-empty">{{ t('connPage.noMatch', { q: connQ.trim() }) }}
      <button class="pl-link" @click="openToolRequest()">{{t('connPage.askForIt')}}</button></p>
    <p v-else-if="!providers.length" class="pl-empty">{{t('connPage.loadingProviders')}}</p>
  </section>
</div>
</template>
