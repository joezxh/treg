<script>
import { useDashboard } from '../state/context'
export default { setup: useDashboard }
</script>

<template>
<div class="scrim" role="dialog" aria-labelledby="share-dialog-title" aria-modal="true" v-dialog="() => { share.on=false }" @click.self="share.on=false">
      <div class="modal" style="width:min(560px,95vw)"><div class="hd"><b id="share-dialog-title">{{t('share.title')}} “{{detail.name}}”</b><button class="btn sm ico" @click="share.on=false" :aria-label="t('common.close')">✕</button></div>
        <div style="padding:16px 18px">
          <template v-if="share.sent">
            <p class="explain">{{ t('share.inviteSent', { email: share.sent.email }) }}</p>
            <p class="sub" style="margin:0 0 8px">{{ t('share.dmLink') }}</p>
            <pre class="code" style="white-space:pre-wrap;word-break:break-all">{{shareInviteUrl}}</pre>
            <div style="margin-top:12px;display:flex;gap:10px;align-items:center;flex-wrap:wrap">
              <button class="btn primary" @click="copyDetail(shareInviteUrl,'sharecopy')">⧉ {{detailCopied==='sharecopy'?t('common.copiedAlt'):t('share.copyInviteLink')}}</button>
              <span class="sub" style="margin:0;font-size:12px">{{ t('share.backupCodePrefix') }} <span class="mono">{{share.sent.code}}</span> <span class="mono">treg org join</span> {{ t('share.joinHint') }}</span>
            </div>
          </template>
          <template v-else>
            <p class="explain">{{ t('share.alreadyTeam') }}</p>
            <div v-if="share.member" class="tut-notice" style="margin:0 0 10px"><b>{{share.member.email}}</b> {{ t('share.memberNotice', { email: share.member.email }) }}</div>
            <div class="field" style="margin-bottom:10px"><input v-model="share.email" type="email" placeholder="teammate@company.com" @keyup.enter="sendShare"/></div>
            <div style="margin-bottom:10px">
              <label style="display:flex;gap:6px;align-items:center;font-size:12.5px">{{ t('share.role') }}
                <select v-model="share.role" style="background:var(--panel2);border:1px solid var(--line);color:var(--ink);border-radius:6px;padding:4px 8px;font-family:var(--mono)">
                  <option value="viewer">{{t('share.viewer')}}</option><option value="member">{{t('share.member')}}</option><option v-if="isOwner" value="admin">{{t('share.admin')}}</option>
                </select>
              </label>
            </div>
            <div style="margin-bottom:10px">
              <label style="display:flex;gap:8px;align-items:center;font-size:12.5px;cursor:pointer">
                <input type="checkbox" v-model="share.full"/> {{ t('share.fullAccessLabel') }}
              </label>
            </div>
            <p class="sub" style="margin:0 0 12px;font-size:12px">{{ t('share.fullAccessNote', { thing: detail.kind==='skill'?t('share.thisSkill'):t('share.thisTool') }) }}</p>
            <div v-if="share.err" class="banner" style="margin:0 0 10px">{{share.err}}</div>
            <button class="btn primary" @click="sendShare" :disabled="share.busy">{{share.busy?t('share.sending'):t('share.sendInvite')}}</button>
          </template>
        </div></div>
    </div>
</template>
