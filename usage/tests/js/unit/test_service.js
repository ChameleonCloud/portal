'use strict';
/* global it, expect, describe, beforeEach, inject, jasmine, getJSONFixture */
describe('NotificationFactory', function() {
    var NotificationFactory;

    beforeEach(function() {
        module('underscore');
        module('usageApp.service');
        inject(function(_NotificationFactory_) {
            NotificationFactory = _NotificationFactory_;
        });
    });

    it('checks if this generates a random uuid', function() {
        var result = NotificationFactory.uuid();
        expect(result.length).toEqual(36);
    });

    it('checks if loading is added', function() {
        NotificationFactory.addLoading('test');
        expect(NotificationFactory.getLoading().test).toBe(true);
    });

    it('checks if loading is removed', function() {
        NotificationFactory.removeLoading('test');
        expect(NotificationFactory.getLoading().test).not.toBeDefined();
    });

    it('checks if message is added', function() {
        NotificationFactory.addMessage('allocations', 'There was an error fetching allocations.', 'danger');
        expect(NotificationFactory.getMessages().allocations[0].type).toEqual('danger');
        expect(NotificationFactory.getMessages().allocations[0].body).toEqual('There was an error fetching allocations.');
    });

    it('checks if message is removed', function() {
        NotificationFactory.addMessage('allocations', 'There was an error fetching allocations.', 'danger');
        var msgObj = NotificationFactory.getMessages().allocations[0];
        NotificationFactory.removeMessage('allocation', msgObj, 's');
        expect(NotificationFactory.getMessages().allocations[0]).toEqual(null);
    });

    it('checks if messages are cleared', function() {
        NotificationFactory.addMessage('allocations', 'Allocations fetched successfully.', 'success');
        NotificationFactory.addMessage('allocations', 'Error fetching allocations.', 'danger');
        NotificationFactory.addMessage('userAllocations', 'User Allocations fetched successfully.', 'success');
        NotificationFactory.addMessage('userAllocations', 'Error fetching user allocations.', 'danger');
        var result = NotificationFactory.clearMessages('allocations');
        expect(NotificationFactory.getMessages().allocations).toEqual([]);
        result = NotificationFactory.clearMessages('all');
        expect(NotificationFactory.getMessages()).toEqual({});
    });

});

describe('UtilFactory', function() {
    var UtilFactory, NotificationFactory;

    beforeEach(function() {
        module('moment');
        module('underscore');
        module('usageApp.service');
        jasmine.getJSONFixtures().fixturesPath = 'base/unit/fixtures';
        module(function($provide) {
            $provide.value('Liferay', {});
        });
        inject(function(_UtilFactory_, _NotificationFactory_) {
            NotificationFactory = _NotificationFactory_;
            UtilFactory = _UtilFactory_;
        });
    });

    it('checks get class', function() {
        var allocation = {
            status: 'pending'
        };
        var clas = UtilFactory.getClass(allocation);
        expect(clas).toEqual('label label-warning');
        allocation.status = 'rejected';
        clas = UtilFactory.getClass(allocation);
        expect(clas).toEqual('label label-danger');
        allocation.status = 'approved';
        clas = UtilFactory.getClass(allocation);
        expect(clas).toEqual('label label-success');
    });

    it('checks if loading', function() {
        NotificationFactory.addLoading('approveAllocation1');
        var result = UtilFactory.isLoading('approveAllocation', {
            id: 2
        });
        expect(result).toBe(false);
        result = UtilFactory.isLoading('approveAllocation', {
            id: 1
        });
        expect(result).toBe(true);
    });

    it('checks if message is closed', function() {
        NotificationFactory.addMessage('approveAllocation1', 'Allocation approved successfully.', 'success');
        var msgObj = NotificationFactory.getMessages().approveAllocation1[0];
        UtilFactory.closeMessage('approveAllocation', msgObj, 1);
        expect(NotificationFactory.getMessages().approveAllocation1[0]).toEqual(null);
    });

    it('checks if an object is empty', function() {
        expect(UtilFactory.isEmpty()).toBe(true);
        expect(UtilFactory.isEmpty('')).toBe(true);
        expect(UtilFactory.isEmpty([])).toBe(true);
        expect(UtilFactory.isEmpty({})).toBe(true);
        expect(UtilFactory.isEmpty(['test'])).toBe(false);
        expect(UtilFactory.isEmpty({
            test: 'test'
        })).toBe(false);
    });

    it('checks if has a message by type', function() {
        var arr = [{
            type: 'success',
            body: 'test msg'
        }, {
            type: 'danger',
            body: 'test msg'
        }];
        expect(UtilFactory.hasMessage(arr, 'success')).toBe(true);
        expect(UtilFactory.hasMessage(arr, 'danger')).toBe(true);
        arr = [{
            type: 'danger',
            body: 'test msg'
        }, {
            type: 'danger',
            body: 'test msg'
        }];
        expect(UtilFactory.hasMessage(arr, 'success')).toBe(false);
        arr = [{
            type: 'success',
            body: 'test msg'
        }, {
            type: 'success',
            body: 'test msg'
        }];
        expect(UtilFactory.hasMessage(arr, 'danger')).toBe(false);
    });

    it('checks messages', function() {
        NotificationFactory.addMessage('approveAllocation1', 'Allocation approved successfully.', 'success');
        expect(UtilFactory.getMessages('approveAllocation', {
            id: 2
        })).toEqual([]);
        expect(UtilFactory.getMessages('approveAllocation', {
            id: 1
        })).toEqual(NotificationFactory.getMessages().approveAllocation1);
    });

    it('checks search', function() {
        var projects = getJSONFixture('projects.json')['result'];
        var filteredProjects = UtilFactory.search(projects, 'CH-815748');
        expect(filteredProjects.length).toEqual(1);
        filteredProjects = UtilFactory.search(projects, 'Test Ajit II');
        expect(filteredProjects.length).toEqual(1);
        filteredProjects = UtilFactory.search(projects, 'agauli@tacc.utexas.edu');
        expect(filteredProjects.length).toEqual(2);
        filteredProjects = UtilFactory.search(projects, 'Ajit');
        expect(filteredProjects.length).toEqual(2);
        filteredProjects = UtilFactory.search(projects, 'Gauli');
        expect(filteredProjects.length).toEqual(2);
    });

    it('checks update selected', function() {
        var projects = getJSONFixture('projects.json')['result'];
        var filter = {
            active: true,
            inactive: false,
            pending: false,
            rejected: false,
            search: 'CH-815748'
        };
        var selectedProjects = UtilFactory.updateSelected(projects, [], filter);
        expect(selectedProjects.length).toEqual(1);
        expect(selectedProjects[0].allocations[0].doNotShow).toBe(false);
        expect(selectedProjects[0].allocations[1].doNotShow).toBe(true);
    });
});

describe('AllocationFactory', function() {
    var AllocationFactory, NotificationFactory, $httpBackend;
    var projects = [{
        id: 1,
        allocations: [{
            id: 1
        }]
    }, {
        id: 2,
        allocations: []
    }];

    var users = [{
        id: 1,
        username: 'test1'
    }, {
        id: 2,
        username: 'test2'
    }];

    beforeEach(function() {
        module('usageApp.service');
        module('underscore');
        module('moment');
        inject(function(_AllocationFactory_, _NotificationFactory_, _$httpBackend_) {
            AllocationFactory = _AllocationFactory_;
            NotificationFactory = _NotificationFactory_;
            $httpBackend = _$httpBackend_;
        });
    });

    it('should get allocations', function() {
        $httpBackend.when('GET', '/admin/allocations/view/').respond(200, projects);
        AllocationFactory.getAllocations();
        $httpBackend.flush();
        $httpBackend.verifyNoOutstandingExpectation();
        $httpBackend.verifyNoOutstandingRequest();
        expect(AllocationFactory.projects).toEqual(projects);
    });

    it('should get user allocations', function() {
        $httpBackend.when('GET', '/admin/allocations/user/test/').respond(200, projects);
        AllocationFactory.getUserAllocations('test');
        $httpBackend.flush();
        $httpBackend.verifyNoOutstandingExpectation();
        $httpBackend.verifyNoOutstandingRequest();
        expect(AllocationFactory.userProjects).toEqual(projects);
    });

    it('should get project users', function() {
        $httpBackend.when('GET', '/admin/usage/projects/1/users/').respond(200, users);
        var project = projects[0];
        AllocationFactory.getProjectUsers(project);
        $httpBackend.flush();
        $httpBackend.verifyNoOutstandingExpectation();
        $httpBackend.verifyNoOutstandingRequest();
        expect(project.users).toEqual(users);
    });
});

describe('UsageFactory', function() {
    var UsageFactory, NotificationFactory, $httpBackend;
    var project = {
        id: 1,
        selectedAllocation: {
            id: 1
        },
        selectedUser: {
            username: 'test1'
        },
        selectedQueue: 'chi@tacc'
    };

    var usage = [
        [456, 19.99],
        [123, 9.90],
        [456, 20.01],
        [123, 10.10]
    ];
    var processedUsage = [
        [123, 20.00],
        [456, 40.00]
    ];
    var usageByUsers = {
        test1: {
            'chi@uc': 2.6414583333333335,
            'kvm@uc': 0.6414583333333334,
            'chi@tacc': 1.6414583333333335
        },
        test2: {
            'chi@uc': 1.6414583333333335,
            'kvm@uc': 1.6414583333333335,
            'chi@tacc': 0.6414583333333334,
            'kvm@tacc': 3.341458333333333
        }
    };
    var processedUsageByUsers = {
        'chi@uc': [1.64, 2.64],
        'kvm@uc': [1.64, 0.64],
        'chi@tacc': [0.64, 1.64],
        'kvm@tacc': [3.34, 0]
    };
    var usageUsers = ['test2', 'test1'];

    beforeEach(function() {
        module('usageApp.service');
        module('underscore');
        module('moment');
        inject(function(_UsageFactory_, _NotificationFactory_, _$httpBackend_) {
            UsageFactory = _UsageFactory_;
            NotificationFactory = _NotificationFactory_;
            $httpBackend = _$httpBackend_;
        });
    });

    it('should get allocation usage', function() {
        $httpBackend.when('GET', '/admin/usage/allocation/1/').respond(200, usage);
        UsageFactory.getAllocationUsage(project);
        $httpBackend.flush();
        $httpBackend.verifyNoOutstandingExpectation();
        $httpBackend.verifyNoOutstandingRequest();
        expect(project.selectedAllocation.usage).toEqual(processedUsage);
    });

    it('should get allocation user usage', function() {
        $httpBackend.when('GET', '/admin/usage/allocation/1/username/test1/').respond(200, usage);
        UsageFactory.getAllocationUserUsage(project);
        $httpBackend.flush();
        $httpBackend.verifyNoOutstandingExpectation();
        $httpBackend.verifyNoOutstandingRequest();
        expect(project.selectedAllocation.usage).toEqual(processedUsage);
    });

    it('should get allocation user queue usage', function() {
        $httpBackend.when('GET', '/admin/usage/allocation/1/username/test1/queue/chi@tacc/').respond(200, usage);
        UsageFactory.getAllocationUserQueueUsage(project);
        $httpBackend.flush();
        $httpBackend.verifyNoOutstandingExpectation();
        $httpBackend.verifyNoOutstandingRequest();
        expect(project.selectedAllocation.usage).toEqual(processedUsage);
    });

    it('should get allocation queue usage', function() {
        $httpBackend.when('GET', '/admin/usage/allocation/1/queue/chi@tacc/').respond(200, usage);
        UsageFactory.getAllocationQueueUsage(project);
        $httpBackend.flush();
        $httpBackend.verifyNoOutstandingExpectation();
        $httpBackend.verifyNoOutstandingRequest();
        expect(project.selectedAllocation.usage).toEqual(processedUsage);
    });

    it('should get allocation usage by users', function() {
        project.from = '2015-01-01T00:00:00';
        project.to = '2015-11-10T00:00:00';
        $httpBackend.when('GET', '/admin/usage/usage-by-users/1/?from=2015-01-01T06:00:00Z&to=2015-11-10T06:00:00Z').respond(200, usageByUsers);
        UsageFactory.getUsageByUsers(project);
        $httpBackend.flush();
        $httpBackend.verifyNoOutstandingExpectation();
        $httpBackend.verifyNoOutstandingRequest();
        expect(project.selectedAllocation.usageUsers).toEqual(usageUsers);
        expect(project.selectedAllocation.usageByUsers).toEqual(processedUsageByUsers);
    });

});
