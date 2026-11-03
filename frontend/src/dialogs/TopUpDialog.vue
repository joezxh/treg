<script>
import { useDashboard } from '../state/context'
export default { setup: useDashboard }
</script>

<template>
<div  class="scrim" role="dialog" aria-labelledby="top-up-dialog-title" aria-modal="true" v-dialog="() => { topupOpen=false }" @click.self="topupOpen=false">
      <div class="modal" style="padding:18px 20px;width:min(620px,94vw)">
        <div style="display:flex;justify-content:space-between;align-items:center">
          <h3 id="top-up-dialog-title" style="margin:0">{{t('topup.title')}}</h3>
          <button class="btn sm" @click="topupOpen=false" :aria-label="t('common.close')">✕</button>
        </div>
        <p class="sub" style="margin:6px 0 14px">{{ t('topup.sub') }}</p>
        <div class="fundgrid fundgrid-5">
          <button v-for="p in billing.topup.presets" :key="p" class="fundcard" :class="{sel:topupPick===p}" :disabled="billingBusy" @click="topupPick=p">
            <b>${{p}}</b>
            <!-- The bonus is named ON the qualifying buttons: the amount is chosen here, and a
                 preset that quietly forfeits a bonus is the whole failure this is meant to prevent.
                 The referral bonus (refPresetBonus) stacks on the tier bonus. -->
            <span v-if="tierBonus(p)" style="color:var(--green)">{{ t('topup.bonus', { amount: money(tierBonus(p)) }) }}</span>
            <span v-else-if="refPresetBonus(p)" style="color:var(--green)">{{ t('topup.bonus', { amount: money(refPresetBonus(p)) }) }}</span>
          </button>
          <button class="fundcard" :class="{sel:topupPick==='other'}" :disabled="billingBusy" @click="pickOther()">
            <b>{{t('topup.other')}}</b>
          </button>
        </div>
        <div v-if="topupPick==='other'" style="margin-top:12px">
          <div style="display:flex;align-items:center;border:1px solid var(--line);border-radius:var(--rb);background:var(--bg);padding:0 14px">
            <span style="font-family:var(--mono);font-size:22px;color:var(--muted)">$</span>
            <input type="number" :min="billing.topup.min_usd" :max="billing.topup.max_usd" step="1" v-model.number="topupOther" placeholder="0" autocomplete="off" data-lpignore="true"
                   style="flex:1;border:0;background:transparent;color:var(--ink);font-family:var(--mono);font-size:22px;font-weight:700;padding:12px 8px;outline:none;min-width:0"/>
          </div>
          <p class="sub" style="margin:6px 0 0">{{ t('topup.wholeDollars', { min: billing.topup.min_usd, max: billing.topup.max_usd.toLocaleString() }) }}</p>
        </div>

        <!-- Auto top-up. Read-only line when the team already has a mandate; otherwise the toggle. -->
        <div style="margin-top:14px;border:1px solid var(--line);border-radius:var(--rb);padding:10px 12px;background:var(--panel2)">
          <template v-if="billing.autotopup.enabled||billing.autotopup.consented_at">
            <template v-if="billing.autotopup.disabled_reason==='authentication_required'">
              <b style="font-size:12.5px">{{ t('topup.autoPaused') }}</b>
              <span class="sub" style="margin:0">{{ t('topup.autoPausedNote') }}</span>
            </template>
            <template v-else>
              <b style="font-size:12.5px">{{ billing.autotopup.enabled ? t('topup.autoOn') : t('topup.autoSetUp') }}</b>
              <span class="sub" style="margin:0">{{ t('topup.autoManage') }}</span>
            </template>
          </template>
          <template v-else>
            <label style="display:flex;gap:10px;align-items:flex-start;cursor:pointer">
              <span class="tswitch" style="margin-top:2px"><input type="checkbox" v-model="topupAuto"/><span class="knob"></span></span>
              <span>
                <b style="font-size:12.5px">{{ t('topup.autoToggle', { state: topupAuto ? t('topup.on') : t('topup.off') }) }}</b>
                <!-- The mandate. Not decoration: an off-session charge with no recorded agreement to
                     THESE numbers is an unauthorized charge under PSD2/SCA. The numbers are the
                     server defaults ($20 when below $5), shown here in full; the billing page's
                     Edit panel changes them. Not the top-up amount: a $200 buyer does not want
                     $200 refills. -->
                <span class="sub" style="display:block;margin:2px 0 0">
                  <template v-if="topupAuto">{{ t('topup.autoAuthorize', { amount: '$'+autoAmount, threshold: '$'+autoThreshold, perHour: autoPerHour }) }}</template>
                  <template v-else>{{ t('topup.autoOffNote') }}</template>
                </span>
              </span>
            </label>
          </template>
        </div>

        <div style="margin-top:14px;border:1px solid var(--line);border-radius:var(--rb);padding:10px 12px;font-family:var(--mono);font-size:12.5px">
          <div style="display:flex;justify-content:space-between"><span>{{t('topup.creditAdded')}}</span><span v-if="!topupUsd">—</span><span v-else><b>{{money(topupUsd*1e6+topupBonusMicro)}}</b><span v-if="topupBonusMicro" class="sub" style="margin:0"> ({{money(topupUsd*1e6)}} + <span style="color:var(--green)">{{money(topupBonusMicro)}} {{t('topup.bonusInline')}}</span>)</span></span></div>
          <div style="display:flex;justify-content:space-between;border-top:1px solid var(--line);margin-top:8px;padding-top:8px;font-weight:700"><span>{{t('topup.totalDue')}}</span><span>{{topupUsd?money(topupUsd*1e6):'—'}}</span></div>
        </div>
        <p v-if="topupErr" class="sub" style="color:var(--red);margin:10px 0 0">{{topupErr}}</p>
        <p class="sub" style="margin:10px 0 0">{{ t('topup.stripe') }}</p>
        <div style="margin-top:14px;display:flex;justify-content:flex-end;gap:8px">
          <button class="btn" @click="topupOpen=false" :disabled="billingBusy">{{ t('common.cancel') }}</button>
          <button class="btn primary" :disabled="billingBusy||!topupValid" @click="payTopup()">{{billingBusy?t('topup.opening'):(topupUsd?t('topup.payUsd', {usd: topupUsd}):t('topup.payNow'))}}</button>
        </div>
      </div>
    </div>
</template>
