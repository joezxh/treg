<script>
import { useDashboard } from '../state/context'
export default { setup: useDashboard }
</script>

<template>
<div class="scrim" role="dialog" aria-labelledby="edit-tool-dialog-title" aria-modal="true" v-dialog="() => { newTool=false;toolErr='' }" @click.self="newTool=false;toolErr=''">
      <div class="modal" style="width:min(620px,95vw)"><div class="hd"><b id="edit-tool-dialog-title">{{tForm.id?t('edit.edit'):t('edit.add')}}{{tForm.mode==='cli'?'CLI':t('edit.endpoint')}}</b><button class="btn sm" @click="newTool=false;toolErr=''" :aria-label="t('common.close')">✕</button></div>
        <div style="padding:16px 18px">
          <template v-if="tForm.mode!=='cli'">
            <p class="explain">{{t('edit.endpointExplain')}}</p>
            <div class="frow"><label>{{t('edit.name')}}</label><input v-model="tForm.name" placeholder="e.g. openai"/></div>
            <p v-if="tForm.id && tForm.name.trim() && tForm.name.trim()!==tForm.oldName" class="sub" style="font-size:11px;margin-top:-4px">{{ t('edit.renameNote', { name: tForm.oldName }) }}</p>
            <div class="frow"><label>{{t('edit.baseUrl')}}</label><input v-model="tForm.base_url" placeholder="https://api.openai.com"/></div>
            <div class="lbl" style="margin-top:12px;display:flex;align-items:center">{{t('edit.bindings')}} <button class="btn sm" @click="addBinding" style="margin-left:auto">{{t('edit.addBinding')}}</button></div>
            <div class="bindrow" v-for="(b,i) in tForm.bindings" :key="i">
              <select v-model="b.secret_id" class="msel">
                <option v-if="!secrets.length" :value="null" disabled>{{t('edit.addSecret')}}</option>
                <option v-for="s in secrets" :key="s.id" :value="s.id">{{s.name}}</option>
              </select>
              <select v-model="b.injector" class="msel"><option>env</option><option>oauth</option></select>
              <select v-model="b.location" class="msel"><option value="header">header</option><option value="query">query</option></select>
              <input v-model="b.name" placeholder="field (Authorization)" class="bindinput"/>
              <input v-model="b.format" placeholder="Bearer {secret}" class="bindinput"/>
              <input v-if="b.injector==='oauth'" v-model="b.secret_field" placeholder="token" class="bindinput" style="max-width:80px;min-width:70px"/>
              <button v-if="tForm.bindings.length>1" class="btn sm" @click="removeBinding(i)" :aria-label="t('edit.removeBinding')">✕</button>
            </div>
            <p class="sub" style="font-size:11px">{{ t('edit.secretBecomes', { secret: '{secret}' }) }}</p>
            <div class="frow" v-if="projects.length"><label>{{t('edit.project')}}</label>
              <select v-model="tForm.project" class="msel">
                <option :value="null">{{t('edit.teamWide')}}</option>
                <option v-for="p in projects" :key="p.id" :value="p.slug">{{p.name}}</option>
              </select></div>
            <p v-if="projects.length" class="sub" style="font-size:11px;margin-top:-4px">{{t('edit.projectNote')}}</p>
          </template>
          <template v-else>
            <p class="explain">{{ t('edit.cliExplain', { cli: tForm.cli.bin || '<cli>' }) }}</p>
            <div class="frow"><label>{{t('edit.cliCommand')}}</label><input v-model="tForm.cli.bin" :disabled="!!tForm.id" placeholder="e.g. gh" style="font-family:var(--mono)"/></div>
            <div class="frow"><label>{{t('edit.package')}}</label><input v-model="tForm.cli.package" placeholder="how to install it, e.g. brew install gh (optional)"/></div>
            <div class="frow"><label>{{t('edit.apiBaseUrl')}}</label><input v-model="tForm.base_url" placeholder="https://api.github.com — the provider behind the CLI"/></div>
            <div class="lbl" style="margin-top:14px;display:flex;align-items:center">{{t('edit.bindingKey')}} <button class="btn sm" @click="tForm.cli.inject.push({via:'env',name:'',secret_id:null})" style="margin-left:auto">{{t('edit.addEnvVar')}}</button></div>
            <div class="bindrow" v-for="(inj,i) in tForm.cli.inject" :key="'inj'+i">
              <select v-model="inj.secret_id" class="msel">
                <option v-if="!secrets.length" :value="null" disabled>{{t('edit.addSecret')}}</option>
                <option v-for="s in secrets" :key="s.id" :value="s.id">{{s.name}}</option>
              </select>
              <input v-model="inj.name" placeholder="env var, e.g. GH_TOKEN" class="bindinput" style="font-family:var(--mono)"/>
              <button v-if="tForm.cli.inject.length>1" class="btn sm" @click="tForm.cli.inject.splice(i,1)" :aria-label="t('edit.removeEnvVar')">✕</button>
            </div>
            <div class="frow" v-if="projects.length"><label>{{t('edit.project')}}</label>
              <select v-model="tForm.project" class="msel">
                <option :value="null">{{t('edit.teamWide')}}</option>
                <option v-for="p in projects" :key="p.id" :value="p.slug">{{p.name}}</option>
              </select>
            </div>
            <label class="cliopt"><span class="tswitch"><input type="checkbox" v-model="tForm.cli.enabled"/><span class="knob"></span></span><span style="flex:1;min-width:0"><b>{{t('edit.localRuns')}}</b><span class="sub" style="display:block;margin-top:2px">{{tForm.cli.enabled?t('edit.localOn',{cli:tForm.cli.bin||'it'}):t('edit.localOff')}}</span></span></label>
            <div class="lbl" style="margin-top:14px;display:flex;align-items:center">{{t('edit.denyList')}} <button class="btn sm" @click="tForm.cli.deny.push('')" style="margin-left:auto">{{t('edit.addPattern')}}</button></div>
            <p class="sub" style="font-size:11px;margin:4px 0 8px">{{ t('edit.denyHelp', { a: '(^|\\s)run(\\s|$)', b: '--publish-url\\b' }) }}</p>
            <div class="bindrow" v-for="(p,i) in tForm.cli.deny" :key="'dn'+i">
              <input v-model="tForm.cli.deny[i]" placeholder="regex, e.g. (^|\s)run(\s|$)" class="bindinput" style="font-family:var(--mono)"/>
              <button class="btn sm" @click="tForm.cli.deny.splice(i,1)" :aria-label="t('edit.removePattern')">✕</button>
            </div>
            <p class="sub" v-if="!tForm.cli.deny.length && !(tForm.cli.deny_defaults && catalogExtra.length)" style="font-size:11px;margin:4px 0 8px;color:var(--warn,#e0a458)">{{ t('edit.noGuardrails', { cli: tForm.cli.bin || 'CLI' }) }}</p>
            <label class="cliopt" v-if="catalogExtra.length"><span class="tswitch"><input type="checkbox" v-model="tForm.cli.deny_defaults"/><span class="knob"></span></span><span style="flex:1;min-width:0"><b>{{t('edit.catalogDefaults')}}</b><span class="sub" style="display:block;margin-top:2px">{{ t('edit.catalogNote', { cli: tForm.cli.bin }) }}</span></span></label>
            <template v-if="tForm.cli.deny_defaults && catalogExtra.length">
              <div class="bindrow" v-for="(cp,ci) in catalogExtra" :key="'cd'+ci">
                <input :value="cp" disabled class="bindinput" style="font-family:var(--mono);opacity:.55"/>
                <span class="chip" :title="t('edit.fromCatalogTitle')">{{t('edit.catalog')}}</span>
              </div>
            </template>
          </template>
          <div v-if="toolErr" class="banner">{{toolErr}}</div>
          <button class="btn primary" style="margin-top:6px" @click="saveTool" :disabled="toolBusy">{{toolBusy?t('edit.saving'):(tForm.id?t('edit.saveChanges'):(tForm.mode==='cli'?t('edit.createCli'):t('edit.createEndpoint')))}}</button>
        </div></div>
    </div>
</template>
