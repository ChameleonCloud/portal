'use strict';
/*global it, expect, describe, beforeEach, inject */
describe('ModalInstanceCtrl', function() {

    var controller, scope, modalInstance;

    beforeEach(function() {
        module('discoveryApp');
    });

    beforeEach(module(function($provide) {
        $provide.value('$modalInstance', {});
        $provide.value('userSelections', {
            startDate: Date.parse('01/01/2015'),
            endDate: Date.parse('12/30/2015'),
            minNode: 10,
            maxNode: 20
        });
    }));

    beforeEach(inject(function($controller, $rootScope, ResourceFactory, $modalInstance) {
        modalInstance = $modalInstance;
        scope = $rootScope.$new();
        scope.open = {
            start: false,
            end: false
        };
        scope.scrpt = '';
        ResourceFactory.prunedAppliedFilters = {
            site: {
                tacc: true
            },
            network_adapters: [{
                rate: {
                    1.00: true,
                }
            }, {}]
        };

        scope.filteredNodes = [{
            uid: 1,
            site: 'tacc'
        }, {
            uid: 2,
            site: 'uc'
        }];

        controller = $controller('ModalInstanceCtrl', {
            $scope: scope
        });
    }));

    it('Generates script based on user selections', function() {
        scope.generateScript();
        expect('climate lease-create --physical-reservation min=10,max=20,resource_properties=\'[\"=\", \"$network_adapters.0.rate\", \"1\"]\' --start-date \"2015-01-01 06:00\" --end-date \"2015-12-30 06:00\" my-custom-lease').toEqual(scope.scrpt);
    });

    it('Opens and closes calendar', function() {
        var mockEvent = {
            preventDefault: function(){},
            stopPropagation: function(){}
        };
        scope.open(mockEvent, 'start');
        expect(scope.open.start).toEqual(true);
        scope.open(mockEvent, 'end');
        expect(scope.open.end).toEqual(true);
    });

});
