<script>
import { useDashboard } from '../state/context'
export default { setup: useDashboard }
</script>

<template>
<div  class="scrim" role="dialog" aria-labelledby="resource-picker-dialog-title" aria-modal="true" v-dialog="() => { resPick=null }" @click.self="resPick=null">
      <div class="modal" style="padding:16px">
        <h3 id="resource-picker-dialog-title" style="margin:0 0 10px">{{ t('res.choose', { art: article(resPick.label), label: resPick.label }) }}</h3>
        <p class="sub" v-if="resPick.scoped" style="margin:0 0 10px">{{ t('res.scoped', { label: resPick.label }) }}</p>
        <p class="sub" v-else style="margin:0 0 10px">{{ t('res.default', { label: resPick.label }) }}</p>
        <div v-if="resPick.loading" class="ttable-wrap">
          <div style="padding:22px;text-align:center;color:var(--muted);font-family:var(--mono);font-size:12.5px">
            <span class="spin" aria-hidden="true"></span> {{ t('res.asking', { plural: resPick.plural }) }}
          </div>
        </div>
        <div v-else-if="resPick.err" class="banner" style="margin:0 0 10px">{{resPick.err}}</div>
        <p class="sub" v-else-if="!resPick.rows.length" style="margin:0 0 10px">{{ t('res.noneFound', { plural: resPick.plural }) }}</p>
        <div class="ttable-wrap" v-else><table class="ttable">
          <tr v-for="r in resPick.rows" :key="r.id">
            <td class="tn"><b>{{r.label||r.id}}</b><span class="sub" style="display:block;font-size:11px">{{r.id}}</span></td>
            <td class="tx"><button class="btn sm" :class="{primary:r.id===resPick.selected}" @click="chooseResource(r)">{{r.id===resPick.selected?t('res.current'):t('res.useThis')}}</button></td>
          </tr>
        </table></div>
        <div style="margin-top:12px;text-align:right"><button class="btn sm" @click="resPick=null">{{t('common.close')}}</button></div>
      </div>
    </div>
</template>
