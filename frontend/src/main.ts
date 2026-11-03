import { createApp } from 'vue'
import App from './App.vue'
import { vDialog } from './dialogs/dialog'
import { preloadInitialView, prefetchAfterBoot } from './views'
import { t, locale } from './i18n/index'
// The two brand faces, from pinned npm packages (OFL-1.1) and bundled same-origin: Geist Pixel for
// page titles, DM Mono for figures and code. Body text uses the system font (DESIGN.md).
import '@fontsource/geist-pixel/latin-400.css'
import '@fontsource/dm-mono/latin-400.css'
import '@fontsource/dm-mono/latin-500.css'
import '@fontsource/dm-mono/latin-400-italic.css'
import './styles/base.css'
import '../../src/treg/web/media/redesign/dashboard.css'

preloadInitialView()
const app = createApp(App).directive('dialog', vDialog)
// Every template reaches the translator without an import each: `t()` reads the same reactive
// `locale` the i18n module holds, so a switch re-renders any template that rendered a string.
app.config.globalProperties.t = t
app.config.globalProperties.tregLocale = locale
document.documentElement.lang = locale.value
prefetchAfterBoot(app.mount('#app'))
