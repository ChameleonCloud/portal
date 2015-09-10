/**
 * author agauli
 */
'use strict';
angular.module('allocationsApp')
    .controller('modalController', ['$scope', '$modalInstance', '$timeout', 'data', function modalController($scope, $modalInstance, $timeout, data) {
        $scope.data = data;
        $scope.ok = function() {
            $modalInstance.close(data);
        };

        $scope.cancel = function() {
            $modalInstance.dismiss('cancel');
        };

        //calendar
        $scope.disabled = function(date, mode) {
            //always returns false, not using currently but good to keep
            return (false && mode === 'day' && (date.getDay() === 0 || date.getDay() === 6));
        };

        $scope.minStartDate = new Date();
        $scope.maxDate = angular.copy($scope.minStartDate);
        $scope.maxDate = $scope.maxDate.setFullYear($scope.maxDate.getFullYear() + 10);
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
