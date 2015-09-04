/**
 * author agauli
 */
'use strict';
angular.module('allocationsApp')
    .controller('UserAllocationsController', ['$scope', '$http', '_', 'UtilFactory', 'AllocationFactory', 'NotificationFactory', function($scope, $http, _, UtilFactory, AllocationFactory, NotificationFactory) {
        $scope.messages = [];
        $scope.$on('allocation:notifyMessage', function() {
            $scope.messages = NotificationFactory.getMessages();
        });
        $scope.loading = {};
        $scope.$on('allocation:notifyLoading', function() {
            $scope.loading = NotificationFactory.getLoading();
        });
        $scope.close = UtilFactory.closeMessage;
        $scope.isEmpty = UtilFactory.isEmpty;
        $scope.hasMessage = UtilFactory.hasMessage;
        $scope.isLoading = UtilFactory.isLoading;
        $scope.getMessages = UtilFactory.getMessages;
        $scope.getClass = UtilFactory.getClass;
        $scope.filter = {
            active: false,
            inactive: false,
            pending: false,
            rejected: false,
            search: ''
        };
        $scope.updateSelected = function(){
            $scope.selectedProjects = UtilFactory.updateSelected($scope.projects, $scope.selectedProjects, $scope.filter);
        };
        $scope.reset = function() {
            $scope.selectedProjects = angular.copy($scope.projects);
            $scope.filter.active = false;
            $scope.filter.inactive = false;
            $scope.filter.pending = false;
            $scope.filter.rejected = false;
            $scope.filter.search = '';
        };

        $scope.selections = {
            usernamemodel: '',
            username: ''
        };
        $scope.submitted = false;
        $scope.getUserAllocations = function() {
            $scope.projects = [];
            $scope.selections.username = $scope.selections.usernamemodel;
            $scope.submitted = true;
            if ($scope.selections.username && $scope.selections.username.length > 0) {
                AllocationFactory.getUserAllocations($scope.selections.username).then(function() {
                    $scope.projects = AllocationFactory.userProjects;
                    $scope.selectedProjects = angular.copy($scope.projects);
                });
            }
        };

        $scope.handleKeyPress = function(e) {
            var key = e.keyCode || e.which;
            if (key === 13) {
                $scope.getUserAllocations();
            }
        };
    }]);
