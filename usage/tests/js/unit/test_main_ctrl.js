'use strict';
/*global xit, expect, describe, beforeEach, inject*/
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

    xit('checks reset', function() {
        scope.projects = [1, 2, 3];
        scope.reset();
        expect(scope.selectedProjects).toEqual(scope.projects);
        expect(scope.filter.active).toBe(false);
        expect(scope.filter.inactive).toBe(false);
        expect(scope.filter.pending).toBe(false);
        expect(scope.filter.rejected).toBe(false);
        expect(scope.filter.search).toEqual('');
    });

    xit('checks get allocations', function() {
        scope.getAllocations();
        expect(scope.projects).toEqual(projects);
        expect(scope.selectedProjects).toEqual(projects);
    });
});
