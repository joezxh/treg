<script>
import { useDashboard } from '../state/context'
export default { setup: useDashboard }
</script>

<template>
<div  class="scrim" role="dialog" aria-labelledby="agent-guide-dialog-title" aria-modal="true" v-dialog="() => { capAsk=null }" @click.self="capAsk=null">
      <div class="modal" style="padding:16px">
        <h3 id="agent-guide-dialog-title" style="margin:0 0 6px">{{t('method.connect')}} {{capAsk.provider.display_name}}</h3>
        <p class="sub" style="margin:0 0 14px">{{t('agent.question')}}</p>
        <p v-if="capAsk.provider.consent_notice" class="mk-notice" style="margin:0 0 14px">{{capAsk.provider.consent_notice}}</p>
        <!-- The price BEFORE the consent screen, not on the invoice: an oauth-billed provider (X)
             charges treg's app per use, so calls on this connection are metered from the balance. -->
        <p v-if="capAsk.provider.metered" class="mk-notice" style="margin:0 0 14px">{{ t('agent.metered', { name: capAsk.provider.display_name, read: '$'+capAsk.provider.billed_rates.read_per_result_usd, write: '$'+capAsk.provider.billed_rates.write_per_call_usd, writeLink: '$'+capAsk.provider.billed_rates.write_with_link_usd }) }}</p>
        <div class="ttable-wrap"><table class="ttable">
          <tr v-for="cap in capOptions(capAsk)" :key="cap">
            <!-- Deliberately NOT .tn: that class is nowrap, which is right for a name column
                 but here the help text shares the cell. Unwrapped, a long capability
                 description widens the table past the modal and .ttable-wrap's overflow:hidden
                 clips the Choose button clean off — the choice becomes unclickable. -->
            <td style="white-space:normal"><b>{{capLabel(cap,capAsk)}}</b>
              <span v-if="capInReview(cap,capAsk)" class="chip warn" style="margin-left:6px">{{t('agent.inReview')}}</span>
              <span class="sub" style="display:block;font-size:11px;margin-top:3px">{{capHelp(cap,capAsk)}}</span></td>
            <td class="tx"><button class="btn sm" :class="{primary:cap===capDefault(capAsk)}"
                                    @click="chooseCapability(cap)">{{t('agent.choose')}}</button></td>
          </tr>
        </table></div>
        <div style="margin-top:12px;text-align:right"><button class="btn sm" @click="capAsk=null">{{t('common.cancel')}}</button></div>
      </div>
    </div>
</template>
