import axios from 'axios'
import Vue from 'vue'

import ApplianceCatalog from './AppCatalog.vue'
import CreateAppButton from './CreateAppButton'
import { configureXHR } from '../../util/vue/django'

configureXHR(axios)

new Vue({
    render: a => a(ApplianceCatalog)
}).$mount('#appCatalog')

new Vue({
    render: a => a(CreateAppButton)
}).$mount('#createAppButton')
