/**
 * Created by agauli on 2/26/15.
 */
angular.module('discoveryApp')
    .controller('AppController', ['$scope', '$http', '_', '$q', '$timeout', 'ResourceFactory', 'UtilFactory', function($scope, $http, _, $q, $timeout, ResourceFactory, UtilFactory) {
        $scope.snakeToReadable = UtilFactory.snakeToReadable;
        $scope.isArray = function(obj) {
            return _.isArray(obj);
        }
        $scope.isNestedObject = function(obj) {
            if (_.isArray(obj)) {
                return false;
            } else if (_.isObject(obj)) {
                for (var key in obj) {
                    if (_.isArray(obj[key])) {
                        return false;
                    } else if (_.isObject(obj[key])) {
                        return true;
                    } else {
                        return false;
                    }
                }
            }
        }
        $scope.isArrayOfObjects = function(obj) {
            if (!_.isArray(obj) || _.isEmpty(obj)) {
                return false;
            } else {
                //checking only the first element serves our purpose here
                if (_.isObject(obj[0])) {
                    return true;
                } else {
                    return false;
                }
            }
        }
        var booleanizeFilter = function(filters) {
            for (key in filters) {
                if ($scope.isArrayOfObjects(filters[key])) {
                    var len = filters[key].length;
                    for (var i = 0; i < len; i++) {
                        var key = key + '';
                        booleanizeFilter(filters[key][i]);
                    }
                } else if (_.isArray(filters[key])) {
                    filters[key] = false;
                } else if (_.isObject(filters[key])) {
                    booleanizeFilter(filters[key]);
                }
            }
        }
        var pruneAppliedFilters = function(filters, ky) {
            var filtersOrg = filters;
            filters = (typeof filters === 'undefined') ? $scope.prunedAppliedFilters : filters[ky];
            for (var key in filters) {
                if (_.isObject(filters[key]) && !_.isArray(filters[key]) && !UtilFactory.isEmpty(filters[key])) {
                    pruneAppliedFilters(filters, key);
                } else if (_.isArray(filters[key]) && !UtilFactory.isEmpty(filters[key])) {
                    if (_.isObject(filters[key][0])) {
                        var len = filters[key].length - 1;
                        for (var i = len; i >= 0; i--) {
                            pruneAppliedFilters(filters[key], i);
                        }
                        if (_.isEmpty(filters[key])) {
                            delete filters[key];
                        }
                    }
                } else if (UtilFactory.isEmpty(filters[key]) || filters[key] === false) {
                    if (_.isArray(filters)) {
                        filters.splice(key, 1);
                    } else {
                        delete filters[key];
                    }
                }
            }
            if (UtilFactory.isEmpty(filters) && typeof ky !== 'undefined') {
                if (_.isArray(filtersOrg)) {
                    filtersOrg.splice(ky, 1);
                } else {
                    delete filtersOrg[ky];
                }
            }
        }
        ResourceFactory.getResources($scope, function() {
            $scope.allNodes = ResourceFactory.allNodes;
            $scope.filteredNodes = ResourceFactory.allNodes;
            ResourceFactory.processNodes($scope.allNodes);
            $scope.filters = angular.copy(ResourceFactory.filters);
            $scope.appliedFilters = angular.copy(ResourceFactory.filters);
            booleanizeFilter($scope.appliedFilters);
            $scope.filterSite = $scope.filters['site'];
            delete $scope.filters['site'];
            $scope.filterCluster = $scope.filters['cluster'];
            delete $scope.filters['cluster'];
            $scope.filterArchitecture = $scope.filters['architecture'];
            delete $scope.filters['architecture'];
            $scope.filterProcessor = $scope.filters['processor'];
            delete $scope.filters['processor'];;
            $scope.filterMainMemory = $scope.filters['main_memory'];
            delete $scope.filters['main_memory'];
        }, function(errorMsg) {
            console.error(errorMsg);
        });
        var intersectArray = [];
        var resourceFilter;
        var createIntersectArray = function(filters, ky, resourceFilter) {
            filters = (typeof filters === 'undefined') ? $scope.prunedAppliedFilters : filters[ky];
            resourceFilter = (typeof ky === 'undefined') ? ResourceFactory.filters : resourceFilter[ky];
                for (var key in filters) {
                    if (_.isObject(filters[key]) && !_.isArray(filters[key]) && !UtilFactory.isEmpty(filters[key])) {
                        createIntersectArray(filters, key, resourceFilter);
                    } else if (_.isArray(filters[key]) && !UtilFactory.isEmpty(filters[key])) {
                        if (_.isObject(filters[key][0])) {
                            var len = filters[key].length - 1;
                            for (var i = len; i >= 0; i--) {
                                createIntersectArray(filters[key], i, resourceFilter);
                            }
                        }
                    } else if (filters[key] === true) {
                        key = key + '';
                        intersectArray.push(resourceFilter[key]);
                    }
                }
        }

        $scope.applyFilter = function() {
            $scope.prunedAppliedFilters = angular.copy($scope.appliedFilters);
            pruneAppliedFilters();
            console.log('$scope.prunedAppliedFilters', $scope.prunedAppliedFilters);
            intersectArray = [];
            createIntersectArray();
            var filteredNodes = null;
            if(intersectArray.length > 0){
               _.each(intersectArray, function(arr){
                   if(filteredNodes === null){
                      filteredNodes = arr;
                   }
                   else if(filteredNodes.length > 0){
                      filteredNodes = _.intersection(filteredNodes, arr);
                   }
               });
            }
            $scope.filteredNodes = filteredNodes;
            console.log('filteredNodes', filteredNodes);
        }
    }]);
