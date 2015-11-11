'use strict';
/*global it, expect, xdescribe, beforeEach, inject*/
xdescribe('UserAllocationsController', function() {
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
                getUserAllocations: function(username) {
                    return {
                        then: function(successClbk) {
                            angular.noop(username);
                            successClbk(projects);
                        }
                    };
                },
                userProjects: projects
            });
        });
        inject(function($controller, $rootScope, $modal) {
            modal = $modal;
            scope = $rootScope.$new();
            controller = $controller('UserAllocationsController', {
                $scope: scope
            });
            scope.selections = {
                username: 'test',
                usernamemodel: 'test'
            };
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
        scope.getUserAllocations();
        expect(scope.projects).toEqual(projects);
        expect(scope.selectedProjects).toEqual(projects);
    });

    it('checks enter key press', function() {
        var keyEvent = {
            keyCode: 13
        };
        scope.handleKeyPress(keyEvent);
        expect(scope.projects).toEqual(projects);
        expect(scope.selectedProjects).toEqual(projects);
    });
});
