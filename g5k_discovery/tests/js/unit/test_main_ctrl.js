'use strict';
/*global it, expect, xdescribe, beforeEach, inject */
xdescribe('MainController', function() {

    var controller, scope;

    beforeEach(function() {
        module('discoveryApp');
    });

    beforeEach(inject(function($controller, $rootScope) {
        scope = $rootScope.$new();
        scope.intersectArray = [];
        scope.filters = scope.filtersOrg = {
            site: {
                tacc: [1, 2, 3, 4],
                uc: [5, 6, 7, 8]
            },
            network_adapters: [{
                rate: {
                    1.00: [1, 2, 3],
                    10.00: [4]
                }
            }, {
                rate: {
                    10.00: [5, 6, 7],
                    100.00: [8]
                }
            }]
        };
        scope.booleanizedFilters = {
            site: {
                tacc: false,
                uc: false
            },
            network_adapters: [{
                rate: {
                    1.00: false,
                    10.00: false
                }
            }, {
                rate: {
                    10.00: false,
                    100.00: false
                }
            }]
        };
        scope.appliedFilters = {
            site: {
                tacc: true,
                uc: false
            },
            network_adapters: [{
                rate: {
                    1.00: true,
                    10.00: false
                }
            }, {
                rate: {
                    10.00: false,
                    100.00: false
                }
            }]
        };
        scope.prunedAppliedFilters = {
            site: {
                tacc: true
            },
            network_adapters: [{
                rate: {
                    1.00: true,
                }
            }, {
            }]
        };

        scope.prunedAppliedFiltersNoPreserve = {
            site: {
                tacc: true
            },
            network_adapters: [{
                rate: {
                    1.00: true,
                }
            }]
        };
        
        scope.filteredNodesOrg = [{
            uid: 1,
            site: 'tacc'
        }, {
            uid: 2,
            site: 'uc'
        }];
        controller = $controller('MainController', {
            $scope: scope
        });
    }));

    it('Checks if an object is an object of object(s)', function() {
        var obj = {
            test1: {
                a: [1, 2, 3]
            },
            test2: {
                b: [1, 2, 3]
            }
        };
        var result = scope.isNestedObject(obj);
        expect(result).toEqual(true);
    });

    it('Checks if an object is an array of object(s)', function() {
        var obj = [{
            a: [1, 2, 3]
        }, {
            b: [1, 2, 3]
        }];
        var result = scope.isArrayOfObjects(obj);
        expect(result).toEqual(true);
    });

    it('Checks if user selected checkbox should be disabled', function() {
        var result = scope.shouldDisable(['site', 'tacc'], 2);
        expect(result).toEqual(false);
    });

    it('Checks if user selected nested checkbox should be disabled', function() {
        var result = scope.shouldDisable(['network_adapters', 0, 'rate', 1.00], 2);
        expect(result).toEqual(false);
    });

    it('Checks if untouched checkbox should be disabled', function() {
        var result = scope.shouldDisable(['site', 'uc'], 2);
        expect(result).toEqual(true);
    });

    it('Checks if untouched nested checkbox should be disabled', function() {
        var result = scope.shouldDisable(['network_adapters', 0, 'rate', 10.00], 2);
        expect(result).toEqual(true);
    });

    it('Converts all leaf values to false', function() {
        var filters = angular.copy(scope.filters);
        scope.booleanizeFilter(filters);
        expect(filters).toEqual(scope.booleanizedFilters);
    });

    it('Prunes filters keeping only the applied ones, preserves array', function() {
        var filters = angular.copy(scope.appliedFilters);
        scope.prune(filters, null, true);
        expect(filters).toEqual(scope.prunedAppliedFilters);
    });

    it('Prunes filters keeping only the applied ones, does not preserve array', function() {
        var filters = angular.copy(scope.appliedFilters);
        scope.prune(filters, null, false);
        expect(filters).toEqual(scope.prunedAppliedFiltersNoPreserve);
    });

    it('Creates intersect array of applied filters', function() {
        scope.createIntersectArray();
        expect(scope.intersectArray).toEqual([[1, 2, 3, 4], [1, 2, 3]]);
        scope.intersectArray=[];
    });

});
