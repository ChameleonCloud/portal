'use strict';
/* global it, expect, describe, beforeEach, inject, jasmine, getJSONFixture */
describe('NotificationFactory', function () {
  var NotificationFactory;

  beforeEach(function () {
    module('underscore');
    module('ng.django.urls');
    module('appCatalogApp.service');
    inject(function (_NotificationFactory_) {
      NotificationFactory = _NotificationFactory_;
    });
  });

  it('checks if this generates a random uuid', function () {
    var result = NotificationFactory.uuid();
    expect(result.length).toEqual(36);
  });

  it('checks if loading is added', function () {
    NotificationFactory.addLoading('test');
    expect(NotificationFactory.getLoading().test).toBe(true);
  });

  it('checks if loading is removed', function () {
    NotificationFactory.removeLoading('test');
    expect(NotificationFactory.getLoading().test).not.toBeDefined();
  });

  it('checks if message is added', function () {
    NotificationFactory.addMessage('allocations', 'There was an error fetching allocations.', 'danger');
    expect(NotificationFactory.getMessages().allocations[0].type).toEqual('danger');
    expect(NotificationFactory.getMessages().allocations[0].body).toEqual('There was an error fetching allocations.');
  });

  it('checks if message is removed', function () {
    NotificationFactory.addMessage('allocations', 'There was an error fetching allocations.', 'danger');
    var msgObj = NotificationFactory.getMessages().allocations[0];
    NotificationFactory.removeMessage('allocation', msgObj, 's');
    expect(NotificationFactory.getMessages().allocations[0]).toEqual(null);
  });

  it('checks if messages are cleared', function () {
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

describe('UtilFactory', function () {
  var UtilFactory, NotificationFactory;

  beforeEach(function () {
    module('moment');
    module('underscore');
    module('ng.django.urls');
    module('appCatalogApp.service');
    jasmine.getJSONFixtures().fixturesPath = 'base/unit/fixtures';
    module(function ($provide) {
      $provide.value('Liferay', {});
    });
    inject(function (_UtilFactory_, _NotificationFactory_) {
      NotificationFactory = _NotificationFactory_;
      UtilFactory = _UtilFactory_;
    });
  });

  it('checks get class', function () {
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

  it('checks if loading', function () {
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

  it('checks if message is closed', function () {
    NotificationFactory.addMessage('approveAllocation1', 'Allocation approved successfully.', 'success');
    var msgObj = NotificationFactory.getMessages().approveAllocation1[0];
    UtilFactory.closeMessage('approveAllocation', msgObj, 1);
    expect(NotificationFactory.getMessages().approveAllocation1[0]).toEqual(null);
  });

  it('checks if an object is empty', function () {
    expect(UtilFactory.isEmpty()).toBe(true);
    expect(UtilFactory.isEmpty('')).toBe(true);
    expect(UtilFactory.isEmpty([])).toBe(true);
    expect(UtilFactory.isEmpty({})).toBe(true);
    expect(UtilFactory.isEmpty(['test'])).toBe(false);
    expect(UtilFactory.isEmpty({
      test: 'test'
    })).toBe(false);
  });

  it('checks if has a message by type', function () {
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

  it('checks messages', function () {
    NotificationFactory.addMessage('approveAllocation1', 'Allocation approved successfully.', 'success');
    expect(UtilFactory.getMessages('approveAllocation', {
      id: 2
    })).toEqual([]);
    expect(UtilFactory.getMessages('approveAllocation', {
      id: 1
    })).toEqual(NotificationFactory.getMessages().approveAllocation1);
  });

  it('checks search', function () {
    var appliances = getJSONFixture('appliances.json')['result'];
    var filteredAppliances = UtilFactory.search(appliances, 'App One');
    expect(filteredAppliances.length).toEqual(1);
    filteredAppliances = UtilFactory.search(appliances, 'test app description');
    expect(filteredAppliances.length).toEqual(1);
    filteredAppliances = UtilFactory.search(appliances, 'test author');
    expect(filteredAppliances.length).toEqual(2);
  });

});

describe('ApplianceFactory', function () {
  var ApplianceFactory, NotificationFactory, $httpBackend;
  var appliances = {
    result: [{
      id: 1,
      name: 'App One'
    }, {
      id: 2,
      name: 'App Two'
    }]
  };
  var appliance = {
    result: [{
      id: 1,
      name: 'App One'
    }]
  };
  var keywords = {result: [{id: '64-bit'}, {id: '32-bit'}]};
  var keywordsFormatted = [{id: '64-bit', label: '64-bit'}, {id: '32-bit', label: '32-bit'}];
  beforeEach(function () {
    module('ng.django.urls');
    module('appCatalogApp.service');
    module('underscore');
    module('moment');
    inject(function (_ApplianceFactory_, _NotificationFactory_, _$httpBackend_) {
      ApplianceFactory = _ApplianceFactory_;
      NotificationFactory = _NotificationFactory_;
      $httpBackend = _$httpBackend_;
    });
  });

  it('should get appliances', function () {
    $httpBackend.when('GET', '/angular/reverse/?djng_url_name=appliance_catalog%3Aget_appliances').respond(200, appliances);
    ApplianceFactory.getAppliances();
    $httpBackend.flush();
    $httpBackend.verifyNoOutstandingExpectation();
    $httpBackend.verifyNoOutstandingRequest();
    expect(ApplianceFactory.appliances).toEqual(appliances.result);
  });

  it('should get an appliance', function () {
    $httpBackend.when('GET', '/angular/reverse/?djng_url_name=appliance_catalog%3Aget_appliance&djng_url_args=1').respond(200, appliance);
    ApplianceFactory.getAppliance(1);
    $httpBackend.flush();
    $httpBackend.verifyNoOutstandingExpectation();
    $httpBackend.verifyNoOutstandingRequest();
    expect(ApplianceFactory.appliances).toEqual(appliance.result);
  });

  it('should get keywords', function () {
    $httpBackend.when('GET', '/angular/reverse/?djng_url_name=appliance_catalog%3Aget_keywords').respond(200, keywords);
    ApplianceFactory.getKeywords();
    $httpBackend.flush();
    $httpBackend.verifyNoOutstandingExpectation();
    $httpBackend.verifyNoOutstandingRequest();
    expect(ApplianceFactory.keywords).toEqual(keywordsFormatted);
  });
});
