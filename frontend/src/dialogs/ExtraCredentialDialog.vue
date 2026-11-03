<script>
import { useDashboard } from '../state/context'
export default { setup: useDashboard }
</script>

<template>
<div class="scrim" role="dialog" aria-labelledby="extra-credential-dialog-title" aria-modal="true" v-dialog="() => { newSkill=false }" @click.self="newSkill=false">
      <div class="modal" style="width:min(680px,95vw)"><div class="hd"><b id="extra-credential-dialog-title">{{t('skill.addTitle')}}</b><button class="btn sm ico" @click="newSkill=false" :aria-label="t('common.close')">✕</button></div>
        <div style="padding:16px 18px">
          <template v-if="skillMode==='folder'">
            <p class="explain">{{t('skill.folderExplain')}}</p>
            <label class="skill-drop" v-if="!detected">
              <input type="file" webkitdirectory directory multiple @change="onSkillFolder" style="display:none"/>
              <div class="sd-ic">📁</div>
              <div><b>{{t('skill.chooseFolder')}}</b><div class="sub" style="margin:2px 0 0">{{t('skill.readsFiles')}}</div><div class="sub" style="margin:4px 0 0">{{t('skill.hiddenFolder')}}</div></div>
            </label>
            <div v-if="skillBusy && !detected" class="sub">{{t('skill.analyzing')}}</div>
            <template v-if="detected">
              <div class="sub" style="margin:0 0 8px">{{ t('skill.found', { n: detected.length }) }}</div>
              <div class="skill-item" v-for="s in detected" :key="s.name" :class="{off:!skillSel[s.name]}">
                <label class="si-head">
                  <input type="checkbox" v-model="skillSel[s.name]" :disabled="s.already"/>
                  <b>{{s.name}}</b>
                  <span class="chip" :class="s.kind==='recipe_only'?'':'oauth'">{{s.kind==='recipe_only'?t('skill.recipe'):t('skill.tool')}}</span>
                  <span v-if="s.already" class="chip">{{t('skill.already')}}</span>
                </label>
                <div class="si-body">
                  <div class="sub" style="margin:0">{{skillSummary(s)}}</div>
                  <div v-for="sec in s.secrets" :key="sec.name" class="si-sec">
                    <span class="mono">{{sec.name}}</span>
                    <span v-if="sec.present" class="si-ok">{{ t('skill.fromSource', { source: sec.source, ref: sec.ref }) }}</span>
                    <template v-else>
                      <span class="si-warn">{{ t('skill.needs', { source: sec.source, ref: sec.ref }) }}</span>
                      <input v-if="sec.source==='env'" v-model="skillVals[sec.ref]" type="password" :placeholder="t('skill.valueFor', { ref: sec.ref })" class="si-input"/>
                    </template>
                  </div>
                  <div v-for="g in s.gaps" :key="g" class="si-warn">⚠ {{g}}</div>
                  <div v-if="s.cli" class="sub" style="margin:0">{{skillCliNote(s)}}</div>
                </div>
              </div>
            </template>
            <div v-if="skillResults" style="margin-top:10px">
              <div v-for="r in skillResults" :key="r.name" class="sub" style="margin:2px 0"><span :class="r.ok?'si-ok':'si-warn'">{{r.ok?'✓':'✕'}}</span> {{r.name}}<span v-if="!r.ok"> - {{r.error}}</span></div>
            </div>
            <div v-if="skillErr" class="banner" style="margin-top:10px">{{skillErr}}</div>
            <div style="margin-top:14px;display:flex;gap:10px;align-items:center">
              <button v-if="detected" class="btn primary" @click="importSkills" :disabled="skillBusy">{{skillBusy?t('skill.registering'):t('skill.registerSelected')}}</button>
              <button v-if="detected" class="btn" @click="detected=null;skillFiles=[];skillResults=null;skillErr=''">{{t('skill.chooseAnother')}}</button>
              <a href="#" class="adv-link" @click.prevent="skillMode='json'">{{t('skill.advancedJson')}}</a>
            </div>
          </template>
          <template v-else>
            <p class="explain">{{t('skill.jsonExplain')}} <a href="#" class="adv-link" @click.prevent="skillMode='folder'">{{t('skill.backToFolder')}}</a></p>
            <textarea v-model="skillJson" spellcheck="false" style="width:100%;height:260px;background:var(--bg);border:1px solid var(--line);color:var(--ink);border-radius:8px;padding:12px;font-family:var(--mono);font-size:12px;resize:vertical"></textarea>
            <div v-if="skillErr" class="banner" style="margin-top:10px">{{skillErr}}</div>
            <button class="btn primary" style="margin-top:10px" @click="addSkill" :disabled="skillBusy">{{skillBusy?t('skill.registering'):t('skill.register')}}</button>
          </template>
        </div></div>
    </div>
</template>
