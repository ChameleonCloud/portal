'use strict';
/*global it, expect, describe, beforeEach, inject*/
describe('UsageController', function() {
    var controller, scope, _moment;
    var projects = [{
        id: 1,
        allocations: [{
            id: 1,
            status: 'pending'
        }]
    }, {
        id: 2,
        allocations: [{
            id: 2,
            status: 'active'
        }]
    }];

    var selectedProjects = [{
        id: 2,
        allocations: [{
            id: 2,
            status: 'active',
            hasUsage: true,
            doNotShow: false
        }],
        hasActiveAllocation: true,
        selectedAllocation: {
            id: 2,
            status: 'active',
            hasUsage: true,
            doNotShow: false
        }
    }];

    var usageByUsers = {
        test1: {
                'chi@ uc': 2.6414583333333335,
                'kvm@ uc': 0.6414583333333334,
                'chi@ tacc': 1.6414583333333335
        },
        test2: {
                'chi@ uc': 1.6414583333333335,
                'kvm@ uc': 1.6414583333333335,
                'chi@ tacc': 0.6414583333333334,
                'kvm@ tacc': 3.341458333333333
        }
    };

    beforeEach(function() {
        module('usageApp');
        module('moment');
        module('highcharts');
        /* jshint unused:false */
        module(function($provide) {
            $provide.value('AllocationFactory', {
                getAllocations: function() {
                    return {
                        then: function(successClbk) {
                            successClbk(projects);
                        }
                    };
                },
                getUserAllocations: function(username) {
                    return {
                        then: function(successClbk) {
                            successClbk(projects);
                        }
                    };
                },
                projects: projects,
                userProjects: projects
            });
        });
        module(function($provide) {
            $provide.value('UsageFactory', {
                getUsageByUsers: function(project) {
                    return {
                        then: function(successClbk) {
                            successClbk(usageByUsers);
                        }
                    };
                }
            });
        });
        /* jshint unused:true */
        inject(function($controller, $rootScope, moment) {
            scope = $rootScope.$new();
            controller = $controller('UsageController', {
                $scope: scope
            });
            _moment = moment;
        });
    });

    it('checks reset', function() {
        scope.projects = [1, 2, 3];
        scope.reset();
        expect(scope.selectedProjects).toEqual(scope.projects);
        expect(scope.filter.active).toBe(false);
        expect(scope.filter.inactive).toBe(false);
        expect(scope.filter.search).toEqual('');
    });

    it('checks get allocations', function() {
        scope.getAllocations();
        expect(scope.projects).toEqual(projects);
        expect(scope.selectedProjects).toEqual(selectedProjects);
    });

    it('checks get user allocations', function() {
        scope.selections = {
            usernamemodel: 'test'
        };
        scope.getUserAllocations();
        expect(scope.projects).toEqual(projects);
        angular.forEach(projects, function(project) {
            if (project.id === 1) {
                expect(project.hasActiveAllocation).toBe(false);
                expect(project.selectedAllocation).toBeUndefined();
            } else if (project.id === 2) {
                expect(project.hasActiveAllocation).toBe(true);
                expect(project.selectedAllocation).toEqual(projects[1].allocations[0]);
            }
        });
        expect(scope.selectedProjects).toEqual(selectedProjects);
    });

    it('checks update usage by users chart', function() {
        var project = {
            selectedAllocation: {
                id: 1,
                start: '2015-01-01T06:00:00Z'
            }
        };
        //1m
        scope.updateUsageByUsersChart(project, '1m');
        expect(project.dateRange).toEqual('1m');
        expect(project.from).toEqual(_moment().startOf('day').subtract(1, 'months').format('YYYY-MM-DD'));
        expect(project.to).toEqual(_moment().startOf('day').format('YYYY-MM-DD'));
        //3m
        scope.updateUsageByUsersChart(project, '3m');
        expect(project.dateRange).toEqual('3m');
        expect(project.from).toEqual(_moment().startOf('day').subtract(3, 'months').format('YYYY-MM-DD'));
        expect(project.to).toEqual(_moment().startOf('day').format('YYYY-MM-DD'));
        //1m
        scope.updateUsageByUsersChart(project, '6m');
        expect(project.dateRange).toEqual('6m');
        expect(project.from).toEqual(_moment().startOf('day').subtract(6, 'months').format('YYYY-MM-DD'));
        expect(project.to).toEqual(_moment().startOf('day').format('YYYY-MM-DD'));
        //ytd
        scope.updateUsageByUsersChart(project, 'ytd');
        expect(project.dateRange).toEqual('ytd');
        expect(project.from).toEqual(_moment().startOf('day').startOf('year').format('YYYY-MM-DD'));
        expect(project.to).toEqual(_moment().startOf('day').format('YYYY-MM-DD'));
        //1y
        scope.updateUsageByUsersChart(project, '1y');
        expect(project.dateRange).toEqual('1y');
        expect(project.from).toEqual(_moment().startOf('day').subtract(1, 'years').format('YYYY-MM-DD'));
        expect(project.to).toEqual(_moment().startOf('day').format('YYYY-MM-DD'));
        //all
        scope.updateUsageByUsersChart(project, 'all');
        expect(project.dateRange).toEqual('all');
        expect(project.from).toEqual(_moment(project.selectedAllocation.start).startOf('day').format('YYYY-MM-DD'));
        expect(project.to).toEqual(_moment().startOf('day').format('YYYY-MM-DD'));
        //custom
        project.from = project.to = Date();
        scope.updateUsageByUsersChart(project);
        expect(project.dateRange).toEqual('custom');
        expect(project.from).toEqual(_moment().startOf('day').format('YYYY-MM-DD'));
        expect(project.to).toEqual(_moment().startOf('day').format('YYYY-MM-DD'));

    });
});
