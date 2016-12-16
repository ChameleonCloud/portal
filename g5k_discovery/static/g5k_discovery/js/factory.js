'use strict';
angular.module('discoveryApp')
    .factory('UtilFactory', ['_', 'moment', function(_, moment) {
        var factory = {};
        factory.nameMap = {
            'smp_size': '# CPUs',
            'smt_size': '# Threads',
            'ram_size': 'RAM Size',
            'cache_l1': 'Cache L1',
            'cache_l2': 'Cache L2',
            'cache_l3': 'Cache L3',
            'cache_l1d': 'Cache L1d',
            'cache_l1i': 'Cache L1i',
            'clock_speed': 'Clock Speed',
            'rate': 'Rate',
            'size': 'Size',
            'humanized_size': 'Size',
            'gpu': 'GPU',
            'node_type': 'Node Type',
            'besteffort': 'Best Effort',
            'true': 'Yes',
            'false': 'No'
        };
        //RAM Size and disk size provided as humanized and byte size could not be related by a formula, thus mapping
        factory.sizeMap = {
            '12 GiB': 12587876352,
            '64 GiB':  67445407744,
            '128 GiB': 134956859392,
            '146 GB': 14681573376,
            '250 GB': 250059350016,
            '400 GB': 400088457216 ,
            '500 GB': 500107862016,
            '1 TB': 1000204886016,
            '2 TB': 2000398934016
        };


        // Node Types:
        //
        // "compute" -> Compute Nodes
        // "compute_ib" -> Infiniband
        // "fpga" -> FPGA
        // "gpu_k80" -> NVIDIA K80 GPU
        // "gpu_m40" -> NVIDIA M40 GPU
        // "storage" -> Storage Nodes
        // "storage_hierarchy" -> Storage Hierarchy

        //factory.tagMap = {
        //    'architecture~smt_size:48': 'Compute Nodes',
        //    'storage_devices~16~device:sdq': 'Storage Nodes',
        //    'gpu~gpu:yes': 'GPU',
        //    'infiniband': 'Infiniband Support',
        //    'network_adapters~4~interface:InfiniBand': 'Infiniband Support',
        //    'node_type:fpga': 'FPGA',
        //    'node_type:lowpower_xeon': 'Low Power Xeon',
        //    'node_type:atom': 'Atom'
        //};

        factory.tagMap = {
            'compute': 'Compute Nodes',
            'storage': 'Storage Nodes',
            'storage_heirarchy': 'Storage Heirarchy Nodes',
            'gpu_k80': 'NVIDIA K80 GPU Nodes',
            'gpu_m40': 'NVIDIA M40 GPU Nodes',
            'node_type:compute_ib': 'Nodes with Infiniband Support',
            'node_type:fpga': 'FPGA Nodes',
            'node_type:lowpower_xeon': 'Low Power Xeon Nodes',
            'node_type:atom': 'Atom Nodes'
        };

        factory.nameMap = _.extend(factory.nameMap, factory.tagMap);

        factory.isShowValTag = function(key, val) {
            if(val && val.length > 0){
               key += ':' + val;
            }
            return factory.tagMap[key] ? false : true;
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
        
        factory.humanizedToBytes = function(str) {
            var size = factory.sizeMap[str];
            if (size) {
                return size;
            }
            if(!str || str.length < 4){
               return str;
            }
            else{
                if(str.indexOf('KiB') > -1){
                  str = parseFloat(str.substring(0, str.length-4), 10) * 1024;
                  return str;
                }
                else if(str.indexOf('MiB') > -1){
                  str = parseFloat(str.substring(0, str.length-4), 10) * 1024 * 1024;
                  return str;
                }
                 else if(str.indexOf('GiB') > -1){
                  str = parseFloat(str.substring(0, str.length-4), 10) * 1024 * 1024 * 1024;
                  return str;
                }
                 else if(str.indexOf('TiB') > -1){
                  str = parseFloat(str.substring(0, str.length-4), 10) * 1024 * 1024 * 1024 * 1024;
                  return str;
                }
                 else if(str.indexOf('PiB') > -1){
                  str = parseFloat(str.substring(0, str.length-4), 10) * 1024 * 1024 * 1024 * 1024 * 1024;
                  return str;
                }
                else if(str.indexOf('KHz') > -1){
                  str = parseFloat(str.substring(0, str.length-4), 10) * 1000;
                  return str;
                }
                else if(str.indexOf('MHz') > -1){
                  str = parseFloat(str.substring(0, str.length-4), 10) * 1000 * 1000;
                  return str;
                }
                else if(str.indexOf('GHz') > -1){
                  str = parseFloat(str.substring(0, str.length-4), 10) * 1000 * 1000 * 1000;
                  return str;
                }
                else if(str.indexOf('THz') > -1){
                  str = parseFloat(str.substring(0, str.length-4), 10) * 1000 * 1000 * 1000 * 1000;
                  return str;
                }
                else if(str.indexOf('PHz') > -1){
                  str = parseFloat(str.substring(0, str.length-4), 10) * 1000 * 1000 * 1000 * 1000;
                  return str;
                }
                else{
                    return str;
                }
            }
        };

        factory.scaleMemory = function(num) {
            var scale = ['Bytes', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB'];
            var index = 0;
            while (num >= 1024) {
                num = (num / 1024).toFixed(2);
                index++;
            }
            return num + ' ' + scale[index];
        };

        factory.scaleFrequency = function(num) {
            var scale = ['Hz', 'KHz', 'MHz', 'GHz', 'THz', 'PHz'];
            var index = 0;
            while (num >= 1000) {
                num = (num / 1000).toFixed(2);
                index++;
            }
            return num + ' ' + scale[index];
        };

        factory.snakeToReadable = function(str, opt) {
            var strOrg = str;
            if(opt && opt.length > 0){
               str += ':' + opt;
            }
            var name = factory.nameMap[str];
            if (name) {
                return name;
            }
            else{
                str = strOrg;
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

        factory.getFormattedDate = function(date, time) {
            if (!time || !time instanceof Date) {
                time = date;
            }
            if (!date || !date instanceof Date) {
                return null;
            }
            var dateString = moment(date).format('YYYY-MM-DD');
            var timeString = moment(time).format('HH:mm');
            var combinedDate = moment(dateString + ' ' + timeString + ':00').utc();
            return moment(combinedDate).format('YYYY-MM-DD HH:mm');
        };

        return factory;
    }])
    .factory('ResourceFactory', ['$q', '$http', '_', 'UtilFactory', function($q, $http, _, UtilFactory) {
        //Step I: Fetch sites
        var factory = {};

        factory.formatNode = function(node) {
            delete node.links;
            delete node.type;
            try {
                if (typeof node['supported_job_types']['besteffort'] !== 'undefined' && node['supported_job_types']['besteffort'] !== null) {
                    node['supported_job_types']['besteffort'] = node['supported_job_types']['besteffort']?'yes':'no';
                }
            } catch (err) {}
            try {
                if (typeof node['supported_job_types']['deploy'] !== 'undefined' && node['supported_job_types']['deploy'] !== null) {
                    node['supported_job_types']['deploy'] = node['supported_job_types']['deploy']?'yes':'no';
                }
            } catch (err) {}
            try {
                if (typeof node['gpu']['gpu'] !== 'undefined' && node['gpu']['gpu'] !== null) {
                    node['gpu']['gpu'] = node['gpu']['gpu']?'yes':'no';
                }
            } catch (err) {}
            try {
                if (typeof node['monitoring']['wattmeter'] !== 'undefined' && node['monitoring']['wattmeter'] !== null) {
                    node['monitoring']['wattmeter'] = node['monitoring']['wattmeter']?'yes':'no';
                }
            } catch (err) {}
            try {
                if (typeof node['processor']['cache_l1'] !== 'undefined' && node['processor']['cache_l1'] !== null) {
                    node['processor']['cache_l1'] = UtilFactory.scaleMemory(node['processor']['cache_l1']);
                }
            } catch (err) {}
            try {
                if (typeof node['processor']['cache_l2'] !== 'undefined' && node['processor']['cache_l2'] !== null) {
                    node['processor']['cache_l2'] = UtilFactory.scaleMemory(node['processor']['cache_l2']);
                }
            } catch (err) {}
            try {
                if (typeof node['processor']['cache_l3'] !== 'undefined' && node['processor']['cache_l3'] !== null) {
                    node['processor']['cache_l3'] = UtilFactory.scaleMemory(node['processor']['cache_l3']);
                }
            } catch (err) {}
            try {
                if (typeof node['processor']['cache_l1d'] !== 'undefined' && node['processor']['cache_l1d'] !== null) {
                    node['processor']['cache_l1d'] = UtilFactory.scaleMemory(node['processor']['cache_l1d']);
                }
            } catch (err) {}
            try {
                if (typeof node['processor']['cache_l1i'] !== 'undefined' && node['processor']['cache_l1i'] !== null) {
                    node['processor']['cache_l1i'] = UtilFactory.scaleMemory(node['processor']['cache_l1i']);
                }
            } catch (err) {}
            try {
                if (typeof node['processor']['clock_speed'] !== 'undefined' && node['processor']['clock_speed'] !== null) {
                    node['processor']['clock_speed'] = UtilFactory.scaleFrequency(node['processor']['clock_speed']);
                }
            } catch (err) {}
            try {
              if (typeof node['node_type'] !== 'undefined' && node['node_type'] !== null) {
                  node['node_type'] = node['node_type']
              }
            } catch (err) {}
            try {
                var networkAdapters = node['network_adapters'];
                if (!_.isEmpty(networkAdapters) && networkAdapters.length > 0) {
                    _.each(networkAdapters, function(networkAdapter) {
                        if (typeof networkAdapter['rate'] !== 'undefined' && networkAdapter['rate'] !== null) {
                            networkAdapter['rate'] = UtilFactory.scaleFrequency(networkAdapter['rate']);
                        }
                        if (typeof networkAdapter['mounted'] !== 'undefined' && networkAdapter['mounted'] !== null) {
                            networkAdapter['mounted'] = networkAdapter['mounted']?'yes':'no';
                        }
                        if (typeof networkAdapter['management'] !== 'undefined' && networkAdapter['management'] !== null) {
                            networkAdapter['management'] = networkAdapter['management']?'yes':'no';
                        }
                        if (typeof networkAdapter['bridged'] !== 'undefined' && networkAdapter['bridged'] !== null) {
                            networkAdapter['bridged'] = networkAdapter['bridged']?'yes':'no';
                        }
                    });
                }
            } catch (err) {}            
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
        factory.flatten = function(appliedFilters, ky) {
            ky = ky || '';
            for (var key in appliedFilters) {
                if (_.isArray(appliedFilters[key])) {
                    var arr = appliedFilters[key];
                    for (var i = 0; i < arr.length; i++) {
                        var k1 = ky + key + '~' + i + '~';
                        factory.flatten(arr[i], k1);
                    }
                } else if (_.isObject(appliedFilters[key])) {
                    var k2 = ky + key + '~';
                    factory.flatten(appliedFilters[key], k2);
                } else if (appliedFilters[key] === true) {
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
    }])
    .factory('UserSelectionsFactory', ['moment', function(moment) {
        var factory = {};
        factory.userSelections = null;
        var dateS = moment();
        dateS.hours(15);
        dateS.minutes(0);
        dateS.seconds(0);
        dateS = moment(dateS).format('YYYY-MM-DDTHH:mm:ss') + 'Z';
        factory.userSelectionsInit = function() {
            factory.userSelections = {
                startDate: '',
                startTime: dateS,
                endDate: '',
                endTime: dateS,
                minNode: '',
                maxNode: ''
            };
        };
        factory.getUserSelections = function() {
            if(factory.userSelections === null){
               factory.userSelectionsInit();
            }
            return factory.userSelections;
        };
        return factory;
    }]);
