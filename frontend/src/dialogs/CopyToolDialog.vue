<script>
import { useDashboard } from '../state/context'
export default { setup: useDashboard }
</script>

<template>
<div class="scrim" role="dialog" aria-labelledby="copy-tool-dialog-title" aria-modal="true" v-dialog="() => { copyTool=null }" @click.self="copyTool=null">
      <div class="modal"><div class="hd"><b id="copy-tool-dialog-title">{{t('copy.use')}} “{{copyTool.name}}”</b><button class="btn sm ico" @click="copyTool=null" :aria-label="t('common.close')">✕</button></div>
        <div style="padding:16px 18px">
          <div class="tabs"><button v-for="t in snippetTabs" :key="t" :class="{active:snippetTab===t}" @click="snippetTab=t">{{t}}</button></div>
          <p class="explain">{{ t('copy.explain', { host: copyTool.host }) }}</p>
          <div v-if="copyTool.examples && copyTool.examples.length">
            <div class="lbl">{{ t('copy.examples') }}</div>
            <div class="exrow"><span v-for="(ex,exi) in copyTool.examples" :key="exi" class="exchip" :class="{on:exPath===ex.path}" @click="pickEx(ex)"><span class="m">{{ex.method||'GET'}}</span>{{ex.note||ex.path}}</span></div>
          </div>
          <pre class="code" v-html="snip.html"></pre>
          <div style="margin-top:12px;display:flex;gap:10px;align-items:center"><button class="btn primary" @click="copy(snip.text)">⧉ {{copied?t('common.copiedAlt'):t('common.copy')}}</button><span class="sub" style="font-size:12px;margin:0"><template v-if="myToken">{{ t('copy.tokenIncluded') }}</template><template v-else><span class="mono">$TREG_TOKEN</span> {{ t('copy.tokenPlaceholder') }}</template></span></div>
        </div></div>
    </div>
</template>
