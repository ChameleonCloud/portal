'use strict';
angular.module('underscore', []).factory('_', function() {
  return window._; // assumes underscore has already been loaded on the page
});

angular.module('moment', []).factory('moment', function() {
  return window.moment; // assumes moment has already been loaded on the page
});

angular.module('usageApp.service', []);

angular.module('usageApp',['underscore', 'moment', 'usageApp.service', 'ui.bootstrap', 'highcharts-ng'])
.config(function($interpolateProvider, $httpProvider) {
    $interpolateProvider.startSymbol('[[').endSymbol(']]');
    $httpProvider.defaults.headers.common['X-Requested-With'] = 'XMLHttpRequest';
    $httpProvider.defaults.headers.post['Content-Type'] = 'application/x-www-form-urlencoded';
    $httpProvider.defaults.xsrfCookieName = 'csrftoken';
    $httpProvider.defaults.xsrfHeaderName = 'X-CSRFToken';
});
