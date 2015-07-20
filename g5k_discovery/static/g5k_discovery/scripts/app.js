angular.module('underscore', [])
    .factory('_', function() {
        return window._;
    });

angular.module('discoveryApp', ['ng.django.forms', 'underscore'])
    .config(function($interpolateProvider, $httpProvider) {
        $interpolateProvider.startSymbol('[[').endSymbol(']]');
        $httpProvider.defaults.headers.common['X-Requested-With'] = 'XMLHttpRequest';
        $httpProvider.defaults.headers.post['Content-Type'] = 'application/x-www-form-urlencoded';
        $httpProvider.defaults.xsrfCookieName = 'csrftoken';
        $httpProvider.defaults.xsrfHeaderName = 'X-CSRFToken';
    });
