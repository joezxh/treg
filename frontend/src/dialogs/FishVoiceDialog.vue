<script>
import { useDashboard } from '../state/context'
export default { setup: useDashboard }
</script>

<template>
<div  class="scrim" role="dialog" aria-modal="true" aria-labelledby="fish-voice-dialog-title" v-dialog="closeFishVoiceDialog" @click.self="closeFishVoiceDialog">
      <div class="modal" style="width:min(470px,94vw);padding:18px 20px">
        <div class="hd"><b id="fish-voice-dialog-title">{{fishVoiceDialog.action==='rename'?t('fish.renameTitle'):t('fish.deleteTitle')}}</b><button class="btn sm ico" @click="closeFishVoiceDialog" :aria-label="t('common.close')">✕</button></div>
        <template v-if="fishVoiceDialog.action!=='delete'">
          <div class="field" style="margin-top:14px"><label>{{t('fish.voiceName')}}</label><input :ref="el => setElement('fishVoiceName', el)" v-model="fishVoiceDialog.name" maxlength="100" @keyup.enter="submitFishVoiceDialog"/></div>
        </template>
        <p v-else style="margin:14px 0 0">{{ t('fish.deleteConfirm', { name: fishVoiceDialog.voice.display_name||fishVoiceDialog.voice.upstream_id }) }}</p>
        <p v-if="fishVoiceDialog.error" class="err" style="margin:10px 0 0">{{fishVoiceDialog.error}}</p>
        <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:18px"><button class="btn sm" :disabled="fishVoiceDialog.busy" @click="closeFishVoiceDialog">{{t('common.cancel')}}</button><button class="btn sm" :class="{primary:fishVoiceDialog.action!=='delete',danger:fishVoiceDialog.action==='delete'}" :disabled="fishVoiceDialog.busy || (fishVoiceDialog.action!=='delete'&&!fishVoiceDialog.name.trim())" @click="submitFishVoiceDialog">{{fishVoiceDialog.busy?t('fish.working'):fishVoiceDialog.action==='rename'?t('fish.saveName'):t('fish.deleteTitle')}}</button></div>
      </div>
    </div>
</template>
