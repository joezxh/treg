<script setup lang="ts">
// The Manual tab of "Publish a video to your TikTok profile". Every field and line in step 2 is
// one TikTok's Content Sharing Guidelines require (src/tiktokPost.ts). The video never reaches
// treg: the preview plays from the local file, and after Post the browser PUTs the bytes to
// TikTok's own upload URL. treg relays only the creator_info, init and status calls.
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useDashboard } from '../state/context'
import {
  blocker, brandedDisabled, BRANDED_PRIVATE, chunkPlan, declaration, emptyForm, fileProblem,
  interactions, labelPrompt, PICK_ONE, postInfo, privacyOptions, tiktokWords, tooLong,
  uploadUrlOk, VIDEO_TYPES, type Creator, type Form,
} from '../tiktokPost'

type Conn = { name: string, provider: string, resource_name?: string, capabilities?: string[] }
type Phase = 'pick' | 'details' | 'uploading' | 'processing' | 'done' | 'failed'

const d = useDashboard()
const tiktoks = computed<Conn[]>(() => (d.connections || []).filter((c: Conn) => c.provider === 'tiktok'))
const accounts = computed(() => tiktoks.value.filter(c => (c.capabilities || []).includes('post')))
const account = ref('')
const creator = ref<Creator | null>(null)
const file = ref<File | null>(null)
const preview = ref('')
const seconds = ref<number | null>(null)
const form = ref<Form>(emptyForm(''))
const phase = ref<Phase>('pick')
const err = ref('')
const progress = ref('')
const postId = ref('')
let ticket = 0
let poll = 0  // a status loop runs only while its number is current
let timer: ReturnType<typeof setTimeout> | null = null

const fileErr = computed(() => file.value ? fileProblem(file.value) : '')
const lengthErr = computed(() => creator.value && tooLong(creator.value, seconds.value)
  ? `This video is ${seconds.value} s. TikTok allows ${creator.value.max_video_post_duration_sec} s for this account.` : '')
const canNext = computed(() => !!file.value && !fileErr.value && !lengthErr.value && !!creator.value?.ok)
const problem = computed(() => blocker(creator.value, form.value, seconds.value))
const privacy = computed(() => creator.value ? privacyOptions(creator.value, form.value) : [])
const boxes = computed(() => creator.value ? interactions(creator.value) : [])
const profile = computed(() => postId.value && creator.value?.creator_username
  ? `https://www.tiktok.com/@${creator.value.creator_username}/video/${postId.value}` : '')

// One TikTok call through treg, on the chosen connection's tool. TikTok answers {data, error};
// treg's own refusals (no balance, no access) answer {detail}.
async function tiktok(path: string, body: object) {
  const r = await fetch(`/call/${encodeURIComponent(account.value)}/${path}`, {
    method: 'POST', credentials: 'include',
    headers: { ...d.headers(), 'content-type': 'application/json; charset=UTF-8' },
    body: JSON.stringify(body),
  })
  let j: any = null
  try { j = await r.json() } catch { /* not JSON */ }
  if (j?.error && j.error.code && j.error.code !== 'ok') throw new Error(tiktokWords(j.error))
  if (!r.ok) {
    const detail = j?.detail
    throw new Error(typeof detail === 'string' ? detail : detail?.message || `treg answered ${r.status}`)
  }
  return j?.data || {}
}

async function loadCreator() {
  const mine = ++ticket
  creator.value = null; err.value = ''
  if (!account.value) return
  try {
    const c = await tiktok('v2/post/publish/creator_info/query/', {})
    if (mine === ticket) creator.value = { ok: true, ...c }
  } catch (e: any) {
    if (mine === ticket) creator.value = { ok: false, error: { code: 'error', message: e.message } }
  }
}

function pickFile(ev: Event) {
  const f = (ev.target as HTMLInputElement).files?.[0] || null
  if (preview.value) URL.revokeObjectURL(preview.value)
  file.value = f; seconds.value = null
  preview.value = f && !fileProblem(f) ? URL.createObjectURL(f) : ''
}

function setDisclose(on: boolean) {
  form.value.disclose = on
  if (!on) { form.value.your_brand = false; form.value.branded_content = false }
}

async function post() {
  if (problem.value || !file.value || phase.value !== 'details') return
  const f = file.value
  err.value = ''; phase.value = 'uploading'; progress.value = 'Starting…'
  try {
    const plan = chunkPlan(f.size)
    const init = await tiktok('v2/post/publish/video/init/', { post_info: postInfo(form.value), source_info: plan.source_info })
    if (!uploadUrlOk(init.upload_url || '')) throw new Error('TikTok gave an upload address that is not TikTok’s. Nothing was sent.')
    for (const [i, r] of plan.ranges.entries()) {
      progress.value = `Uploading to TikTok: part ${i + 1} of ${plan.ranges.length}`
      const put = await fetch(init.upload_url, {
        method: 'PUT', body: f.slice(r.start, r.end + 1),
        headers: { 'content-type': f.type || 'video/mp4', 'content-range': `bytes ${r.start}-${r.end}/${f.size}` },
      })
      if (!put.ok) throw new Error(`TikTok refused the upload (${put.status}).`)
    }
    phase.value = 'processing'
    follow(init.publish_id, Date.now(), ++poll)
  } catch (e: any) {
    err.value = e.message || String(e)
    phase.value = 'details'
  }
}

// TikTok processes the video after the upload; ask every 5 seconds for up to 10 minutes.
function follow(publishId: string, since: number, mine: number) {
  timer = setTimeout(async () => {
    try {
      const s = await tiktok('v2/post/publish/status/fetch/', { publish_id: publishId })
      if (mine !== poll) return
      if (s.status === 'PUBLISH_COMPLETE') {
        postId.value = (s.publicaly_available_post_id || [])[0] || ''
        phase.value = 'done'; return
      }
      if (s.status === 'FAILED') { err.value = tiktokWords({ code: s.fail_reason }); phase.value = 'failed'; return }
    } catch { /* ask again */ }
    if (mine === poll && Date.now() - since < 600_000) follow(publishId, since, mine)
  }, 5000)
}

function again() {
  poll++
  if (timer) clearTimeout(timer)
  if (preview.value) URL.revokeObjectURL(preview.value)
  file.value = null; preview.value = ''; seconds.value = null
  form.value = emptyForm(''); postId.value = ''; err.value = ''; phase.value = 'pick'
}

watch(accounts, list => {
  if (!list.some(c => c.name === account.value)) account.value = list[0]?.name || ''
}, { immediate: true })
watch(account, () => { form.value = emptyForm(form.value.title); void loadCreator() }, { immediate: true })
onBeforeUnmount(() => {
  poll++
  if (timer) clearTimeout(timer)
  if (preview.value) URL.revokeObjectURL(preview.value)
})
</script>

<template>
  <div class="ttp" data-testid="tt-form">
    <div v-if="!accounts.length" class="banner" style="margin:0" data-testid="tt-connect">
      <template v-if="tiktoks.length">{{t('ttk.readNoPublish')}} <b>{{t('ttk.readPublish')}}</b>.</template>
      <template v-else>{{t('ttk.connectToPost')}} <b>{{t('ttk.readPublish')}}</b>.</template>
      <div style="margin-top:10px"><button class="btn sm primary" @click="d.openProvider('tiktok'); d.closeEpTry()">{{t('ttk.connectTikTok')}}</button></div>
    </div>

    <template v-else>
      <div v-if="accounts.length > 1 && (phase === 'pick' || phase === 'details')" class="field" style="max-width:520px;margin-bottom:12px">
        <label>{{t('ttk.account')}}</label>
        <select v-model="account" data-testid="tt-account">
          <option v-for="c in accounts" :key="c.name" :value="c.name">{{ c.resource_name || c.name }} ({{ c.name }})</option>
        </select>
      </div>

      <div class="who" v-if="creator && creator.ok" data-testid="tt-creator">
        <img v-if="creator.creator_avatar_url" :src="creator.creator_avatar_url" alt="" referrerpolicy="no-referrer">
        <div><div class="lbl">{{t('ttk.postingTo')}}</div><strong>{{ creator.creator_nickname }}</strong> <span class="muted" v-if="creator.creator_username">@{{ creator.creator_username }}</span></div>
      </div>
      <p v-else-if="creator" class="err">{{t('ttk.cannotPost')}} {{ creator.error?.message }}</p>
      <p v-else class="sub">{{t('ttk.loadingAccount')}}</p>

      <!-- STEP 1: choose the video; it plays here from your computer, nothing is uploaded yet -->
      <template v-if="phase === 'pick'">
        <div class="lbl">{{t('ttk.step1Video')}}</div>
        <input type="file" :accept="VIDEO_TYPES.join(',')" @change="pickFile" data-testid="tt-file">
        <p v-if="fileErr" class="err">{{ fileErr }}</p>
        <video v-if="preview" :src="preview" controls playsinline preload="metadata" class="pv" data-testid="tt-preview"
               @loadedmetadata="seconds = Math.round(($event.target as HTMLVideoElement).duration)"></video>
        <p v-if="lengthErr" class="err">{{ lengthErr }}</p>
        <p class="muted small">{{t('ttk.staysLocal')}}</p>
        <button class="btn primary" :disabled="!canNext" @click="phase = 'details'" data-testid="tt-next">{{t('ttk.next')}}</button>
      </template>

      <!-- STEP 2: TikTok's required post settings; nothing is preset for you -->
      <form v-else-if="phase === 'details' || phase === 'uploading'" class="fields" @submit.prevent="post">
        <div class="lbl">{{t('ttk.step2Settings')}}</div>
        <video :src="preview" controls playsinline preload="metadata" class="pv small-pv"></video>

        <label class="lbl" for="tt-title">{{t('ttk.title')}}</label>
        <textarea id="tt-title" v-model="form.title" maxlength="2200" rows="3" :disabled="phase !== 'details'"></textarea>

        <label class="lbl" for="tt-privacy">{{t('ttk.whoCanView')}}</label>
        <select id="tt-privacy" v-model="form.privacy_level" :disabled="phase !== 'details'" data-testid="tt-privacy">
          <option value="" disabled>{{t('ttk.select')}}</option>
          <option v-for="o in privacy" :key="o.value" :value="o.value" :disabled="o.disabled"
                  :title="o.disabled ? BRANDED_PRIVATE : ''">{{ o.label }}</option>
        </select>

        <div class="lbl">{{t('ttk.allowUsers')}}</div>
        <div class="checks">
          <label v-for="b in boxes" :key="b.key" :class="{ off: b.disabled }"
                 :title="b.disabled ? t('ttk.turnedOff') : ''">
            <input type="checkbox" v-model="form[b.key]" :disabled="b.disabled || phase !== 'details'"> {{ b.label }}
          </label>
        </div>

        <div class="disclose">
          <label class="switch">
            <input type="checkbox" :checked="form.disclose" :disabled="phase !== 'details'"
                   @change="setDisclose(($event.target as HTMLInputElement).checked)" data-testid="tt-disclose">
            <span><strong>{{t('ttk.disclose')}}</strong><br>
            <span class="muted">{{t('ttk.discloseNote')}}</span></span>
          </label>
          <div v-if="form.disclose" class="checks col">
            <label><input type="checkbox" v-model="form.your_brand"> <span><strong>{{t('ttk.yourBrand')}}</strong><br><span class="muted">{{t('ttk.yourBrandNote')}}</span></span></label>
            <label :class="{ off: brandedDisabled(form) }" :title="brandedDisabled(form) ? BRANDED_PRIVATE : ''">
              <input type="checkbox" v-model="form.branded_content" :disabled="brandedDisabled(form)">
              <span><strong>{{t('ttk.brandedContent')}}</strong><br><span class="muted">{{t('ttk.brandedContentNote')}}</span></span>
            </label>
            <p v-if="brandedDisabled(form)" class="muted small">{{ BRANDED_PRIVATE }}</p>
            <p v-if="labelPrompt(form)" class="note">{{ labelPrompt(form) }}</p>
          </div>
        </div>

        <label class="switch aigc">
          <input type="checkbox" v-model="form.is_aigc" :disabled="phase !== 'details'">
          <span><strong>{{t('ttk.aigc')}}</strong><br><span class="muted">{{t('ttk.aigcNote')}}</span></span>
        </label>

        <p class="consent" data-testid="tt-consent"><template v-for="part in declaration(form)" :key="part.text"><a v-if="part.href" :href="part.href" target="_blank" rel="noopener">{{ part.text }}</a><template v-else>{{ part.text }}</template></template></p>
        <p class="muted small">{{t('ttk.afterPost')}}</p>
        <div class="actions">
          <button class="btn" type="button" :disabled="phase !== 'details'" @click="phase = 'pick'">{{t('ttk.back')}}</button>
          <span :title="problem === PICK_ONE ? PICK_ONE : ''">
            <button class="btn primary" type="submit" :disabled="!!problem || phase !== 'details'" data-testid="tt-post">{{ phase === 'uploading' ? t('ttk.posting') : t('ttk.post') }}</button>
          </span>
          <span v-if="phase === 'uploading'" class="muted small">{{ progress }}</span>
          <span v-else-if="problem" class="muted small" data-testid="tt-blocker">{{ problem }}</span>
        </div>
        <p v-if="err" class="err" role="alert" data-testid="tt-error">{{ err }}</p>
      </form>

      <div v-else class="state" :class="phase" data-testid="tt-state">
        <template v-if="phase === 'processing'">
          <strong>{{t('ttk.processing')}}</strong>
          <span>{{t('ttk.processingNote')}}</span>
        </template>
        <template v-else-if="phase === 'done'">
          <strong>{{t('ttk.onTikTok')}}</strong>
          <a v-if="profile" :href="profile" target="_blank" rel="noopener">{{t('ttk.openOnTikTok')}}</a>
          <span v-else>{{t('ttk.privateNoLink')}}</span>
        </template>
        <template v-else>
          <strong>{{t('ttk.notPublished')}}</strong>
          <span>{{ err }}</span>
        </template>
        <div v-if="phase !== 'processing'"><button class="btn sm" @click="again">{{t('ttk.postAnother')}}</button></div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.ttp{display:flex;flex-direction:column;gap:10px;max-width:520px}
.pv{width:100%;max-height:420px;border-radius:var(--r);background:#000;object-fit:contain}
.small-pv{max-height:260px}
.fields{display:flex;flex-direction:column;gap:8px}
.fields textarea,.fields select{width:100%;font:inherit;padding:9px 10px;border-radius:var(--rb);border:1px solid var(--line);background:var(--panel);color:var(--ink)}
.who{display:flex;gap:10px;align-items:center;padding:10px 12px;border:1px solid var(--line);border-radius:var(--r);background:var(--panel)}
.who img{width:36px;height:36px;border-radius:50%}
.lbl{font-size:10.5px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;margin-top:8px}
.checks{display:flex;gap:18px;flex-wrap:wrap}
.checks.col{flex-direction:column;gap:10px;margin:10px 0 0 26px}
.checks label{display:flex;gap:8px;align-items:flex-start;font-size:13.5px}
.checks label.off{opacity:.45}
.disclose{border:1px solid var(--line);border-radius:var(--r);padding:12px;margin-top:10px}
.switch{display:flex;gap:10px;align-items:flex-start;font-size:13.5px}
.aigc{margin-top:8px}
.consent{font-size:13px;margin-top:12px}
.note{font-size:13px;color:var(--amber)}
.small{font-size:12px}
.actions{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:6px}
.state{display:flex;flex-direction:column;gap:6px;padding:16px;border:1px solid var(--line);border-radius:var(--r);background:var(--panel)}
.state.done strong{color:var(--green)} .state.failed strong{color:var(--red)}
p.err{color:var(--red);margin:0}
</style>
