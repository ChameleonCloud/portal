/**
 * author agauli
 */
'use strict';
angular.module('allocationsApp')
    .controller('AllocationsController', ['$scope', '$http', '_', '$q', '$timeout', '$modal', 'moment', function($scope, $http, _, $q, $timeout, $modal, moment) {
        $scope.projects = [];
        $scope.filteredProjects = [];
        $scope.loading = {
            allocations: true,
        };
        $scope.loadingError = {
            allocations: '',
        };
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

        $scope.search = function() {
            if (!$scope.filter.search) {
                return $scope.projects;
            } else {
                return _.filter($scope.projects, function(project) {
                    var term = $scope.filter.search.toLowerCase();
                    var pass = false;
                    var projectTitle = project.title || '';
                    var chargeCode = project.chargeCode || '';
                    var pi = project.pi || false;
                    if (projectTitle.toLowerCase().indexOf(term) > -1) {
                        pass = true;
                    } else if (chargeCode.toLowerCase().indexOf(term) > -1) {
                        pass = true;
                    } else if (pi && (
                        pi.lastName.toLowerCase().indexOf(term) > -1 ||
                        pi.firstName.toLowerCase().indexOf(term) > -1 ||
                        pi.username.toLowerCase().indexOf(term) > -1 ||
                        pi.email.toLowerCase().indexOf(term) > -1)
                    ) {
                        pass = true;
                    }
                    return pass;
                });
            }
        };

        $scope.updateSelected = function() {
            var chosenStatusFilters = [];
            for (var key in $scope.filter) {
                if ($scope.filter[key] === true) {
                    chosenStatusFilters.push(key.toLowerCase());
                }
            }
            $scope.selectedProjects = $scope.search();
            if (chosenStatusFilters.length !== 0) {
                var selectedProjectsNew = _.filter($scope.selectedProjects, function(project) {
                    var pass = false;
                    _.each(project.allocations, function(allocation) {
                        allocation.doNotShow = false;
                        var status = allocation.status.toLowerCase();
                        if (_.contains(chosenStatusFilters, status)) {
                            pass = true;
                        } else {
                            allocation.doNotShow = true;
                        }
                    });
                    return pass;
                });
                $scope.selectedProjects = selectedProjectsNew;
            } else {
                _.each($scope.selectedProjects, function(project) {
                    _.each(project.allocations, function(allocation) {
                        allocation.doNotShow = false;
                    });
                });

            }

        };
        $scope.getClass = function(allocation) {
            var status = allocation.status.toLowerCase();
            if (status === 'pending') {
                return 'label label-warning';
            } else if (status === 'rejected') {
                return 'label label-danger';
            } else {
                return 'label label-success';
            }
        };
        $http({
                method: 'GET',
                url: '/admin/allocations/view/',
                cache: 'true'
            })
            .then(function(response) {
                    $scope.loading.allocations = false;
                    $scope.projects = response.data;
                    $scope.selectedProjects = response.data;

                },
                function(error) {
                    console.log('There was an error fetching allocations. ' + error);
                    $scope.loadingError.allocations = 'There was an error loading allocations.';
                    $scope.loading.allocations = false;
                });

        $scope.toUTC = function(date) {
            return moment(date).format('YYYY-MM-DD');
        };
        $scope.approveAllocation = function(allocation, $event) {
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
                allocation.loadingApprove = true;
                allocation.errorApprove = false;
                allocation.successApprove = false;
                try {
                    delete postData.loadingApprove;
                    delete postData.errorApprove;
                    delete postData.successApprove;
                    delete postData.doNotShow;
                } catch (err) {
                    //pass
                }

                postData.status = 'Approved';
                postData.start = $scope.toUTC(postData.start);
                postData.end = $scope.toUTC(postData.end);
                postData.dateReviewed = $scope.toUTC(new Date());
                $http({
                        method: 'POST',
                        url: '/admin/allocations/approval/',
                        data: postData
                    })
                    .then(function(response) {
                            allocation.loadingApprove = false;
                            if (response.data.status === 'error') {
                                allocation.errorApprove = true;
                            } else {
                                //not working when i assign postData to allocation entirely
                                allocation.successApprove = true;
                                allocation.computeAllocated = postData.computeAllocated;
                                allocation.storageAllocated = postData.storageAllocated;
                                allocation.memoryAllocated = postData.memoryAllocated;
                                allocation.start = postData.start;
                                allocation.end = postData.end;
                                allocation.decisionSummary = postData.decisionSummary;
                                allocation.status = postData.status;

                            }
                        },
                        function(error) {
                            console.log('There was an error approving this allocation. ' + error);
                            allocation.errorApprove = true;
                            allocation.loadingApprove = false;
                        });
            }, function() {
                $event.currentTarget.blur();
            });
        };

        $scope.rejectAllocation = function(allocation, $event) {
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
                allocation.loadingReject = true;
                allocation.errorReject = false;
                allocation.successReject = false;
                try {
                    delete postData.loadingReject;
                    delete postData.errorReject;
                    delete postData.successReject;
                    delete postData.doNotShow;
                } catch (err) {
                    //pass
                }

                postData.status = 'Rejected';
                postData.dateReviewed = $scope.toUTC(new Date());
                $http({
                        method: 'POST',
                        url: '/admin/allocations/approval/',
                        data: postData
                    })
                    .then(function(response) {
                            console.log('response.data', response.data);
                            allocation.loadingReject = false;
                            if (response.data.status === 'error') {
                                allocation.errorReject = true;
                            } else {
                                //not working when i assign postData to allocation entirely
                                allocation.successReject = true;
                                allocation.decisionSummary = postData.decisionSummary;
                                allocation.status = postData.status;

                            }
                        },
                        function(error) {
                            console.log('There was an error rejecting this allocation. ' + error);
                            allocation.errorReject = true;
                            allocation.loadingReject = false;
                        });
            }, function() {
                $event.currentTarget.blur();
            });
        };

    }]);