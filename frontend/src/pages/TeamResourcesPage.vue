<script>
import { useDashboard } from '../state/context'
import OwnToolsHeader from '../components/OwnToolsHeader.vue'
import ProviderLogo from '../components/ProviderLogo.vue'
import FilterBox from '../components/FilterBox.vue'
import { DataTable } from '../components/ui/table'

const COLUMNS = [
  { key: 'name', headerKey: 'teamResources.colName', mobile: 'primary', wrap: true },
  { key: 'kind', headerKey: 'teamResources.colType' },
  { key: 'provider', headerKey: 'teamResources.colProvider' },
  { key: 'by', headerKey: 'teamResources.colAddedBy' },
  { key: 'created', headerKey: 'teamResources.colCreated' },
  { key: 'acts', header: '', align: 'right', mobile: 'wide' },
]
export default { components: { OwnToolsHeader, ProviderLogo, FilterBox, DataTable }, setup: useDashboard,
  computed: { columns(){ return COLUMNS.map(c => c.headerKey ? { ...c, header: this.t(c.headerKey) } : c) } } }
</script>

<template>
<div class="pl own">
  <OwnToolsHeader current="resources">
    {{ t('teamResources.intro') }}
  </OwnToolsHeader>

  <div v-if="teamResourceErr" class="banner err cn-banner"><span>{{teamResourceErr}}</span><button class="btn sm ico" @click="teamResourceErr=''" :aria-label="t('teamResources.dismiss')">✕</button></div>

  <div class="cn-filters">
    <FilterBox v-model="q" :label="t('teamResources.searchPlaceholder')" :placeholder="t('teamResources.searchPlaceholder')" :register="el => setElement('search', el)" />
    <select class="pl-select" v-model="teamResourceProvider" @change="teamResourcePage=1" :aria-label="t('teamResources.provider')">
      <option value="">{{ t('teamResources.allProviders') }}</option><option v-for="p in teamResourceProviders" :key="p" :value="p">{{p}}</option>
    </select>
    <select class="pl-select" v-model="teamResourceKind" @change="teamResourcePage=1" :aria-label="t('teamResources.resourceType')">
      <option value="">{{ t('teamResources.allResourceTypes') }}</option><option v-for="k in teamResourceKinds" :key="k" :value="k">{{k}}</option>
    </select>
    <button class="pl-btn ghost pl-push" :disabled="teamResourceBusy" @click="loadTeamResources">{{teamResourceBusy ? t('teamResources.refreshing') : t('teamResources.refresh')}}</button>
  </div>

  <p v-if="teamResourceBusy" class="pl-empty">{{ t('teamResources.loading') }}</p>
  <section v-else-if="pagedTeamResources.length" class="pl-sec">
    <h2 class="pl-h"><span>{{ t('teamResources.resources') }}</span><i></i><em>{{filteredTeamResources.length}}</em></h2>
    <DataTable :columns="columns" :rows="pagedTeamResources" :row-key="r => String(r.id)" surface>
      <template #cell-name="{ row: r }"><b>{{r.display_name||t('teamResources.untitledResource')}}</b><span class="pl-sub mono" :title="r.upstream_id">{{r.upstream_id}}</span></template>
      <template #cell-kind="{ row: r }"><span class="muted">{{r.kind}}</span></template>
      <template #cell-provider="{ row: r }"><span class="pl-by"><ProviderLogo :service="r.provider" />{{r.provider}}</span></template>
      <template #cell-by="{ row: r }"><span class="muted">{{r.created_by ? short(r.created_by) : '-'}}</span></template>
      <template #cell-created="{ row: r }"><span class="muted">{{r.created_at ? when(r.created_at) : '-'}}</span></template>
      <template #cell-acts="{ row: r }"><span class="cn-links">
        <button v-if="r.provider==='fishaudio'&&r.kind==='voice'" @click="useFishVoice(r)">{{ t('teamResources.useInTts') }}</button>
        <button @click="copyTeamResourceId(r)">{{teamResourceCopied===r.id ? t('common.copied') : t('teamResources.copyId')}}</button>
        <template v-if="r.provider==='fishaudio'&&r.kind==='voice'"><button @click="beginRenameFishVoice(r)">{{ t('teamResources.rename') }}</button>
        <button class="cn-del" @click="beginDeleteFishVoice(r)">{{ t('teamResources.delete') }}</button></template>
      </span></template>
    </DataTable>
    <div v-if="teamResourcePageCount>1" class="own-pager">
      <span class="pl-meta">{{ t('teamResources.pageOf', { cur: teamResourceCurrentPage, total: teamResourcePageCount }) }}</span>
      <button class="pl-btn sm ghost" :disabled="teamResourceCurrentPage<=1" @click="teamResourcePage=teamResourceCurrentPage-1">{{ t('teamResources.previous') }}</button>
      <button class="pl-btn sm ghost" :disabled="teamResourceCurrentPage>=teamResourcePageCount" @click="teamResourcePage=teamResourceCurrentPage+1">{{ t('teamResources.next') }}</button>
    </div>
  </section>
  <p v-else class="pl-empty">{{teamResources.length ? t('teamResources.noMatch') : t('teamResources.empty')}}</p>
</div>
</template>
