angular.module('discoveryApp')
    .factory('UtilFactory', ['_', function(_) {
        var factory = {};
        var nameMap = {
            'smp_size': '# CPUs',
            'smt_size': '# Cores',
            'ram_size': 'RAM (MiB)',
            'cache_l1': 'Cache L1 (KiB)',
            'cache_l2': 'Cache L2 (KiB)',
            'cache_l1d': 'Cache L1d (KiB)',
            'cache_l1i': 'Cache L1i (KiB)',
            'clock_speed': 'Clock Speed (GHz)'
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
            str = str.replace(/(_[a-z\d])/g, function(m) {
                if (!isNaN(parseInt(m[1]))) {
                    m = ' #' + m[1];
                } else {
                    m = ' ' + m[1].toUpperCase();
                }
                return m;
            });
            return str.charAt(0).toUpperCase() + str.slice(1);
        }
        return factory;
    }])
    .factory('ResourceFactory', ['$q', '$http', '_', 'UtilFactory', function($q, $http, _, UtilFactory) {
        //Step I: Fetch sites
        var factory = {};
        factory.sites = [];
        factory.allNodes = [];
        factory.filters = {};
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
                            cluster_link = _.findWhere(links, {
                                rel: 'clusters'
                            });
                            if (cluster_link) {
                                cluster_link_href = (cluster_link.href.substring(1)) + '.json';
                                //Step II: Fetch Clusters
                                var promise_clusters = $http({
                                        method: 'GET',
                                        url: cluster_link_href,
                                        cache: 'true'
                                    })
                                    .then(function(response) {
                                            site.clusters = response.data.items;
                                            _.each(site.clusters, function(cluster, index) {
                                                var links = cluster.links
                                                node_link = _.findWhere(links, {
                                                    rel: 'nodes'
                                                });
                                                if (node_link) {
                                                    nodes_link_href = (node_link.href.substring(1)) + '.json';
                                                    //Step III: Fetch Nodes
                                                    var promise_nodes = $http({
                                                            method: 'GET',
                                                            url: nodes_link_href,
                                                            cache: 'true'
                                                        })
                                                        .then(function(response) {
                                                                cluster.nodes = response.data.items;
                                                                _.each(cluster.nodes, function(node) {
                                                                    node.site = site.uid;
                                                                    node.cluster = cluster.uid;
                                                                    delete node.links;
                                                                    factory.allNodes.push(node);
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
                                                    if ((parentIndex === factory.sites.length - 1) && (index === site.clusters.length - 1)) {
                                                        $q.all(promises).then(function() {
                                                            scope.loading = false;
                                                            successCallBack();
                                                        });
                                                    }
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
        }

        factory.pruneFilters = function(filters, ky) {
            var filtersOrg = filters;
            filters = (typeof filters === 'undefined') ? factory.filters : filters[ky];
            for (var key in filters) {
                if (_.isObject(filters[key]) && !_.isArray(filters[key]) && !UtilFactory.isEmpty(filters[key])) {
                    factory.pruneFilters(filters, key);
                } 
                else if (_.isArray(filters[key]) && !UtilFactory.isEmpty(filters[key])) {
                    if(_.isObject(filters[key][0])){
                        for (var i = 0; i < filters[key].length; i++) {
                           factory.pruneFilters(filters[key], i);
                        }
                    }
                }
                else if (UtilFactory.isEmpty(filters[key])) { 
                    delete filters[key];
                }
            }
            if (UtilFactory.isEmpty(filters) && typeof ky !== 'undefined') {
                    delete filtersOrg[ky];
                }
        }

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
                        if (!(key === 'type' || key === 'uid' || key === 'version' || key === 'mac' || key === 'guid' || key === 'serial')) {
                            if (filters.hasOwnProperty(key)) {
                                var subKey = node[key];
                                if (subKey) {
                                    if (typeof filters[key][subKey] === 'undefined') {
                                        filters[key][subKey] = [];
                                    }
                                    filters[key][subKey].push(uid);
                                }
                            } else {
                                filters[key] = {};
                                var subKey = node[key];
                                if (subKey) {
                                    filters[key][subKey] = [];
                                    filters[key][subKey].push(uid);
                                }
                            }
                        }
                    }
                }
            }
        }

        factory.processNodes = function(nodes) {
            if (UtilFactory.isEmpty(nodes)) {
                return;
            }
            _.each(nodes, function(node) {
                processNode(node, node['uid']);
            });
            factory.pruneFilters();
            console.log('filters:', factory.filters);
        }
        return factory;
    }]);
