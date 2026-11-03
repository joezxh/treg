<script>
import { useDashboard } from '../state/context'
import PageTabs from './PageTabs.vue'
import { t } from '../i18n/index'

// The head of the three "Your own tools" pages (tools, secrets, team resources): the shelf's hero, and
// the three as one tab row, the catalog's. The lede is the family's, so the tabs never move; each
// page adds its own note under them, and its own actions.
export default {
  components: { PageTabs },
  props: { current: { type: String, required: true } },
  setup() { const ctx = useDashboard(); ctx.t = t; return ctx },
  methods: {
    tabs() {
      return [
        { key: 'tools', label: t('tools.skillsAndTools') },
        ...(this.canRegister ? [{ key: 'secrets', label: t('tools.secrets') }] : []),
        { key: 'resources', label: t('tools.teamResources') },
      ]
    },
  },
}
</script>

<template>
<header class="pl-hero pl-hero-row">
  <div>
    <h1>{{ t('tools.title') }}</h1>
    <p class="pl-lede">{{ t('tools.lede') }}</p>
  </div>
  <div class="pl-hero-a"><slot name="actions" /></div>
</header>
<PageTabs :label="t('tools.title')" :tabs="tabs" :current="current" @select="go" />
<p v-if="$slots.default" class="cat-hint own-note"><slot /></p>
</template>
