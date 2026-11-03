<script>
import { useDashboard } from '../state/context'
import PageTabs from '../components/PageTabs.vue'
import { DataTable } from '../components/ui/table'
import SpendBars from '../components/SpendBars.vue'
import SelectMenu from '../components/ui/SelectMenu.vue'
import DateRangePicker from '../components/ui/DateRangePicker.vue'
import InfoTip from '../components/ui/InfoTip.vue'
import Money from '../components/ui/Money.vue'
import { NO_KEY } from '../state/constants.js'

// The feed reads left to right as one sentence: when, who (the key and runtime under it), which call
// (the action and tags under it), how it went, what it cost.
const FEED = [
  { key: 'when', headerKey: 'activity.colWhen' },
  { key: 'caller', headerKey: 'activity.colCaller', width: '22%', wrap: true },
  { key: 'call', headerKey: 'activity.colCall', wrap: true, mobile: 'primary' },
  { key: 'status', headerKey: 'activity.colStatus' },
  { key: 'cost', headerKey: 'activity.colCost', align: 'right' },
]
const num = (key, headerKey) => ({ key, headerKey, align: 'right' })
const BY_MEMBER = [{ key: 'member', headerKey: 'activity.colMember', mobile: 'primary' }, num('call', 'activity.colApi'), num('local_run', 'activity.colLocal'), num('server_run', 'activity.colServer'), num('total', 'activity.colTotal')]
const BY_TOOL = [{ key: 'name', headerKey: 'activity.colTool', mobile: 'primary' }, num('total', 'activity.colEvents')]
const BY_DAY = [{ key: 'day', headerKey: 'activity.colDay', mobile: 'primary' }, num('total', 'activity.colEvents')]
const BY_TAG = [{ key: 'value', headerKey: 'activity.colValue', mobile: 'primary' }, num('calls', 'activity.colCalls'), num('spend', 'activity.colSpend')]
const BY_SERIES = [{ key: 'name', headerKey: 'activity.colName', mobile: 'primary' }, { key: 'share', headerKey: 'activity.colShare', width: '22%' }, num('spend', 'activity.colSpend')]
const GROUPS = [{ value: 'day', labelKey: 'activity.groupDay' }, { value: 'week', labelKey: 'activity.groupWeek' }, { value: 'month', labelKey: 'activity.groupMonth' }]
const STACKS = [{ value: 'key', labelKey: 'activity.stackKeys' }, { value: 'tool', labelKey: 'activity.stackTools' }]
const PAGE = 10
const dayLabel = (iso, opts) => new Date(iso + 'T00:00:00Z').toLocaleDateString(undefined, { timeZone: 'UTC', ...opts })

export default {
  components: { PageTabs, DataTable, SpendBars, SelectMenu, DateRangePicker, InfoTip, Money },
  setup: useDashboard,
  data: () => ({ PAGE, NO_KEY }),
  computed: {
    // Column headers carry their own translation key; the table reads `.header` after we resolve it.
    feedColumns() { return FEED.map(c => ({ ...c, header: this.t(c.headerKey) })) },
    memberColumns() { return BY_MEMBER.map(c => ({ ...c, header: this.t(c.headerKey) })) },
    toolColumns() { return BY_TOOL.map(c => ({ ...c, header: this.t(c.headerKey) })) },
    dayColumns() { return BY_DAY.map(c => ({ ...c, header: this.t(c.headerKey) })) },
    tagColumns() { return BY_TAG.map(c => ({ ...c, header: this.t(c.headerKey) })) },
    spendColumns() { return BY_SERIES.map(c => ({ ...c, header: this.t(c.headerKey) })) },
    groups() { return GROUPS.map(g => ({ value: g.value, label: this.t(g.labelKey) })) },
    stacks() { return STACKS.map(s => ({ value: s.value, label: this.t(s.labelKey) })) },
    // The filter lists keep the current choice even when the new range has no spend for it.
    daysNewestFirst() { return [...(this.usage?.by_day || [])].reverse() },
    activityKeyOptions() {
      return [{ value: '', label: this.t('activity.allApiKeys') }, ...this.apiKeys.map(k => ({ value: String(k.id), label: this.keyLabel(k) }))]
    },
    spendKeyOptions() {
      return [{ value: '', label: this.t('activity.allApiKeys') }, ...(this.usageSpend?.options?.keys || []).map(k => ({ value: String(k.id), label: k.name }))]
    },
    spendProviderOptions() {
      return [{ value: '', label: this.t('activity.allProviders') }, ...(this.usageSpend?.options?.providers || []).map(p => ({ value: p.id, label: p.name || p.id }))]
    },
    spendSeries() {
      const noun = this.usageSpend?.stack === 'tool' ? 'tools' : 'keys'
      return (this.usageSpend?.series || []).map(s => s.id === 'none' ? { ...s, info: NO_KEY }
        : s.id === '__other' ? { ...s, name: `Other (${s.members} ${noun})`, folded: this.foldedRanking } : s)
    },
    // What the Other slice holds over the whole range: every ranked series without its own color.
    foldedRanking() {
      const shown = new Set((this.usageSpend?.series || []).map(s => s.id))
      return (this.usageSpend?.ranking || []).filter(r => !shown.has(r.id)).map(r => ({ id: r.id, name: r.name, micro: r.spent_micro }))
    },
    spendBuckets() {
      const s = this.usageSpend
      if (!s?.buckets) return []
      const month = s.group === 'month', week = s.group === 'week'
      return s.buckets.map(b => ({
        id: b.start, parts: b.parts, charges: b.charges,
        label: month ? dayLabel(b.start, { month: 'long', year: 'numeric' }) : (week ? 'Week of ' : '') + dayLabel(b.start, { month: 'short', day: 'numeric', year: 'numeric' }),
        tick: month ? dayLabel(b.start, { month: 'short' }) : dayLabel(b.start, { month: 'short', day: 'numeric' }),
      }))
    },
    usageCountsFrom() {
      const u = this.usage
      return u?.history_from && u.history_from > u.since.slice(0, 10) ? dayLabel(u.history_from, { month: 'short', day: 'numeric', year: 'numeric' }) : ''
    },
    historyFrom() { return this.usageSpend?.history_from ? dayLabel(this.usageSpend.history_from, { month: 'short', day: 'numeric', year: 'numeric' }) : '' },
    actTabs() { return [{ key: 'feed', label: this.t('activity.tabCalls') }, ...(this.canAdmin ? [{ key: 'usage', label: this.t('activity.tabUsage') }] : [])] },
  },
  methods: {
    pickTab(key) { this.actTab = key; if (key === 'usage') this.loadUsage() },
    page(rows, n) { return rows.slice(n * PAGE, (n + 1) * PAGE) },
    pageLabel(rows, n) { return `${n * PAGE + 1}–${Math.min((n + 1) * PAGE, rows.length)} of ${rows.length}` },
    share(r) { const t = this.usageSpend?.spent_micro || 0; return t ? Math.round((r.spent_micro / t) * 1000) / 10 : 0 },
    // A ranked row wears its chart color when it has its own slice, and the Other gray when folded.
    rankColor(r) {
      const s = this.spendSeries.find(x => x.id === r.id)
      return s ? `var(--sb-${(s.slot ?? 0) + 1})` : 'var(--sb-other)'
    },
    pickRankRow(r) {
      if (this.usageSpend?.stack !== 'key' || r.id === 'none') return
      this.spendFilter.key = r.id
      this.loadUsageSpend()
    },
    clearSpendFilters() { Object.assign(this.spendFilter, { group: 'day', key: '', provider: '', stack: 'key' }); this.loadUsageSpend() },
    // A run has no request to show, so only a call's row opens anything.
    feedRowClass(a) { return { 'act-static': a.kind !== 'call' } },
    // A tag's rows, with the untagged remainder as one more row: shown, never dropped.
    tagRows(key) {
      const u = this.tagUsage[key]
      return [...u.rows, ...(u.unattributed_micro ? [{ value: null, calls: null, charged_micro: u.unattributed_micro }] : [])]
    },
  },
}
</script>

<template>
<div class="pl act">
  <header class="pl-hero">
    <h1>{{ t('activity.title') }}</h1>
    <p class="pl-lede">{{ t('activity.lede', { name: activeName }) }}</p>
  </header>
  <!-- One page, two readings of the same traffic: the RAW FEED (every call, newest first)
       and the ROLLUPS (who/what/when, and spend per caller tag). They were separate sidebar
       entries, which made you leave one to answer a question about the other. -->
  <PageTabs :label="t('activity.feedLabel')" :tabs="actTabs" :current="actTab" @select="pickTab" />

  <template v-if="actTab==='feed'">
  <div class="cn-filters">
    <SelectMenu v-model="activityKey" class="act-key" size="lg" icon="key" :label="t('activity.apiKey')" :options="activityKeyOptions" @change="loadCalls" />
    <div class="seg pl-seg" role="radiogroup" :aria-label="t('activity.feedLabel')">
      <button role="radio" :aria-checked="actOkOnly" :class="{on:actOkOnly}" @click="actOkOnly=true" :title="t('activity.hideFailed')">{{ t('activity.succeeded') }} <span>{{activityOkRows.length}}</span></button>
      <button role="radio" :aria-checked="!actOkOnly" :class="{on:!actOkOnly}" @click="actOkOnly=false" :title="t('activity.includeFailed')">{{ t('activity.all') }} <span>{{activityRows.length}}</span></button>
    </div>
    <span v-if="activityCachedCount" class="pl-meta pl-push">{{ t('activity.archiveNote', { n: activityCachedCount, m: activityCallCount, calls: activityCallCount===1 ? t('activity.callsOne') : t('activity.callsMany') }) }}</span>
  </div>

  <DataTable v-if="activityShown.length" class="act-feed" :columns="feedColumns" :rows="activityShown" :row-key="a => a.kind+'-'+a.id"
             :row-class="feedRowClass" interactive surface @row-click="a => a.kind==='call' && openCall(a)">
    <template #cell-when="{ row: a }"><span class="muted" :title="a.created_at">{{when(a.created_at)}}</span></template>
    <template #cell-caller="{ row: a }"><span class="act-who">{{activityWho(a)}}<span v-if="activityOwner(a)" class="act-dim" :title="'Agent owner: '+activityAgentKey(a).created_by"> · owner {{activityOwner(a)}}</span></span>
        <span class="pl-sub"><span v-if="a.api_key_name" class="mono">{{a.api_key_name}}<template v-if="a.api_key_prefix"> · {{a.api_key_prefix}}</template></span><span v-if="a.client && a.client!=='cli'" title="reported by the runtime: attribution, not authentication"><template v-if="a.api_key_name"> · </template>via {{a.client}}</span></span></template>
    <template #cell-call="{ row: a }"><b class="act-tool">{{a.tool}}</b><span v-if="a.kind==='run'" class="act-kind" :title="a.where==='local'?t('activity.ranLocal'):t('activity.ranServer')">{{a.where||'run'}} run</span>
        <span class="pl-sub mono">{{a.action}}</span>
        <span v-if="a.tags || (a.task && (a.task.result_url||a.task.fetch_command))" class="act-extra">
          <span v-for="(v,k) in a.tags" :key="k" class="chip act-tag" :title="'X-Treg-Meta '+k+'='+v">{{k}}={{v}}</span>
          <!-- A generation task's artifact, once it succeeded: the provider's time-limited URL, or the CLI command that retrieves it (treg never downloads media). -->
          <template v-if="a.task"><a v-if="a.task.result_url" :href="a.task.result_url" target="_blank" rel="noopener" class="act-link" :title="taskArtifactTitle(a.task)" @click.stop>result ↗</a><span v-else-if="a.task.fetch_command" class="chip act-tag" :title="'retrieve it from the CLI: '+a.task.fetch_command">result via CLI</span><span v-if="a.task.result_url||a.task.fetch_command" class="act-dim"> {{a.task.ttl_note?'expires in '+a.task.ttl_note:'time-limited link'}}</span></template>
        </span></template>
    <template #cell-status="{ row: a }"><span class="act-st" :class="a.ok?'ok':'bad'">{{a.status}}</span><span v-if="a.task" class="act-st pending" :title="taskStateTitle(a.task)">{{taskStateLabel(a.task)}}</span><span v-if="a.has_result" class="act-view">Result ›</span></template>
    <template #cell-cost="{ row: a }"><span class="act-cost" :title="a.held?t('activity.holdTitle'):(a.tier==='platform'?t('activity.teamBalanceTitle'):(a.cost!=null?t('activity.estimatedTitle'):''))">
        <span v-if="a.cached" class="act-cached" :title="t('activity.cachedTitle')">{{ t('activity.cached') }}</span><span v-if="a.held" class="act-dim">hold </span>{{a.cost!=null?money(a.cost):'-'}}</span></template>
  </DataTable>
  <p v-if="callsLoaded && !activityRows.length" class="pl-empty">{{ t('activity.noActivity') }}</p>
  <p v-else-if="callsLoaded && !activityShown.length" class="pl-empty">{{ activityHasOlder ? t('activity.noneSucceeded') : t('activity.noSuccessful') }} <button class="pl-link" @click="actOkOnly=false">{{ t('activity.showAll', { n: activityRows.length }) }}</button></p>
  <button v-if="callsLoaded && activityHasOlder" class="pl-link pl-more-rows" :disabled="activityOlderBusy" @click="loadOlderActivity">{{ activityOlderBusy ? t('common.loading') : t('activity.loadOlder') }}</button>
  </template>

  <template v-if="canAdmin && actTab==='usage'">
  <!-- SPEND: money from the LEDGER, through the daily spend rollup only (never the ledger or the
       audit table on a page open). Its own request and its own range: the rollup holds a bounded
       history, and the picker goes back no further than it. -->
  <section class="us-card" :aria-busy="usageSpendBusy">
    <header class="us-card-head">
      <div>
        <h2>{{ t('activity.spend') }}</h2>
        <p class="muted">{{ t('activity.spendLede') }}<template v-if="historyFrom">{{ t('activity.historyStart', { date: historyFrom }) }}</template></p>
      </div>
      <div v-if="usageSpend && usageSpend.ready" class="us-totals">
        <div><b><Money :micro="usageSpend.spent_micro" /></b><span>{{ t('activity.spent') }}</span></div>
        <div><b>{{usageSpend.charges}}</b><span>{{usageSpend.charges === 1 ? t('activity.chargeOne') : t('activity.charges')}}</span></div>
      </div>
    </header>
    <div v-if="usageSpend && usageSpend.ready" class="us-filters">
      <div class="us-filter"><span>{{ t('activity.dateRange') }}</span>
        <DateRangePicker :model-value="spendRange" :min="usageSpend.history_from" @change="setSpendRange" /></div>
      <div class="us-filter"><span>{{ t('activity.groupby') }}</span>
        <SelectMenu v-model="spendFilter.group" icon="clock" :label="t('activity.groupby')" :options="groups" @change="loadUsageSpend" /></div>
      <div class="us-filter"><span>{{ t('activity.apiKey') }}</span>
        <SelectMenu v-model="spendFilter.key" icon="key" :label="t('activity.apiKey')" :options="spendKeyOptions" @change="loadUsageSpend" /></div>
      <div class="us-filter"><span>{{ t('activity.provider') }}</span>
        <SelectMenu v-model="spendFilter.provider" icon="plug" :label="t('activity.provider')" :options="spendProviderOptions" @change="loadUsageSpend" /></div>
      <!-- Stacking by tool only reads within one provider: across all of them it is hundreds of series. -->
      <div v-if="spendFilter.provider" class="us-filter"><span>{{ t('activity.stackBy') }}</span>
        <SelectMenu v-model="spendFilter.stack" icon="layers" :label="t('activity.stackBy')" :options="stacks" @change="loadUsageSpend" /></div>
      <button v-if="spendFilter.key || spendFilter.provider || spendFilter.group!=='day'" class="pl-link us-clear" @click="clearSpendFilters">{{ t('activity.clearFilters') }}</button>
    </div>
    <div class="us-card-body" :class="{ busy: usageSpendBusy && usageSpend }">
      <p v-if="usageSpendErr" class="pl-empty">{{usageSpendErr}}</p>
      <p v-else-if="!usageSpend" class="pl-empty">{{ t('activity.loadingSpend') }}</p>
      <p v-else-if="!usageSpend.ready" class="pl-empty">{{ t('activity.spendPrep') }}</p>
      <p v-else-if="!usageSpend.spent_micro" class="pl-empty">{{ t('activity.noCharges') }}</p>
      <template v-else>
        <SpendBars :buckets="spendBuckets" :series="spendSeries"
                   :aria-label="`Billed spend by ${usageSpend.group}: ${moneyGlance(usageSpend.spent_micro)} from ${usageSpend.from} to ${usageSpend.to}`" />
        <!-- Every series, none folded: the chart can color seven, a list can name them all. A key's
             row filters the chart to it; the chart answers "when", this list "who". -->
        <button type="button" class="us-rank-toggle" :aria-expanded="spendRankOpen" aria-controls="us-ranking" @click="spendRankOpen=!spendRankOpen">
          {{usageSpend.stack==='tool' ? t('activity.spendPerTool') : t('activity.spendPerKey')}}
          <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 6l4 4 4-4" /></svg>
        </button>
        <div id="us-ranking" class="us-ranking" :class="{ open: spendRankOpen }" :inert="!spendRankOpen"><div class="us-ranking-inner">
          <DataTable :columns="spendColumns" :rows="page(usageSpend.ranking, spendRankPage)" :row-key="r => r.id" surface
                     :interactive="usageSpend.stack==='key'" @row-click="pickRankRow">
            <template #head-name>{{usageSpend.stack==='tool' ? t('activity.colTool') : t('activity.apiKey')}}</template>
            <template #cell-name="{ row: r }"><span class="us-rank-name"><s :style="{ background: rankColor(r) }"></s><span :title="r.name">{{r.name}}</span><InfoTip v-if="r.id==='none'" :title="NO_KEY.title" :text="NO_KEY.text" /></span></template>
            <template #cell-share="{ row: r }"><span class="us-share"><i :style="{ width: share(r) + '%' }"></i></span><span class="muted">{{share(r)}}%</span></template>
            <template #cell-spend="{ row: r }"><b><Money :micro="r.spent_micro" /></b></template>
          </DataTable>
          <div v-if="usageSpend.ranking.length > PAGE" class="us-pager">
            <span class="muted">{{pageLabel(usageSpend.ranking, spendRankPage)}}</span>
            <button class="btn sm" :disabled="!spendRankPage" @click="spendRankPage--">{{ t('activity.previous') }}</button>
            <button class="btn sm" :disabled="(spendRankPage+1)*PAGE >= usageSpend.ranking.length" @click="spendRankPage++">{{ t('activity.next') }}</button>
          </div>
        </div></div>
      </template>
    </div>
  </section>

  <div class="cn-filters">
    <div class="seg pl-seg" role="radiogroup" :aria-label="t('activity.window')">
      <button v-for="d in [7,30,90]" :key="d" role="radio" :aria-checked="usageDays===d" :class="{on:usageDays===d}" @click="usageDays=d; usageToolPage=0; usageDayPage=0; loadUsageCounts(); loadTagUsage()">{{ t('activity.days', { d }) }}</button>
    </div>
    <span class="pl-meta pl-push">{{ t('activity.countsOnly') }}</span>
  </div>

  <p v-if="usageErr" class="pl-empty">{{usageErr}}</p>
  <p v-else-if="!usage" class="pl-empty">{{ t('activity.loadingCounts') }}</p>
  <p v-else-if="usage.ready === false" class="pl-empty">{{ t('activity.usagePrep') }}</p>
  <template v-else>
    <p v-if="usageCountsFrom" class="pl-meta">{{ t('activity.countedFrom', { date: usageCountsFrom }) }}</p>
    <div class="act-stats">
      <div v-for="s in [{n:usage.totals.total, l:t('activity.statTotal')}, {n:usage.totals.call, l:t('activity.statApi')}, {n:usage.totals.local_run, l:t('activity.statLocal')}, {n:usage.totals.server_run, l:t('activity.statServer')}]"
           :key="s.l" class="pl-card act-stat"><b>{{s.n}}</b><span>{{s.l}}</span></div>
    </div>

    <section class="pl-sec">
      <h2 class="pl-h"><span>{{ t('activity.byMember') }}</span><i></i><em>{{usage.by_user.length}}</em></h2>
      <DataTable :columns="memberColumns" :rows="usage.by_user" :row-key="u => u.user_email" surface :empty="t('activity.noUsage')">
        <template #cell-member="{ row: u }">{{short(u.user_email)}}</template>
        <template #cell-total="{ row: u }"><b>{{u.total}}</b></template>
      </DataTable>
    </section>

    <div class="act-pair">
      <!-- Ten rows at a time, paged here: one request already holds every row, so Next is free. -->
      <section v-if="usage.by_tool.length" class="pl-sec">
        <h2 class="pl-h"><span>{{ t('activity.topTools') }}</span><i></i><em>{{usage.by_tool.length}}</em></h2>
        <DataTable :columns="toolColumns" :rows="page(usage.by_tool, usageToolPage)" :row-key="t => t.name" surface />
        <div v-if="usage.by_tool.length > PAGE" class="us-pager">
          <span class="muted">{{pageLabel(usage.by_tool, usageToolPage)}}</span>
          <button class="btn sm" :disabled="!usageToolPage" @click="usageToolPage--">{{ t('activity.previous') }}</button>
          <button class="btn sm" :disabled="(usageToolPage+1)*PAGE >= usage.by_tool.length" @click="usageToolPage++">{{ t('activity.next') }}</button>
        </div>
      </section>
      <section v-if="usage.by_day.length" class="pl-sec">
        <h2 class="pl-h"><span>{{ t('activity.perDay') }}</span><i></i><em>{{usage.by_day.length}}</em></h2>
        <DataTable :columns="dayColumns" :rows="page(daysNewestFirst, usageDayPage)" :row-key="d => d.day" surface>
          <template #cell-day="{ row: d }"><span class="mono muted">{{d.day}}</span></template>
        </DataTable>
        <div v-if="usage.by_day.length > PAGE" class="us-pager">
          <span class="muted">{{pageLabel(usage.by_day, usageDayPage)}}</span>
          <button class="btn sm" :disabled="!usageDayPage" @click="usageDayPage--">{{ t('activity.newer') }}</button>
          <button class="btn sm" :disabled="(usageDayPage+1)*PAGE >= usage.by_day.length" @click="usageDayPage++">{{ t('activity.older') }}</button>
        </div>
      </section>
    </div>
  </template>

    <!-- SPEND BY CALLER TAG - one section per key the team has ACTUALLY SENT, not a picker.
         A dropdown hides the other dimensions behind an interaction, and the whole point of
         tagging by both customer and workspace is seeing them side by side. The list comes from
         /tag-keys (observed), so a team that never tags sees nothing here at all.

         Money here comes from the LEDGER, unlike the per-member/tool/day counts above, which
         come from the audit table and are allowed to lose rows. This is what a reselling team
         invoices from, so it has to be complete. -->
    <template v-for="key in tagKeys" :key="key">
      <section v-if="tagUsage[key]" class="pl-sec">
        <h2 class="pl-h"><span>{{ t('activity.spendBy', { key }) }}</span><i></i><em title="a caller tag from X-Treg-Meta">X-Treg-Meta</em></h2>
        <p class="cat-hint" v-html="t('activity.spendByLede', { key })"></p>
        <DataTable :columns="tagColumns" :rows="tagRows(key)" :row-key="r => r.value ?? '(untagged)'" surface :empty="t('activity.nothingTagged', { key })">
          <template #head-value>{{key}}</template>
          <template #cell-value="{ row: r }"><span v-if="r.value" class="chip">{{r.value}}</span><span v-else class="muted" title="calls carrying no value for this tag - shown, never dropped">untagged</span></template>
          <template #cell-calls="{ row: r }"><span class="muted">{{r.calls ?? '-'}}</span></template>
          <template #cell-spend="{ row: r }"><b v-if="r.value">{{money(r.charged_micro)}}</b><span v-else class="muted">{{money(r.charged_micro)}}</span></template>
        </DataTable>
      </section>
      <section v-else-if="tagUsageErr[key]" class="pl-sec">
        <h2 class="pl-h"><span>Spend by {{key}}</span><i></i></h2>
        <p class="pl-empty">{{tagUsageErr[key]}}</p>
      </section>
    </template>
  </template>
</div>
</template>
