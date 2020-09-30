import axios from 'axios'
import camelcaseKeys from 'camelcase-keys'
import snakecaseKeys from 'snakecase-keys'
import Vue from 'vue'

import MigrateAccount from './MigrateAccount.vue'

// Django CSRF compatibility -- this should be in any Vue entry point that
// requires XHR.
axios.defaults.xsrfCookieName = 'csrftoken'
axios.defaults.xsrfHeaderName = 'X-CSRFTOKEN'
// Handle Python snake_case versus Javascript preferred camelCase
axios.defaults.transformResponse = [(data, headers) => {
  if (data && headers['content-type'].includes('application/json')) {
    return camelcaseKeys(JSON.parse(data), { deep: true })
  }
}]
axios.defaults.transformRequest = [(data, headers) => {
  const contentType = headers['content-type']
  if (data && (!contentType || contentType.includes('application/json'))) {
    return JSON.stringify(snakecaseKeys(data, { deep: true }))
  }
}]
axios.defaults.headers['Content-Type'] = 'application/json'

new Vue({
  render: h => h(MigrateAccount)
}).$mount('#app')
