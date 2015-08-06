'use strict';
/*global it, expect, describe, beforeEach, inject, moment*/
describe('AllocationsController', function() {

    var controller, scope, httpBackend;

    beforeEach(function() {
        module('moment');
        module('allocationsApp');
        inject(function($controller, $httpBackend, $rootScope) {
            httpBackend = $httpBackend;
            scope = $rootScope.$new();
            controller = $controller('AllocationsController', {
                $scope: scope
            });
        });
    });

    it('checks call to allocations view', function(){
        var data = [{title: 'Project I'},{title: 'Project II'}];
       httpBackend.expect('GET', '/admin/allocations/view/')
            .respond(data);
       httpBackend.flush();
       expect(scope.projects).toEqual(data);
       expect(scope.selectedProjects).toEqual(data);
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

    it('checks search', function() {
        scope.filter = {
            search: ''
        };

        scope.projects = [{
            title: 'Analytical Mathematics',
            chargeCode: '1ABC',
            pi: {
                firstName: 'John',
                lastName:  'Ham',
                username: 'jham',
                email: 'jham@test.edu'
            },
            allocations: [{
                title: 'Wrangler Allocation',
                status: 'pending'
            }, {
                title: 'Maverick Allocation',
                status: 'approved'
            }]
        }, {
            title: 'Computational Science',
            chargeCode: '2DEF',
            pi: {
                firstName: 'Walter',
                lastName:  'Smith',
                username: 'swalter',
                email: 'swalter@test.edu'
            },
            allocations: [{
                title: 'Chameleon Allocation',
                status: 'active'
            }, {
                title: 'Stampede Allocation',
                status: 'inactive'
            }]
        }];

        var projectsJohn = [{
            title: 'Analytical Mathematics',
            chargeCode: '1ABC',
            pi: {
                firstName: 'John',
                lastName:  'Ham',
                username: 'jham',
                email: 'jham@test.edu'
            },
            allocations: [{
                title: 'Wrangler Allocation',
                status: 'pending'
            }, {
                title: 'Maverick Allocation',
                status: 'approved'
            }]
        }];

        var result = scope.search();
        expect(result).toEqual(scope.projects);
        scope.filter.search = 'Analytical Mathematics';
        result = scope.search();
        expect(result).toEqual(projectsJohn);
        scope.filter.search = '1ABC';
        result = scope.search();
        expect(result).toEqual(projectsJohn);
        scope.filter.search = 'jham';
        result = scope.search();
        expect(result).toEqual(projectsJohn);
        scope.filter.search = 'John';
        result = scope.search();
        expect(result).toEqual(projectsJohn);
        scope.filter.search = 'Ham';
        result = scope.search();
        expect(result).toEqual(projectsJohn);
        scope.filter.search = 'jham';
        result = scope.search();
        expect(result).toEqual(projectsJohn);
        scope.filter.search = 'jham@test.edu';
        result = scope.search();
        expect(result).toEqual(projectsJohn);
    });

    it('checks update selected', function() {
        scope.filter = {
            pending: true,
            approved: false,
            active: false,
            inactive: false,
            search: ''
        };
        var selectedProjects = [{
            name: 'Project I',
            allocations: [{
                name: 'Allocation I',
                status: 'pending',
                doNotShow : false
            }, {
                name: 'Allocation II',
                status: 'approved',
                doNotShow : true
            }]
        }];

        scope.projects = [{
            name: 'Project I',
            allocations: [{
                name: 'Allocation I',
                status: 'pending'
            }, {
                name: 'Allocation II',
                status: 'approved'
            }]
        }, {
            name: 'Project II',
            allocations: [{
                name: 'Allocation III',
                status: 'active'
            }, {
                name: 'Allocation III',
                status: 'inactive'
            }]
        }];

        scope.updateSelected();
        expect(scope.selectedProjects).toEqual(selectedProjects);
    });

it('checks getClass', function() {
        var allocation = {
            status: 'pending'
        };
        var result = scope.getClass(allocation);
        expect(result).toEqual('label label-warning');
        allocation = {
            status: 'rejected'
        };
        result = scope.getClass(allocation);
        expect(result).toEqual('label label-danger');
        allocation = {
            status: 'active'
        };
        result = scope.getClass(allocation);
        expect(result).toEqual('label label-success');
    });

it('checks toUTC', function() {
        var expectedDate = moment().format('YYYY-MM-DD');
        console.log('expectedDate', expectedDate);
        var result = scope.toUTC(moment());
        expect(result).toEqual(expectedDate);
    });
});
