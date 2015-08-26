'use strict';
angular.module('discoveryApp')
    .factory('UtilFactory', ['_', function(_) {
        var factory = {};
        var nameMap = {
            'smp_size': '# CPUs',
            'smt_size': '# Cores',
            'ram_size': 'RAM',
            'cache_l1': 'Cache L1',
            'cache_l2': 'Cache L2',
            'cache_l3': 'Cache L3',
            'cache_l1d': 'Cache L1d',
            'cache_l1i': 'Cache L1i',
            'clock_speed': 'Clock Speed',
            'rate': 'Rate',
            'size': 'Size',
            'gpu': 'GPU',
            'besteffort': 'Best Effort',
            'true': 'Yes',
            'false': 'No'
        };

        var tagMap = {
            'architecture~smt_size' : 'Compute Nodes',
            'storage_devices~16~device' : 'Storage Nodes',
            'gpu~gpu' : 'With GPU',
            'infiniband' : 'With Infiniband'
        };

        nameMap = _.extend(nameMap, tagMap);

        factory.isShowValTag = function(key){
            return tagMap[key]?false:true;
        };

        factory.isEmpty = function(obj) {
            if (typeof obj === 'undefined' || !obj) {
                return true;
            } else if (angular.isArray(obj) && obj.length === 0) {
                return true;
            } else if (angular.isObject(obj) && _.isEmpty(obj)) {
                return true;
            } else {
                return false;
            }
        };

        factory.snakeToReadable = function(str) {
            var name = nameMap[str];
            if (name) {
                return name;
            }
            str = str + '';
            str = str.replace(/([_~][a-z\d])/g, function(m) {
                if (!isNaN(parseInt(m[1]))) {
                    m = ' #' + m[1];
                } else {
                    m = ' ' + m[1].toUpperCase();
                }
                return m;
            });
            return str.charAt(0).toUpperCase() + str.slice(1);
        };
        return factory;
    }])
    .factory('ResourceFactory', ['$q', '$http', '_', 'UtilFactory', function($q, $http, _, UtilFactory) {
        //Step I: Fetch sites
        var factory = {};

        factory.scaleMemory = function(num){
           var scale= ['Bytes', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB'];
           var index = 0;
           while(num > 1024){
             num = (num/1024).toFixed(2);
             index++;
           }
           return num + ' ' + scale[index];
        };

        factory.scaleFrequency = function(num){
           var scale= ['Hz', 'KHz', 'MHz', 'GHz', 'THz', 'PHz'];
           var index = 0;
           while(num >= 1000){
             num = (num/1000).toFixed(2);
             index++;
           }
           return num + ' ' + scale[index];
        };

        factory.formatNode = function(node){
            delete node.links;
            delete node.type;
            try{
                node['main_memory']['ram_size'] = factory.scaleMemory(node['main_memory']['ram_size']);
            }
            catch(err){}
            try{
                if(typeof node['processor']['cache_l1'] !== 'undefined' && node['processor']['cache_l1'] !== null){
                    node['processor']['cache_l1'] = factory.scaleMemory(node['processor']['cache_l1']);
                }
            }
            catch(err){}
            try{
                if(typeof node['processor']['cache_l2'] !== 'undefined' && node['processor']['cache_l2'] !== null){
                    node['processor']['cache_l2'] = factory.scaleMemory(node['processor']['cache_l2']);
                }
            }
            catch(err){}
            try{
                if(typeof node['processor']['cache_l3'] !== 'undefined' && node['processor']['cache_l3'] !== null){
                    node['processor']['cache_l3'] = factory.scaleMemory(node['processor']['cache_l3']);
                }
            }
            catch(err){}
            try{
                if(typeof node['processor']['cache_l1d'] !== 'undefined' && node['processor']['cache_l1d'] !== null){
                    node['processor']['cache_l1d'] = factory.scaleMemory(node['processor']['cache_l1d']);
                }
            }
            catch(err){}
            try{
                if(typeof node['processor']['cache_l1i'] !== 'undefined' && node['processor']['cache_l1i'] !== null){
                    node['processor']['cache_l1i'] = factory.scaleMemory(node['processor']['cache_l1i']);
                }
            }
            catch(err){}            
            try{
                if(typeof node['processor']['clock_speed'] !== 'undefined' && node['processor']['clock_speed'] !== null){
                    node['processor']['clock_speed'] = factory.scaleFrequency(node['processor']['clock_speed']);
                }
            }
            catch(err){}
            try{
                var networkAdapters = node['network_adapters'];
                if(!_.isEmpty(networkAdapters) && networkAdapters.length > 0){
                   _.each(networkAdapters, function(networkAdapter){
                    if(typeof networkAdapter['rate'] !== 'undefined' && networkAdapter['rate'] !== null){
                    networkAdapter['rate'] = factory.scaleFrequency(networkAdapter['rate']);
                }
                   });
                }
            }
            catch(err){}
            try{
                var storageDevices = node['storage_devices'];
                if(!_.isEmpty(storageDevices) && storageDevices.length > 0){
                   _.each(storageDevices, function(storageDevice){
                    if(typeof storageDevice['size'] !== 'undefined' && storageDevice['size'] !== null){
                    storageDevice['size'] = factory.scaleMemory(storageDevice['size']);
                }
                   });
                }
            }
            catch(err){}
        };

        factory.sites = [];
        factory.allNodes = [];
        factory.filters = {};
        factory.prunedAppliedFilters = {};
        factory.flatAppliedFilters = {};
        var promises = [];
        factory.getResources = function(scope, successCallBack, errorCallBack) {
            scope.loading = true;
            scope.loadingError = false;
            var promise_sites = $http({
                    method: 'GET',
                    url: 'sites.json',
                    cache: 'true'
                })
                .then(function(response) {
                        factory.sites = response.data.items;
                        _.each(factory.sites, function(site, parentIndex) {
                            var links = site.links;
                            var cluster_link = _.findWhere(links, {
                                rel: 'clusters'
                            });
                            if (cluster_link) {
                                var cluster_link_href = (cluster_link.href.substring(1)) + '.json';
                                //Step II: Fetch Clusters
                                var promise_clusters = $http({
                                        method: 'GET',
                                        url: cluster_link_href,
                                        cache: 'true'
                                    })
                                    .then(function(response) {
                                            site.clusters = response.data.items;
                                            _.each(site.clusters, function(cluster, clusterIndex) {
                                                var links = cluster.links;
                                                var node_link = _.findWhere(links, {
                                                    rel: 'nodes'
                                                });
                                                if (node_link) {
                                                    var nodes_link_href = (node_link.href.substring(1)) + '.json';
                                                    //Step III: Fetch Nodes
                                                    var promise_nodes = $http({
                                                            method: 'GET',
                                                            url: nodes_link_href,
                                                            cache: 'true'
                                                        })
                                                        .then(function(response) {
                                                                cluster.nodes = response.data.items;
                                                                _.each(cluster.nodes, function(node, nodeIndex) {
                                                                    node.site = site.uid;
                                                                    node.cluster = cluster.uid;
                                                                    factory.formatNode(node);
                                                                    factory.allNodes.push(node);
                                                                    if ((parentIndex === factory.sites.length - 1) && (clusterIndex === site.clusters.length - 1) && (nodeIndex === cluster.nodes.length - 1)) {
                                                                        $q.all(promises).then(function() {
                                                                            scope.loading = false;
                                                                            successCallBack();
                                                                        });
                                                                    }
                                                                });
                                                                return response;
                                                            },
                                                            function(response) {
                                                                scope.loadingError = true;
                                                                scope.loading = false;
                                                                errorCallBack('There was an error fetching nodes.');
                                                                return response;
                                                            });
                                                    promises.push(promise_nodes);
                                                } else {
                                                    scope.loadingError = true;
                                                    scope.loading = false;
                                                    errorCallBack('Node link is missing.');
                                                }
                                            });
                                            return response;
                                        },
                                        function(response) {
                                            scope.loadingError = true;
                                            scope.loading = false;
                                            errorCallBack('There was an error fetching clusters.');
                                            return response;
                                        });
                                promises.push(promise_clusters);
                            } else {
                                scope.loadingError = true;
                                scope.loading = false;
                                errorCallBack('Cluster link is missing.');
                            }
                        });
                        return response;
                    },
                    function(response) {
                        scope.loadingError = true;
                        scope.loading = false;
                        errorCallBack('There was an error fetching sites.');
                        return response;
                    });
            promises.push(promise_sites);
        };

        factory.pruneFilters = function(filters, ky) {
            var filtersOrg = filters;
            filters = (typeof filters === 'undefined') ? factory.filters : filters[ky];
            for (var key in filters) {
                if (_.isObject(filters[key]) && !_.isArray(filters[key]) && !UtilFactory.isEmpty(filters[key])) {
                    factory.pruneFilters(filters, key);
                } else if (_.isArray(filters[key]) && !UtilFactory.isEmpty(filters[key])) {
                    if (_.isObject(filters[key][0])) {
                        for (var i = 0; i < filters[key].length; i++) {
                            factory.pruneFilters(filters[key], i);
                        }
                    }
                } else if (UtilFactory.isEmpty(filters[key])) {
                    delete filters[key];
                }
            }
            if (UtilFactory.isEmpty(filters) && typeof ky !== 'undefined') {
                delete filtersOrg[ky];
            }
        };

        // make sure to set factory.flatAppliedFilters = {} before calling this function
        factory.flatten = function(appliedFilters, ky){
        ky = ky || '';
           for(var key in appliedFilters){
              if(_.isArray(appliedFilters[key])){
                var arr = appliedFilters[key];
                 for(var i=0; i<arr.length; i++){
                    var k1 = ky + key + '~' + i + '~';
                    factory.flatten(arr[i], k1);
                 }
              }
              else if(_.isObject(appliedFilters[key])){
                    var k2 = ky + key + '~';
                    factory.flatten(appliedFilters[key], k2);
              }
              else if(appliedFilters[key] === true){
                ky = ky.substring(0, ky.length - 1);
                 factory.flatAppliedFilters[ky] = key; 
              }
           }
    };

        var processNode = function(node, uid, filters) {
            filters = (typeof filters === 'undefined') ? factory.filters : filters;
            for (var key in node) {
                if (node.hasOwnProperty(key)) {
                    if (_.isArray(node[key])) {
                        if (typeof filters[key] === 'undefined') {
                            filters[key] = [];
                        }
                        for (var i = 0; i < node[key].length; i++) {
                            if (typeof filters[key][i] === 'undefined') {
                                filters[key][i] = {};
                            }
                            processNode(node[key][i], uid, filters[key][i]);
                        }
                    } else if (_.isObject(node[key])) {
                        if (typeof filters[key] === 'undefined') {
                            filters[key] = {};
                        }
                        processNode(node[key], uid, filters[key]);
                    } else {
                        if (!(key === 'type' || key === 'uid' || key === 'guid' || key === 'mac' || key === 'serial')) {
                            var subKey = '';
                            if (filters.hasOwnProperty(key)) {
                                subKey = node[key];
                                //this keeps values that are false
                                if (subKey !== null && subKey !== '') {
                                    if (typeof filters[key][subKey] === 'undefined') {
                                        filters[key][subKey] = [];
                                    }
                                    filters[key][subKey].push(uid);
                                }
                            } else {
                                filters[key] = {};
                                subKey = node[key];
                                if (subKey !== null && subKey !== '') {
                                    filters[key][subKey] = [];
                                    filters[key][subKey].push(uid);
                                }
                            }
                        }
                    }
                }
            }
        };

        factory.processNodes = function(nodes) {
            factory.filters = {};
            if (UtilFactory.isEmpty(nodes)) {
                return;
            }
            _.each(nodes, function(node) {
                processNode(node, node['uid']);
            });
            factory.pruneFilters();
        };
        return factory;
    }]);
