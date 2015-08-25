/**
 * Created by agauli on 2/26/15.
 */
'use strict';
angular.module('discoveryApp')
    .controller('MainController', ['$scope', '$http', '_', '$q', '$timeout', 'ResourceFactory', 'UtilFactory', function($scope, $http, _, $q, $timeout, ResourceFactory, UtilFactory) {
        $scope.snakeToReadable = UtilFactory.snakeToReadable;

        $scope.isArray = function(obj) {
            return _.isArray(obj);
        };

        $scope.isObject = function(obj) {
            return _.isObject(obj);
        };

        $scope.contains = function(arr, element) {
            return _.contains(arr, element);
        };

        $scope.isShowValTag = UtilFactory.isShowValTag;
        $scope.isEmpty = UtilFactory.isEmpty;

        $scope.changeView = function() {
            $scope.showNodes = !$scope.showNodes;
        };

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
        };

        $scope.isEmptyArrayNested = function(arr) {
            if (!arr || !_.isArray(arr) || arr.length < 1) {
                return true;
            } else {
                for (var i = 0; i < arr.length; i++) {
                    if (!_.isEmpty(arr[i])) {
                        return false;
                    }
                }
                return true;
            }
        };
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
        };
        $scope.shouldDisable = function(keyArr, count) {
            var val = null;
            for (var i = 0; i < keyArr.length; i++) {
                var k = keyArr[i];
                if (val === null) {
                    val = $scope.appliedFilters[k];
                } else {
                    val = val[k];
                }
            }
            //do not disable if it is a user selected filter, only auto checked filters are disabled
            if (val === false) {
                if (typeof count !== 'undefined' && count !== $scope.filteredNodes.length) {
                    val = true;
                }
            }
            return !val;
        };
        $scope.booleanizeFilter = function(filters) {
            for (var key in filters) {
                if ($scope.isArrayOfObjects(filters[key])) {
                    var len = filters[key].length;
                    for (var i = 0; i < len; i++) {
                        key = key + '';
                        $scope.booleanizeFilter(filters[key][i]);
                    }
                } else if (_.isArray(filters[key])) {
                    filters[key] = false;
                } else if (_.isObject(filters[key])) {
                    $scope.booleanizeFilter(filters[key]);
                }
            }
        };
        $scope.prune = function(filters, ky, preserveArray) {
            var filtersOrg = filters;
            filters = (ky === null) ? filters : filters[ky];
            for (var key in filters) {
                if (_.isObject(filters[key]) && !_.isArray(filters[key]) && !UtilFactory.isEmpty(filters[key])) {
                    $scope.prune(filters, key, preserveArray);
                } else if (_.isArray(filters[key]) && !UtilFactory.isEmpty(filters[key])) {
                    if (_.isObject(filters[key][0])) {
                        var len = filters[key].length - 1;
                        for (var i = len; i >= 0; i--) {
                            $scope.prune(filters[key], i, preserveArray);
                        }
                        if (_.isEmpty(filters[key])) {
                            delete filters[key];
                        }
                    }
                } else if (UtilFactory.isEmpty(filters[key]) || filters[key] === false) {
                    if (_.isArray(filters)) {
                        if (!preserveArray) {
                            filters.splice(key, 1);
                        }
                    } else {
                        delete filters[key];
                    }
                }
            }
            if (UtilFactory.isEmpty(filters) && typeof ky !== 'undefined') {
                if (_.isArray(filtersOrg)) {
                    if (!preserveArray) {
                        filtersOrg.splice(ky, 1);
                    }
                } else {
                    delete filtersOrg[ky];
                }
            }
        };

        var makeChunks = function() {
            $scope.filterSite = $scope.filters['site'];
            delete $scope.filters['site'];
            $scope.filterCluster = $scope.filters['cluster'];
            delete $scope.filters['cluster'];
            $scope.filterArchitecture = $scope.filters['architecture'];
            delete $scope.filters['architecture'];
            $scope.advancedFiltersOrg = angular.copy($scope.filters);
        };

        ResourceFactory.getResources($scope, function() {
            $scope.allNodes = ResourceFactory.allNodes;
            $scope.filteredNodes = ResourceFactory.allNodes;
            ResourceFactory.processNodes($scope.allNodes);
            $scope.filtersOrg = angular.copy(ResourceFactory.filters);
            $scope.filters = angular.copy(ResourceFactory.filters);
            $scope.appliedFiltersOrg = angular.copy(ResourceFactory.filters);
            $scope.booleanizeFilter($scope.appliedFiltersOrg);
            $scope.appliedFilters = angular.copy($scope.appliedFiltersOrg);
            makeChunks();

        }, function(errorMsg) {
            console.error(errorMsg);
        });
        $scope.intersectArray = [];
        $scope.createIntersectArray = function(filters, ky, resourceFilter) {
            filters = (typeof filters === 'undefined') ? $scope.prunedAppliedFilters : filters[ky];
            resourceFilter = (typeof ky === 'undefined') ? $scope.filtersOrg : resourceFilter[ky];
            for (var key in filters) {
                if (_.isObject(filters[key]) && !_.isArray(filters[key]) && !UtilFactory.isEmpty(filters[key])) {
                    $scope.createIntersectArray(filters, key, resourceFilter);
                } else if (_.isArray(filters[key]) && !UtilFactory.isEmpty(filters[key])) {
                    if (_.isObject(filters[key][0])) {
                        var len = filters[key].length - 1;
                        for (var i = len; i >= 0; i--) {
                            $scope.createIntersectArray(filters[key], i, resourceFilter[key]);
                        }
                    }
                } else if (filters[key] === true) {
                    key = key + '';
                    $scope.intersectArray.push(resourceFilter[key]);
                }
            }
        };

        $scope.advancedFilter = {
            search: '',
            allKeys: false
        };

        $scope.filterSearchRecursive = function(filters, filtersTemp, searchKeys) {
            for (var key in filters) {
                var humanizedKey = UtilFactory.snakeToReadable(key).toLowerCase();
                var pass = false;
                for (var j = 0; j < searchKeys.length; j++) {
                    pass = humanizedKey.indexOf(searchKeys[j]) > -1;
                    if (pass) {
                        break;
                    }
                }
                if (pass) {
                    if (_.isArray(filters[key]) && !UtilFactory.isEmpty(filters[key]) && _.isString(filters[key][0])) {
                        //this means this is a selection option, other options should NOT be filtered out
                        filtersTemp = _.extend(filtersTemp, filters);
                        break;
                    } else {
                        filtersTemp[key] = filters[key];
                    }
                } else {
                    if (_.isObject(filters[key]) && !_.isArray(filters[key]) && !UtilFactory.isEmpty(filters[key])) {
                        filtersTemp[key] = {};
                        $scope.filterSearchRecursive(filters[key], filtersTemp[key], searchKeys);
                    } else if (_.isArray(filters[key]) && !UtilFactory.isEmpty(filters[key])) {
                        if (_.isObject(filters[key][0])) {
                            var len = filters[key].length - 1;
                            filtersTemp[key] = [];
                            for (var i = len; i >= 0; i--) {
                                filtersTemp[key][i] = {};
                                $scope.filterSearchRecursive(filters[key][i], filtersTemp[key][i], searchKeys);
                            }
                        }
                    }
                }
            }
        };

        $scope.filterSearch = function() {
            //$scope.switch.status true means ALL, false means ANY
            console.log('advancedFilter.allKeys', $scope.advancedFilter.allKeys);
            var searchKeys = $scope.advancedFilter.search.split(' ');
            _.each(searchKeys, function(searchKey) {
                searchKey = searchKey.replace(/^\s+ \s+$/g, '');
                searchKey = searchKey.toLowerCase();
            });
            console.log('searchKeys', searchKeys);
            if (searchKeys && searchKeys.length > 0) {
                var filtersTemp = {};
                if ($scope.advancedFilter.allKeys) {
                    var filters = $scope.advancedFiltersOrg;
                    for (var i = 0; i < searchKeys.length; i++) {
                        filtersTemp = {};
                        var searchKey = searchKeys[i];
                        $scope.filterSearchRecursive(filters, filtersTemp, [searchKey]);
                        $scope.prune(filtersTemp, null, true);
                        filters = filtersTemp;
                    }
                    $scope.filters = filtersTemp;

                } else {
                    $scope.filterSearchRecursive($scope.advancedFiltersOrg, filtersTemp, searchKeys);
                    $scope.prune(filtersTemp, null, true);
                    $scope.filters = filtersTemp;
                }
                console.log('filtersTemp', filtersTemp);
            } else {
                $scope.filters = $scope.advancedFiltersOrg;
            }
        };

        $scope.resetFilters = function() {
            $scope.filters = angular.copy($scope.filtersOrg);
            $scope.appliedFilters = angular.copy($scope.appliedFiltersOrg);
            $scope.filteredNodes = ResourceFactory.allNodes;
            makeChunks();
        };

        $scope.removeFilter = function(key, value) {
            var keyArr = key.split('~') || [];
            if (_.isNumber(value)) {
                value = value.toString();
            }
            console.log('keyArr', keyArr);
            var thisFilter = $scope.appliedFilters;
            for (var i = 0; i < keyArr.length; i++) {
                console.log('thisFilter', thisFilter);
                console.log('i', i);
                console.log('keyArr[i]', keyArr[i]);
                var k = keyArr[i].toLowerCase();
                thisFilter = thisFilter[k];
            }
            console.log('value', value);
            console.log('thisFilter[value]', thisFilter[value]);
            thisFilter[value] = false;
            $scope.applyFilter();
            console.log('flatAppliedFilters', $scope.flatAppliedFilters);
        };


        $scope.applyFilter = function() {
            $scope.prunedAppliedFilters = angular.copy($scope.appliedFilters);
            $scope.prune($scope.prunedAppliedFilters, null, true);
            var prunedAppliedFilters = angular.copy($scope.prunedAppliedFilters);
            ResourceFactory.flatAppliedFilters = {};
            ResourceFactory.flatten(prunedAppliedFilters);
            $scope.flatAppliedFilters = ResourceFactory.flatAppliedFilters;
            ResourceFactory.prunedAppliedFilters = prunedAppliedFilters;
            $scope.intersectArray = [];
            $scope.createIntersectArray();
            var filteredNodes = null;
            if ($scope.intersectArray.length > 0) {
                _.each($scope.intersectArray, function(arr) {
                    if (filteredNodes === null) {
                        filteredNodes = arr;
                    } else if (filteredNodes.length > 0) {
                        filteredNodes = _.intersection(filteredNodes, arr);
                    }
                });
            }
            $scope.prune(prunedAppliedFilters, null, false);
            if (_.isEmpty(prunedAppliedFilters)) {
                $scope.filteredNodes = ResourceFactory.allNodes;
            } else {
                $scope.filteredNodes = _.filter(ResourceFactory.allNodes, function(node) {
                    return _.contains(filteredNodes, node.uid);
                });
            }
            ResourceFactory.processNodes($scope.filteredNodes);
            ResourceFactory.filteredNodes = $scope.filteredNodes;
            $scope.filters = angular.copy(ResourceFactory.filters);
            makeChunks();
        };
    }]);
