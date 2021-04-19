/**
 * author agauli
 */
'use strict';
angular.module('allocationsApp')
    .controller('AllocationsController', ['$scope', '$http', '$timeout', 'moment', '_', '$modal', 'UtilFactory', 'AllocationFactory', 'NotificationFactory', function($scope, $http, $timeout, moment, _, $modal, UtilFactory, AllocationFactory, NotificationFactory) {
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
        $scope.reset = function() {
            $scope.selectedProjects = $scope.projects;
            $scope.filter.active = false;
            $scope.filter.inactive = false;
            $scope.filter.pending = false;
            $scope.filter.rejected = false;
            $scope.filter.search = '';
        };

        $scope.getAllocations = function() {
            $scope.projects = [];
            AllocationFactory.getAllocations().then(function() {
                $scope.projects = AllocationFactory.projects;
                $scope.selectedProjects = angular.copy($scope.projects);
            });
        };
        $scope.getAllocations();

        $scope.updateSelected = function() {
            $scope.selectedProjects = UtilFactory.updateSelected($scope.projects, $scope.selectedProjects, $scope.filter);
        };

        $scope.approveAllocation = function(project, allocation, $event) {
            var modifiedAllocation = angular.copy(allocation);
            var modalInstance = $modal.open({
                templateUrl: '/admin/allocations/template/approval.html/',
                controller: 'modalController',
                resolve: {
                    data: function() {
                        return {
                            'allocation': modifiedAllocation,
                            'type': 'approve'
                        };
                    }
                }
            });
            modalInstance.result.then(function(data) {
                $event.currentTarget.blur();
                var postData = angular.copy(data.allocation);
                try {
                    delete postData.doNotShow;
                } catch (err) {}
                postData.status = 'Approved';
                postData.start = moment(postData.start).format('YYYY-MM-DD');
                postData.end = moment(postData.end).format('YYYY-MM-DD');
                postData.dateReviewed = moment(new Date()).format('YYYY-MM-DD');
                AllocationFactory.approveAllocation(postData).then(function(response) {
                    if (response !== null) {
                        project.allocations = _.reject(project.allocations, function(alloc) {
                            return alloc.id === response.id;
                        });
                        project.allocations.push(response);
                    }
                });

            }, function() {
                $event.currentTarget.blur();
            });
        };

        $scope.rejectAllocation = function(project, allocation, $event) {
            var modifiedAllocation = angular.copy(allocation);
            var modalInstance = $modal.open({
                templateUrl: '/admin/allocations/template/approval.html/',
                controller: 'modalController',
                resolve: {
                    data: function() {
                        return {
                            'allocation': modifiedAllocation,
                            'type': 'reject'
                        };
                    }
                }
            });
            modalInstance.result.then(function(data) {
                $event.currentTarget.blur();
                var postData = angular.copy(data.allocation);
                try {
                    delete postData.doNotShow;
                } catch (err) {}
                postData.status = 'Rejected';
                postData.dateReviewed = moment(new Date()).format('YYYY-MM-DD');
                AllocationFactory.rejectAllocation(postData).then(function(response) {
                    if (response !== null) {
                        project.allocations = _.reject(project.allocations, function(alloc) {
                            return alloc.id === response.id;
                        });
                        project.allocations.push(response);
                    }
                });
            }, function() {
                $event.currentTarget.blur();
            });
        };
        
        $scope.waitingAllocation = function(project, allocation, $event) {
            var modalInstance = $modal.open({
                templateUrl: '/admin/allocations/template/contact.html/',
                controller: 'modalController',
                resolve: {
                    data: function() {
                        return {};
                    }
                }
            });
            modalInstance.result.then(function(data) {
                $event.currentTarget.blur();
                var postData = angular.copy(data);
                postData.allocation = angular.copy(allocation);
            	postData.rt.requestor = project.pi.email;
                try {
                    delete postData.doNotShow;
                } catch (err) {}
                AllocationFactory.waitingAllocation(postData);
            }, function() {
                $event.currentTarget.blur();
            });
        };

    }]);
