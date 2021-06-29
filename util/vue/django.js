// Copyright 2021 University of Chicago
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import camelcaseKeys from 'camelcase-keys'
import snakecaseKeys from 'snakecase-keys'

export function configureXHR(axios) {
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
}
