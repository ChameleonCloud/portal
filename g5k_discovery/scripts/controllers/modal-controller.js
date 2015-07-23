/**
 * Created by agauli on 2/26/15.
 */
 'use strict';
angular.module('discoveryApp')
    .controller('ModalController', ['$scope', '$modal', '$log', function($scope, $modal, $log) {
        $scope.userSelections = {
            startDate: '',
            endDate: '',
            minNode: '',
            maxNode: ''
        };
        $scope.open = function() {

            var modalInstance = $modal.open({
                animation: true,
                templateUrl: 'template/reserve-modal.html/',
                controller: 'ModalInstanceCtrl',
                resolve: {
                    userSelections: function() {
                        return $scope.userSelections;
                    }
                }
            });

            modalInstance.result.then(function(userSelections) {
                $scope.userSelections = userSelections;
            }, function() {
                $log.info('Modal dismissed at: ' + new Date());
            });
        };

    }]);

// Please note that $modalInstance represents a modal window (instance) dependency.
// It is not the same as the $modal service used above.

angular.module('discoveryApp').controller('ModalInstanceCtrl', ['$scope', '$filter', 'ResourceFactory', '$modalInstance', 'userSelections', function($scope, $filter, ResourceFactory, $modalInstance, userSelections) {
    $scope.userSelections = userSelections;
    var nodes = ResourceFactory.filteredNodes || ResourceFactory.allNodes;
    $scope.maxNodes = nodes.length;
    $scope.showScript = false;
    var scrpt = '';
    $scope.generateScript = function() {
        var appliedFilters = ResourceFactory.prunedAppliedFilters;
        scrpt = '';
        generateFilterScript(appliedFilters);
        var selectionScript = 'startDate=' + $filter('date')($scope.userSelections.startDate, 'yyyy-MM-dd') + '&endDate=' + $filter('date')($scope.userSelections.endDate, 'yyyy-MM-dd') + '&min=' + $scope.userSelections.minNode + '&max=' + $scope.userSelections.maxNode;
        if(scrpt){
           $scope.scrpt = scrpt + '&' + selectionScript;
        }
        else{
            $scope.scrpt = selectionScript;
        }
        $scope.showScript = true;
    };
    var generateFilterScript = function(appliedFilters, ky){
        ky = ky || '';
           for(var key in appliedFilters){console.log('key>>>>', key);
              if(_.isArray(appliedFilters[key])){
                var arr = appliedFilters[key];
                 for(var i=0; i<arr.length; i++){
                    var k1 = ky + key + '_' + i + '_';
                    generateFilterScript(arr[i], k1);
                 }
              }
              else if(_.isObject(appliedFilters[key])){
                    var k2 = ky + key + '_';
                    generateFilterScript(appliedFilters[key], k2);
              }
              else if(appliedFilters[key] === true){
                ky = ky.substring(0, ky.length -1);
                 scrpt += '&' + ky + '=' + key; 
              }
           }
    };

    $scope.getScript = function() {
        return $scope.scrpt;
    };

    $scope.fallback = function(copy) {
        //do somthing
       console.log('copy', copy);
    };

    $scope.ok = function() {
        $modalInstance.close( $scope.userSelections);
    };

    $scope.cancel = function() {
        $modalInstance.dismiss('cancel');
    };

    $scope.getMin = function(){
       return $scope.userSelections.minNode || 1;
    };
    $scope.minDate = new Date();
    $scope.open = {
        start: false,
        end: false
    };
    $scope.open = function($event, caltype) {
        $event.preventDefault();
        $event.stopPropagation();

        caltype = caltype.toLowerCase();
        if (caltype === 'start') {
            if ($scope.open.start) {
                $scope.open.start = false;
            }
            $scope.open.start = true;

        } else if (caltype === 'end') {
            if ($scope.open.end) {
                $scope.open.end = false;
            }
            $scope.open.end = true;
        }
    };

    $scope.dateOptions = {
        formatYear: 'yy',
        startingDay: 1
    };

    $scope.format = 'yyyy-MM-dd';
}]);
