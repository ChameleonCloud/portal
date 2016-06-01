/**
 * Created by agauli on 2/26/15.
 */
'use strict';
angular.module('discoveryApp')
    .controller('ModalController', ['$scope', '$modal', '$log', 'moment', 'UserSelectionsFactory', function($scope, $modal, $log, moment, UserSelectionsFactory) {
        //modal open
        $scope.open = function() {
            $scope.userSelections = UserSelectionsFactory.getUserSelections();
            var modalInstance = $modal.open({
                animation: true,
                templateUrl: 'template/reserve_modal.html/',
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
                //
            });
        };

    }]);

// Please note that $modalInstance represents a modal window (instance) dependency.
// It is not the same as the $modal service used above.

angular.module('discoveryApp').controller('ModalInstanceCtrl', ['$scope', '$filter', 'ResourceFactory', 'UtilFactory', '$modalInstance', 'userSelections', function($scope, $filter, ResourceFactory, UtilFactory, $modalInstance, userSelections) {
    $scope.userSelections = userSelections;
    var nodes = ResourceFactory.filteredNodes || ResourceFactory.allNodes;
    $scope.maxNodes = nodes.length;
    $scope.showScript = false;
    $scope.scrpt = '';
    $scope.generateScript = function() {
        var appliedFilters = ResourceFactory.prunedAppliedFilters;
        generateFilterScript(appliedFilters);
        if ($scope.scrpt) {
            $scope.scrpt = $scope.scrpt.substring(0, $scope.scrpt.length - 2);
            $scope.scrpt = 'climate lease-create --physical-reservation min=' + $scope.userSelections.minNode + ',max=' + $scope.userSelections.maxNode +
                ',resource_properties=\'[' + $scope.scrpt + ']\'' + ' --start-date \"' + UtilFactory.getFormattedDate($scope.userSelections.startDate, $scope.userSelections.startTime) +
                '\" --end-date \"' + UtilFactory.getFormattedDate($scope.userSelections.endDate, $scope.userSelections.endTime) + '\" my-custom-lease';
        } else {
            $scope.scrpt = 'climate lease-create --physical-reservation min=' + $scope.userSelections.minNode + ',max=' + $scope.userSelections.maxNode +
                ' --start-date \"' + UtilFactory.getFormattedDate($scope.userSelections.startDate, $scope.userSelections.startTime) + '\" --end-date \"' +
                UtilFactory.getFormattedDate($scope.userSelections.endDate, $scope.userSelections.endTime) + '\" my-custom-lease';
        }
        $scope.showScript = true;
    };
    var generateFilterScript = function(appliedFilters, ky) {
        ky = ky || '';
        for (var key in appliedFilters) {
            if (_.isArray(appliedFilters[key])) {
                var arr = appliedFilters[key];
                for (var i = 0; i < arr.length; i++) {
                    var k1 = ky + key + '.' + i + '.';
                    generateFilterScript(arr[i], k1);
                }
            } else if (_.isObject(appliedFilters[key])) {
                var k2 = ky + key + '.';
                generateFilterScript(appliedFilters[key], k2);
            } else if (appliedFilters[key] && appliedFilters[key] === true && ['site.', 'cluster.'].indexOf(ky) === -1) {
                ky = ky.substring(0, ky.length - 1);
                $scope.scrpt += '\"=\", \"$' + ky + '\", \"' + UtilFactory.humanizedToBytes(key) + '\", ';
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
        $modalInstance.close($scope.userSelections);
    };

    $scope.cancel = function() {
        $modalInstance.dismiss('cancel');
    };

    $scope.getMin = function() {
        return $scope.userSelections.minNode || 1;
    };
    $scope.minDate = new Date();
    $scope.open = {
        start: false,
        end: false
    };
    //calendar widget open
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
