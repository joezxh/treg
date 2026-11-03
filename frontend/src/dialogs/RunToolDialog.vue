<script>
import { useDashboard } from '../state/context'
export default { setup: useDashboard }
</script>

<template>
<div class="scrim" role="dialog" aria-labelledby="run-tool-dialog-title" aria-modal="true" v-dialog="() => { tryTool=null }" @click.self="tryTool=null" style="place-items:stretch;justify-items:end">
      <div class="drawer"><div class="hd" style="padding:15px 18px;border-bottom:1px solid var(--line)"><b id="run-tool-dialog-title">{{t('run.use')}} “{{tryTool.name}}”</b><button class="btn sm" @click="tryTool=null" :aria-label="t('common.close')">✕</button></div>
        <div style="padding:16px 18px;overflow:auto">
          <div v-if="canCall(tryTool) && canRun(tryTool)" class="exrow" style="margin-bottom:12px">
            <span class="exchip" :class="{on:useMode==='call'}" @click="useMode='call'"><span class="m">HTTP</span>{{t('run.apiCall')}}</span>
            <span class="exchip" :class="{on:useMode==='run'}" @click="useMode='run'"><span class="m">CLI</span>{{t('run.runOnServer')}}</span>
          </div>

          <template v-if="useMode==='call'">
            <p class="explain">{{ t('run.explainCall', { host: tryTool.host }) }}</p>
            <div v-if="tryTool.examples && tryTool.examples.length">
              <div class="lbl">{{ t('run.examplesFill') }}</div>
              <div class="exrow"><span v-for="(ex,exi) in tryTool.examples" :key="exi" class="exchip" :class="{on:tryPath===ex.path}" @click="tryPath=ex.path; tryMethod=ex.method||'GET'"><span class="m">{{ex.method||'GET'}}</span>{{ex.note||ex.path}}</span></div>
            </div>
            <div class="field"><select v-model="tryMethod"><option>GET</option><option>POST</option><option>PUT</option><option>DELETE</option></select><input v-model="tryPath" :placeholder="t('run.pathPlaceholder')" @keyup.enter="runTry"/></div>
            <textarea v-if="tryMethod!=='GET'" v-model="tryBody" :placeholder="t('run.bodyPlaceholder')" rows="3" style="width:100%;margin-top:8px;background:var(--bg);border:1px solid var(--line);color:var(--ink);border-radius:var(--rb);padding:8px;font-family:var(--mono);font-size:12.5px"></textarea>
            <div class="muted" style="font-size:12px;margin:6px 0 12px">→ {{tryMethod}} {{tryTool.base_url}}/{{tryPath}}</div>
            <button class="btn primary" @click="runTry" :disabled="trying">{{trying?t('run.sending'):t('run.send')}}</button>
            <div v-if="tryResp!==null" style="margin-top:14px"><div class="muted" style="font-size:12px;margin-bottom:6px">{{ t('run.response') }} <span class="badge" :class="(tryStatus>0&&tryStatus<400)?'ok':'invalid'">{{tryStatus||'ERR'}}</span> · {{tryMs}}ms · {{ t('run.keyInjectedByRegistry') }}</div><pre>{{tryResp}}</pre></div>
          </template>

          <template v-if="useMode==='run'">
            <p class="explain">{{ t('run.explainRun', { bin: (tryTool.cli&&tryTool.cli.bin)||tryTool.name, name: tryTool.name }) }}</p>
            <div class="field"><input v-model="runArgsStr" :placeholder="t('run.cliArgsPlaceholder')" @keyup.enter="doRun" style="width:100%"/></div>
            <div class="muted" style="font-size:12px;margin:6px 0 12px">→ {{(tryTool.cli&&tryTool.cli.bin)||tryTool.name}} {{runArgsStr}}</div>
            <button class="btn primary" @click="doRun" :disabled="running">{{running?t('run.running'):t('run.run')}}</button>
            <div v-if="runOut" style="margin-top:14px">
              <div class="muted" style="font-size:12px;margin-bottom:6px">{{ t('run.result') }} <span class="badge" :class="runOut.exit_code===0?'ok':'invalid'">exit {{runOut.exit_code}}</span> · {{runOut.duration_ms}}ms<span v-if="runOut.timed_out"> · {{ t('run.timedOut') }}</span> · {{ t('run.keyInjectedServerSide') }}</div>
              <pre v-if="runOut.stdout">{{runOut.stdout}}</pre>
              <pre v-if="runOut.stderr" style="opacity:.75">{{runOut.stderr}}</pre>
              <pre v-if="runOut.detail" style="opacity:.75">{{runOut.detail}}</pre>
            </div>
          </template>
        </div></div>
    </div>
</template>
