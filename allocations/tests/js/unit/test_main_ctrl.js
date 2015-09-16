'use strict';
/*global it, expect, describe, beforeEach, inject, spyOn*/
describe('AllocationsController', function() {
    var controller, scope, modal;
    var projects = [{
        id: 1,
        allocations: [{
            id: 1
        }]
    }, {
        id: 2,
        allocations: [{
            id: 2
        }]
    }];

    beforeEach(function() {
        module('allocationsApp');
        module(function($provide) {
            $provide.value('AllocationFactory', {
                getAllocations: function() {
                    return {
                        then: function(successClbk) {
                            successClbk(projects);
                        }
                    };
                },
                approveAllocation: function(postData) {
                    return {
                        then: function(successClbk) {
                            angular.noop(postData);
                            successClbk({
                                id: 1,
                                status: 'Approved'
                            });
                        }
                    };
                },
                rejectAllocation: function(postData) {
                    return {
                        then: function(successClbk) {
                            angular.noop(postData);
                            successClbk({
                                id: 1,
                                status: 'Rejected'
                            });
                        }
                    };
                },
                projects: projects
            });
        });
        inject(function($controller, $rootScope, $modal) {
            modal = $modal;
            scope = $rootScope.$new();
            controller = $controller('AllocationsController', {
                $scope: scope
            });
        });
    });

    it('checks reset', function() {
        scope.projects = [1, 2, 3];
        scope.reset();
        expect(scope.selectedProjects).toEqual(scope.projects);
        expect(scope.filter.active).toBe(false);
        expect(scope.filter.inactive).toBe(false);
        expect(scope.filter.pending).toBe(false);
        expect(scope.filter.rejected).toBe(false);
        expect(scope.filter.search).toEqual('');
    });

    it('checks get allocations', function() {
        scope.getAllocations();
        expect(scope.projects).toEqual(projects);
        expect(scope.selectedProjects).toEqual(projects);
    });

    it('checks approve allocation', function() {
        var modalInstance = {
            result: {
                then: function(successClbk) {
                    successClbk({
                        allocation: projects[0].allocations[0]
                    });
                }
            }
        };
        var $event = {
            currentTarget: {
                blur: function() {}
            }
        };
        spyOn(modal, 'open').andReturn(modalInstance);
        var project = projects[0];
        scope.approveAllocation(project, project.allocations[0], $event);
        expect(project.allocations[0].status).toEqual('Approved');
    });

    it('checks reject allocation', function() {
        var modalInstance = {
            result: {
                then: function(successClbk) {
                    successClbk({
                        allocation: projects[0].allocations[0]
                    });
                }
            }
        };
        var $event = {
            currentTarget: {
                blur: function() {}
            }
        };
        spyOn(modal, 'open').andReturn(modalInstance);
        var project = projects[0];
        scope.rejectAllocation(project, project.allocations[0], $event);
        expect(project.allocations[0].status).toEqual('Rejected');
    });
});
