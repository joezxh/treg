<script>
import { useDashboard } from '../state/context'
export default { setup: useDashboard }
</script>

<template>

          <!-- Two programs, one page, forked at the header: the credit referral program every user
               gets, and the invite-only cash tier behind it. A fork rather than a card under the
               referral column, because a card there read as step four of the referral program. The
               cash tier is hand-approved on purpose — hand-approval IS the anti-gaming design
               (money.md §Referrals) — so it is a form, not a self-serve toggle, and it shows to
               everyone, team or not, so a partner without a team yet can still apply. -->
          <h1>{{refTab==='partner' ? t('referrals.affiliatePartner') : t('referrals.referFriend')}}</h1>
          <p class="sub" v-if="refTab==='partner'">{{ t('referrals.partnerSub') }}</p>
          <p class="sub" v-else :style="ref.loaded ? null : {visibility:'hidden'}">{{ t('referrals.friendSub', { referred: money(ref.terms.referred_micro), min: money(ref.terms.min_topup_micro), referrer: money(ref.terms.referrer_micro), days: ref.terms.hold_days }) }}</p>
          <div class="tabs" style="max-width:720px">
            <button :class="{active:refTab==='friend'}" @click="refTab='friend'">{{ t('referrals.referFriend') }}</button>
            <button :class="{active:refTab==='partner'}" @click="refTab='partner'">{{ t('referrals.affiliatePartner') }}</button>
          </div>
          <div v-if="refTab==='partner'" style="max-width:720px">
            <div class="card">
              <div class="lbl">{{ t('referrals.whoFor') }}</div>
              <p class="sub" style="margin:6px 0 0">{{ t('referrals.whoForText') }}</p>
              <div class="lbl" style="margin-top:16px">{{ t('referrals.whatEarn') }}</div>
              <p class="sub" style="margin:6px 0 0">{{ t('referrals.whatEarnText', { limit: ref.cap.limit }) }}</p>
              <div class="lbl" style="margin-top:16px">{{ t('referrals.howToGetIn') }}</div>
              <p class="sub" style="margin:6px 0 14px">{{ t('referrals.howToGetInText') }}</p>
              <a class="btn primary sm" href="https://forms.gle/5N3DyVPrNJkrGuxF6" target="_blank"
                 rel="noopener" @click="track('affiliate_apply_clicked')" style="text-decoration:none">{{ t('referrals.applyButton') }}</a>
            </div>
            <p class="sub" style="margin:12px 0 0">{{ t('referrals.justFriendLead') }}<a href="#" @click.prevent="refTab='friend'">{{ t('referrals.referAFriend') }}</a>{{ t('referrals.justFriendTail', { amount: money(ref.terms.referrer_micro) }) }}</p>
          </div>

          <template v-if="refTab==='friend'">

          <p v-if="ref.loading" class="sub">{{ t('common.loading') }}</p>
          <!-- ONE column for the whole view. The children carry no max-width of their own: three
               different ones is what made the card, the tiles and the table start and end at three
               different x-positions. -->
          <div v-else style="max-width:720px">
            <!-- Everyone with a team gets a link — including free-tier users, who on a product
                 pitched as "$1.00 free, no card" are most users and the likeliest to tell a friend.
                 This branch is now only the degenerate case (no team to pay the reward into), kept
                 because the reward has to land SOMEWHERE and a silent zero is the worst version. -->
            <div v-if="!ref.eligible" class="card" style="margin-top:14px">
              <div class="lbl">{{ t('referrals.createTeamTitle') }}</div>
              <p class="sub" style="margin:6px 0 12px">{{ t('referrals.createTeamText') }}</p>
              <button class="btn primary sm" @click="go('orgs')">{{ t('referrals.goToTeams') }}</button>
            </div>

            <template v-else>
              <div class="card" style="margin-top:14px">
                <div class="lbl">{{ t('referrals.yourLink') }}</div>
                <div style="display:flex;gap:8px;margin-top:8px">
                  <input readonly :value="ref.link" @focus="$event.target.select()"
                         style="flex:1;min-width:0;font-family:var(--mono);font-size:12px">
                  <button class="btn sm" @click="copyRefLink" style="flex:none">{{refCopied ? t('common.copied') : t('common.copy')}}</button>
                </div>
                <p class="sub" style="margin:10px 0 0" v-if="ref.credit_org" v-html="t('referrals.rewardLands', { name: '<b>'+ref.credit_org.name+'</b>' })"></p>
              </div>

              <!-- `.stat` expects `.n` (the figure) then `.l` (the label), in that order — any other
                   class names render as unstyled text, which is exactly what a hand-rolled k/v pair
                   did here. -->
              <!-- auto-FIT, not the sheet's auto-fill: at this width auto-fill lays out four 150px
                   tracks and leaves the fourth empty, so three tiles stop short of the column's
                   right edge while the card above and the table below reach it. auto-fit collapses
                   the empty track and the three stretch to fill. -->
              <div class="statgrid" style="margin-top:14px;grid-template-columns:repeat(auto-fit,minmax(150px,1fr))">
                <div class="stat"><div class="n">{{ref.totals.signed_up}}</div><div class="l">{{ t('referrals.statSignedUp') }}</div></div>
                <div class="stat"><div class="n">{{ref.totals.topped_up}}</div><div class="l">{{ t('referrals.statToppedUp') }}</div></div>
                <div class="stat"><div class="n">{{money(ref.totals.earned_micro)}}</div><div class="l">{{ t('referrals.statEarned') }}</div></div>
              </div>
              <p v-if="ref.totals.pending_micro" class="sub" style="margin:-8px 0 0">
                {{ t('referrals.pending', { amount: money(ref.totals.pending_micro), days: ref.terms.hold_days }) }}</p>

              <!-- The cap refusal IS the commercial conversation, same posture as a daily-cap
                   refusal: it names the limit and points at a human rather than silently paying 0. -->
              <div v-if="ref.cap.paid >= ref.cap.limit" class="card"
                   style="margin-top:14px;border-color:var(--accent)">
                <div class="lbl">{{ t('referrals.hitLimit', { limit: ref.cap.limit }) }}</div>
                <p class="sub" style="margin:6px 0 0">{{ t('referrals.hitLimitText') }}</p>
              </div>

              <div class="grp" style="margin:20px 0 8px">{{ t('referrals.yourReferrals') }}</div>
              <p v-if="!ref.referrals.length" class="sub" style="margin:0">
                {{ t('referrals.nobodyYet') }}</p>
              <!-- House-style table: bare `<table>` is ALREADY a card (background, border, radius)
                   and `th,td` already carry 10px/13px padding. Overriding that padding to `8px 0`
                   is what pushed the amount flush against the card's own right edge. -->
              <table v-else>
                <tr><th>{{ t('referrals.thWho') }}</th><th>{{ t('referrals.thSignedUp') }}</th><th>{{ t('referrals.thStatus') }}</th><th style="text-align:right">{{ t('referrals.thReward') }}</th></tr>
                <tr v-for="(r,i) in ref.referrals" :key="i">
                  <td>{{r.email || '—'}}</td>
                  <td class="sub" style="white-space:nowrap">{{bhistDate(r.signed_up_at)}}</td>
                  <td>{{refStatus(r)}}</td>
                  <td style="text-align:right;font-family:var(--mono);white-space:nowrap">
                    <span v-if="r.reward_micro">{{money(r.reward_micro)}}</span>
                    <span v-else class="muted">—</span>
                  </td>
                </tr>
              </table>
            </template>
          </div>
          </template>

</template>
