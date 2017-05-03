'use strict';
angular.module('discoveryApp')
    .controller('NodeController', ['$scope', '$http', '_', '$q', '$timeout', 'UtilFactory',
        function($scope, $http, _, $q, $timeout, UtilFactory) {

          $scope.snakeToReadable = UtilFactory.snakeToReadable;

          $scope.resource_link = "";

          $scope.initLink = function(resource_link) {
          console.log("Resource link: " + resource_link);
            $scope.resource_link = '/' + resource_link + '.json';
            console.log("Link in scope: " + $scope.resource_link);

            $scope.node = $http({
            method: 'GET',
            url: $scope.resource_link,
            cache: 'true'
        }).then(function(response) {
            return response;
        });
          }
}]);
