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
        $scope.open = function(size) {

            var modalInstance = $modal.open({
                animation: true,
                templateUrl: 'template/reserve-modal.html/',
                controller: 'ModalInstanceCtrl',
                size: size,
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

angular.module('discoveryApp').controller('ModalInstanceCtrl', ['$scope', '$filter', '$modalInstance', 'userSelections', function($scope, $filter, $modalInstance, userSelections) {
    $scope.userSelections = userSelections;
    $scope.showScript = false;
    $scope.generateScript = function() {
        console.log(' $scope.userSelections',  $scope.userSelections);
        $scope.showScript = true;
        //$modalInstance.close( $scope.userSelections);
    };
    $scope.getScript = function() {
        //$modalInstance.close( $scope.userSelections);
        var scrpt = 'startDate=' + $filter('date')($scope.userSelections.startDate, 'yyyy-MM-dd') + '&endDate=' + $filter('date')($scope.userSelections.endDate, 'yyyy-MM-dd') + '&min=' + $scope.userSelections.minNode + '&max=' + $scope.userSelections.maxNode;
        return scrpt;
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

    $scope.format = 'dd-MMMM-yyyy';
}]);
