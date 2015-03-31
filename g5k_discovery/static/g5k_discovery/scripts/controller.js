/**
 * Created by agauli on 2/26/15.
 */
angular.module('discoveryApp')
    .controller('AppController', ['$scope', '$http', '_', '$q', '$timeout', function ($scope, $http, _, $q, $timeout) {
        $scope.selectednodes = $scope.allnodes = [];
        $scope.loading = true;
        $scope.loadingError = false;
        $scope.nodeStringMap = {};
        $scope.map = {};
        //keeps the node count for each filter
        $scope.init_var = function (noResetFilter) {

            if (!noResetFilter || noResetFilter !== 'sites_nodecount') {
                $scope.map.sites_nodecount = {};
            }
            if (!noResetFilter || noResetFilter !== 'clusters_nodecount') {
                $scope.map.clusters_nodecount = {};
            }
            if (!noResetFilter || noResetFilter !== 'virtual_support') {
                $scope.map.virtual_support = {};
            }
            if (!noResetFilter || noResetFilter !== 'best_effort_support') {
                $scope.map.best_effort_support = {};
            }
            if (!noResetFilter || noResetFilter !== 'deploy_support') {
                $scope.map.deploy_support = {};
            }
            if (!noResetFilter || noResetFilter !== 'net_adap_inf_1') {
                $scope.map.net_adap_inf_1 = {};
            }
            if (!noResetFilter || noResetFilter !== 'net_adap_inf_2') {
                $scope.map.net_adap_inf_2 = {};
            }
            if (!noResetFilter || noResetFilter !== 'net_adap_inf_3') {
                $scope.map.net_adap_inf_3 = {};
            }
            if (!noResetFilter || noResetFilter !== 'storage_dev_inf_1') {
                $scope.map.storage_dev_inf_1 = {};
            }
            if (!noResetFilter || noResetFilter !== 'storage_dev_inf_2') {
                $scope.map.storage_dev_inf_2 = {};
            }
            if (!noResetFilter || noResetFilter !== 'storage_dev_size_1') {
                $scope.map.storage_dev_size_1 = {};
            }
            if (!noResetFilter || noResetFilter !== 'storage_dev_size_2') {
                $scope.map.storage_dev_size_2 = {};
            }
            if (!noResetFilter || noResetFilter !== 'cpus') {
                $scope.map.cpus = {};
            }
            if (!noResetFilter || noResetFilter !== 'cores') {
                $scope.map.cores = {};
            }
            if (!noResetFilter || noResetFilter !== 'rams') {
                $scope.map.rams = {};
            }
            if (!noResetFilter || noResetFilter !== 'clocks') {
                $scope.map.clocks = {};
            }
            if (!noResetFilter || noResetFilter !== 'processor_models') {
                $scope.map.processor_models = {};
            }
            if (!noResetFilter || noResetFilter !== 'cache_l1d') {
                $scope.map.cache_l1d = {};
            }
            if (!noResetFilter || noResetFilter !== 'cache_l1i') {
                $scope.map.cache_l1i = {};
            }
            if (!noResetFilter || noResetFilter !== 'cache_l1') {
                $scope.map.cache_l1 = {};
            }
            if (!noResetFilter || noResetFilter !== 'cache_l2') {
                $scope.map.cache_l2 = {};
            }
            if (!noResetFilter || noResetFilter !== 'cache_l3') {
                $scope.map.cache_l3 = {};
            }
        }
        $scope.init_var();

        $scope.resetFilters = function () {
            $scope.filter = {
                selectedSites: {},
                selectedClusters: {},
                selectedSitesClusters: {},
                search: '',
                selectedVirtualSupport: {},
                selectedBestEffortSupport: {},
                selectedDeploySupport: {},
                selectedNetAdap1: {},
                selectedNetAdap2: {},
                selectedNetAdap3: {},
                selectedStorageDevInf1: {},
                selectedStorageDevInf2: {},
                selectedStorageDevSize1: {},
                selectedStorageDevSize2: {},
                selectedCpus: {},
                selectedCores: {},
                selectedRams: {},
                selectedClockSpeed: {},
                selectedProcessorModels: {},
                selectedCachel1d: {},
                selectedCachel1i: {},
                selectedCachel1: {},
                selectedCachel2: {},
                selectedCachel3: {}
            };
            $scope.selectednodes = $scope.allnodes;
            $scope.filteredSites = $scope.sites;
        }
        $scope.resetFilters();

        $scope.resetUI = function () {
            $scope.resetFilters();
            $scope.map = angular.copy($scope.mapOrg);
        }

        var searchTimeout = null;
        $scope.search = function () {
            if (searchTimeout) {
                $timeout.cancel(searchTimeout);
            }
            searchTimeout = $timeout(function () {
                $scope.preApplyOtherFilters();
            }, 500); // delay 500 ms

        }
        $scope.processNode = function (node, isFirstTimeOnly, noResetFilter) {

            if (!noResetFilter || noResetFilter !== 'virtual_support') {
                try {
                    var virtual_support = 'unknown';
                    var supported_job_types = node.supported_job_types;
                    if (supported_job_types && supported_job_types.virtual) {
                        virtual_support = supported_job_types.virtual;
                    }
                    if (!$scope.map.virtual_support.hasOwnProperty(virtual_support)) {
                        $scope.map.virtual_support[virtual_support] = {count: 1};
                    }
                    else {
                        $scope.map.virtual_support[virtual_support].count = $scope.map.virtual_support[virtual_support].count + 1;
                    }
                }
                catch (err) {
                    //pass
                }
            }

            if (!noResetFilter || noResetFilter !== 'deploy_support') {
                try {
                    var deploy_support = 'unknown';
                    var supported_job_types = node.supported_job_types;
                    if (supported_job_types && (typeof supported_job_types.deploy !== undefined && (supported_job_types.deploy !== null))) {
                        deploy_support = supported_job_types.deploy.toString();
                    }
                    if (!$scope.map.deploy_support.hasOwnProperty(deploy_support)) {
                        $scope.map.deploy_support[deploy_support] = {count: 1};
                    }
                    else {
                        $scope.map.deploy_support[deploy_support].count = $scope.map.deploy_support[deploy_support].count + 1;
                    }
                }
                catch (err) {
                    //pass
                }
            }

            if (!noResetFilter || noResetFilter !== 'best_effort_support') {
                try {
                    var best_effort_support = 'unknown';
                    var supported_job_types = node.supported_job_types;
                    if (supported_job_types && (typeof supported_job_types.besteffort !== undefined && (supported_job_types.besteffort !== null))) {
                        deploy_support = supported_job_types.besteffort.toString();
                    }
                    if (!$scope.map.best_effort_support.hasOwnProperty(best_effort_support)) {
                        $scope.map.best_effort_support[best_effort_support] = {count: 1};
                    }
                    else {
                        $scope.map.best_effort_support[best_effort_support].count = $scope.map.best_effort_support[best_effort_support].count + 1;
                    }
                }
                catch (err) {
                    //pass
                }
            }

            if (!noResetFilter || noResetFilter !== 'storage_dev_inf_1') {
                try {
                    var storage_interface = node.storage_devices[0].interface;
                    if (!storage_interface) {
                        storage_interface = 'unknown';
                    }
                    if (!$scope.map.storage_dev_inf_1.hasOwnProperty(storage_interface)) {
                        $scope.map.storage_dev_inf_1[storage_interface] = {count: 1};
                    }
                    else {
                        $scope.map.storage_dev_inf_1[storage_interface].count = $scope.map.storage_dev_inf_1[storage_interface].count + 1;
                    }
                }
                catch (err) {
                    //pass
                }
            }

            if (!noResetFilter || noResetFilter !== 'storage_dev_inf_2') {
                try {
                    var storage_interface = node.storage_devices[1].interface;
                    if (!storage_interface) {
                        storage_interface = 'unknown';
                    }
                    if (!$scope.map.storage_dev_inf_2.hasOwnProperty(storage_interface)) {
                        $scope.map.storage_dev_inf_2[storage_interface] = {count: 1};
                    }
                    else {
                        $scope.map.storage_dev_inf_2[storage_interface].count = $scope.map.storage_dev_inf_2[storage_interface].count + 1;
                    }
                }
                catch (err) {
                    //pass
                }
            }

            if (!noResetFilter || noResetFilter !== 'storage_dev_size_1') {
                try {
                    var storage_size = node.storage_devices[0].size;
                    if (!storage_size) {
                        storage_size = 'unknown';
                    }
                    else {
                        storage_size = Math.round(storage_size / (1024 * 1024 * 1024));
                    }

                    if (!$scope.map.storage_dev_size_1.hasOwnProperty(storage_size)) {
                        $scope.map.storage_dev_size_1[storage_size] = {count: 1};
                    }
                    else {
                        $scope.map.storage_dev_size_1[storage_size].count = $scope.map.storage_dev_size_1[storage_size].count + 1;
                    }
                }
                catch (err) {
                    //pass
                }
            }

             if (!noResetFilter || noResetFilter !== 'storage_dev_size_2') {
                try {
                    var storage_size = node.storage_devices[1].size;
                    if (!storage_size) {
                        storage_size = 'unknown';
                    }
                    else {
                        storage_size = Math.round(storage_size / (1024 * 1024 * 1024));
                    }

                    if (!$scope.map.storage_dev_size_2.hasOwnProperty(storage_size)) {
                        $scope.map.storage_dev_size_2[storage_size] = {count: 1};
                    }
                    else {
                        $scope.map.storage_dev_size_2[storage_size].count = $scope.map.storage_dev_size_2[storage_size].count + 1;
                    }
                }
                catch (err) {
                    //pass
                }
            }

            if (!noResetFilter || noResetFilter !== 'net_adap_inf_1') {
                try {
                    var net_adap = node.network_adapters[0].interface;
                    if (!net_adap) {
                        net_adap = 'unknown';
                    }
                    if (!$scope.map.net_adap_inf_1.hasOwnProperty(net_adap)) {
                        $scope.map.net_adap_inf_1[net_adap] = {count: 1};
                    }
                    else {
                        $scope.map.net_adap_inf_1[net_adap].count = $scope.map.net_adap_inf_1[net_adap].count + 1;
                    }
                }
                catch (err) {
                    //pass
                }
            }
            if (!noResetFilter || noResetFilter !== 'net_adap_inf_2') {
                try {
                    var net_adap = node.network_adapters[1].interface;
                    if (!net_adap) {
                        net_adap = 'unknown';
                    }
                    if (!$scope.map.net_adap_inf_2.hasOwnProperty(net_adap)) {
                        $scope.map.net_adap_inf_2[net_adap] = {count: 1};
                    }
                    else {
                        $scope.map.net_adap_inf_2[net_adap].count = $scope.map.net_adap_inf_2[net_adap].count + 1;
                    }
                }
                catch (err) {
                    //pass
                }
            }
            if (!noResetFilter || noResetFilter !== 'net_adap_inf_3') {
                try {
                    var net_adap = node.network_adapters[2].interface;
                    if (!net_adap) {
                        net_adap = 'unknown';
                    }
                    if (!$scope.map.net_adap_inf_3.hasOwnProperty(net_adap)) {
                        $scope.map.net_adap_inf_3[net_adap] = {count: 1};
                    }
                    else {
                        $scope.map.net_adap_inf_3[net_adap].count = $scope.map.net_adap_inf_3[net_adap].count + 1;
                    }
                }
                catch (err) {
                    //pass
                }
            }

            if (!noResetFilter || noResetFilter !== 'cpus') {
                try {
                    var cpu = node.architecture.smp_size;
                    if (!cpu) {
                        cpu = 'unknown';
                    }
                    if (!$scope.map.cpus.hasOwnProperty(cpu)) {
                        $scope.map.cpus[cpu] = {count: 1};
                    }
                    else {
                        $scope.map.cpus[cpu].count = $scope.map.cpus[cpu].count + 1;
                    }
                }
                catch (err) {
                    //pass
                }
            }

            if (!noResetFilter || noResetFilter !== 'cores') {
                try {
                    var core = node.architecture.smt_size;
                    if (!core) {
                        core = 'unknown';
                    }
                    if (!$scope.map.cores.hasOwnProperty(core)) {
                        $scope.map.cores[core] = {count: 1};
                    }
                    else {
                        $scope.map.cores[core].count = $scope.map.cores[core].count + 1;
                    }
                }
                catch (err) {
                    //pass
                }
            }

            if (!noResetFilter || noResetFilter !== 'rams') {
                try {
                    var ram = node.main_memory.ram_size;
                    if (!ram) {
                        ram = 'unknown';
                    }
                    else {
                        ram = Math.round(ram / (1024 * 1024));
                    }
                    if (!$scope.map.rams.hasOwnProperty(ram)) {
                        $scope.map.rams[ram] = {count: 1};
                    }
                    else {
                        $scope.map.rams[ram].count = $scope.map.rams[ram].count + 1;
                    }
                }
                catch (err) {
                    //pass
                }
            }

            if (!noResetFilter || noResetFilter !== 'clocks') {
                try {
                    var clock = node.processor.clock_speed;
                    if (!clock) {
                        clock = 'unknown';
                    }
                    else {
                        clock = clock / (1000000000).toFixed(2);
                    }

                    if (!$scope.map.clocks.hasOwnProperty(clock)) {
                        $scope.map.clocks[clock] = {count: 1};
                    }
                    else {
                        $scope.map.clocks[clock].count = $scope.map.clocks[clock].count + 1;
                    }
                }
                catch (err) {
                    //pass
                }
            }

            if (!noResetFilter || noResetFilter !== 'processor_models') {
                try {
                    var processor_model = node.processor.model;
                    if (!processor_model) {
                        processor_model = 'unknown';
                    }
                    if (!$scope.map.processor_models.hasOwnProperty(processor_model)) {
                        $scope.map.processor_models[processor_model] = {count: 1};
                    }
                    else {
                        $scope.map.processor_models[processor_model].count = $scope.map.processor_models[processor_model].count + 1;
                    }
                }
                catch (err) {
                    //pass
                }
            }

            if (!noResetFilter || noResetFilter !== 'cache_l1') {
                try {
                    var cache = node.processor.cache_l1;
                    if (!cache) {
                        cache = 'unknown';
                    }
                    else {
                        cache = Math.round(cache / 1024);
                    }

                    if (!$scope.map.cache_l1.hasOwnProperty(cache)) {
                        $scope.map.cache_l1[cache] = {count: 1};
                    }
                    else {
                        $scope.map.cache_l1[cache].count = $scope.map.cache_l1[cache].count + 1;
                    }
                }
                catch (err) {
                    //pass
                }
            }

            if (!noResetFilter || noResetFilter !== 'cache_l2') {
                try {
                    var cache = node.processor.cache_l2;
                    if (!cache) {
                        cache = 'unknown';
                    }
                    else {
                        cache = Math.round(cache / 1024);
                    }
                    if (!$scope.map.cache_l2.hasOwnProperty(cache)) {
                        $scope.map.cache_l2[cache] = {count: 1};
                    }
                    else {
                        $scope.map.cache_l2[cache].count = $scope.map.cache_l2[cache].count + 1;
                    }
                }
                catch (err) {
                    //pass
                }
            }

            if (!noResetFilter || noResetFilter !== 'cache_l3') {
                try {
                    var cache = node.processor.cache_l3;
                    if (!cache) {
                        cache = 'unknown';
                    }
                    else {
                        cache = Math.round(cache / 1024);
                    }
                    if (!$scope.map.cache_l3.hasOwnProperty(cache)) {
                        $scope.map.cache_l3[cache] = {count: 1};
                    }
                    else {
                        $scope.map.cache_l3[cache].count = $scope.map.cache_l3[cache].count + 1;
                    }
                }
                catch (err) {
                    //pass
                }
            }

            if (!noResetFilter || noResetFilter !== 'cache_l1d') {
                try {
                    var cache = node.processor.cache_l1d;
                    if (!cache) {
                        cache = 'unknown';
                    }
                    else {
                        cache = Math.round(cache / 1024);
                    }
                    if (!$scope.map.cache_l1d.hasOwnProperty(cache)) {
                        $scope.map.cache_l1d[cache] = {count: 1};
                    }
                    else {
                        $scope.map.cache_l1d[cache].count = $scope.map.cache_l1d[cache].count + 1;
                    }
                }
                catch (err) {
                    //pass
                }
            }

            if (!noResetFilter || noResetFilter !== 'cache_l1i') {
                try {
                    var cache = node.processor.cache_l1i;
                    if (!cache) {
                        cache = 'unknown';
                    }
                    else {
                        cache = Math.round(cache / 1024);
                    }
                    if (!$scope.map.cache_l1i.hasOwnProperty(cache)) {
                        $scope.map.cache_l1i[cache] = {count: 1};
                    }
                    else {
                        $scope.map.cache_l1i[cache].count = $scope.map.cache_l1i[cache].count + 1;
                    }
                }
                catch (err) {
                    //pass
                }
            }
            if (isFirstTimeOnly) {
                var nodeCopy = angular.copy(node);
                try{
                   nodeCopy.main_memory.ram_size = Math.round(nodeCopy.main_memory.ram_size / (1024 * 1024));
                }
                catch(err){
                   //pass
                }
                try{
                   nodeCopy.processor.clock_speed = nodeCopy.processor.clock_speed / (1000000000).toFixed(2);
                   nodeCopy.processor.cache_l1 = Math.round(nodeCopy.processor.cache_l1 / 1024);
                   nodeCopy.processor.cache_l2 = Math.round(nodeCopy.processor.cache_l2 / 1024);
                   nodeCopy.processor.cache_l3 = Math.round(nodeCopy.processor.cache_l3 / 1024);
                    nodeCopy.processor.cache_l1d = Math.round(nodeCopy.processor.cache_l1d / 1024);
                   nodeCopy.processor.cache_l1i = Math.round(nodeCopy.processor.cache_l1i / 1024);
                }
                catch(err){
                   //pass
                }
                 try{
                   nodeCopy.storage_devices[0].size = Math.round(nodeCopy.storage_devices[0].size / (1024 * 1024 * 1024));
                }
                catch(err){
                   //pass
                }

                $scope.nodeStringMap[node.uid] = JSON.stringify(nodeCopy);
                try {
                    var link = node.links[0].href;
                    if (link) {
                        var site_index = link.indexOf('/sites/');
                        var cluster_index = link.indexOf('/clusters/');
                        var node_index = link.indexOf('/nodes/');
                        var site = link.substring(site_index + 7, cluster_index);
                        node.site = site.toLowerCase();
                        var cluster = '';

                        if (node_index !== -1) {
                            cluster = link.substring(cluster_index + 10, node_index);
                        }
                        else {
                            cluster = link.substring(cluster_index + 10);
                        }
                        node.cluster = cluster.toLowerCase();

                        var siteObj = _.find($scope.filteredSites, function (s) {
                            return s.uid.toLowerCase() === site;
                        });
                        var siteObjOrg = _.find($scope.sites, function (s) {
                            return s.uid.toLowerCase() === site;
                        });

                        if (!siteObj.node_count) {
                            siteObj.node_count = 1;
                        }
                        else {
                            siteObj.node_count++;
                        }

                        if (!siteObjOrg.node_count) {
                            siteObjOrg.node_count = 1;
                        }
                        else {
                            siteObjOrg.node_count++;
                        }

                        var clusterObj = _.find(siteObj.clusters, function (c) {
                            return c.uid.toLowerCase() === cluster;
                        });

                        var clusterObjOrg = _.find(siteObjOrg.clusters, function (c) {
                            return c.uid.toLowerCase() === cluster;
                        });

                        if (!clusterObj.node_count) {
                            clusterObj.node_count = 1;
                        }
                        else {
                            clusterObj.node_count++;
                        }
                        if (!clusterObjOrg.node_count) {
                            clusterObjOrg.node_count = 1;
                        }
                        else {
                            clusterObjOrg.node_count++;
                        }
                    }

                }
                catch (err) {
                    //pass
                }
            }
        };

        $scope.applyOtherFilters = function (node) {
            var pass = true;
            if (!_.isEmpty($scope.filter.selectedVirtualSupport)) {
                var selectedVirtualSupport = [];
                for (var key in $scope.filter.selectedVirtualSupport) {
                    if ($scope.filter.selectedVirtualSupport[key] == true) {
                        selectedVirtualSupport.push(key.toLowerCase());
                    }
                }
                try {
                    if (typeof node.supported_job_types == undefined || !node.supported_job_types.virtual) {

                        if (selectedVirtualSupport.length !== 0 && !_.contains(selectedVirtualSupport, 'unknown')) {
                            pass = false;
                        }
                    }
                    else {
                        if (selectedVirtualSupport.length !== 0 && !_.contains(selectedVirtualSupport, node.supported_job_types.virtual)) {
                            pass = false;
                        }
                    }
                }
                catch (err) {
                    pass = false;
                    //console.log('Missing node.supported_job_types.virtual in '+node.uid);
                }
            }

            if (!_.isEmpty($scope.filter.selectedDeploySupport)) {
                var selectedDeploySupport = [];
                for (var key in $scope.filter.selectedDeploySupport) {
                    if ($scope.filter.selectedDeploySupport[key] == true) {
                        selectedDeploySupport.push(key.toLowerCase());
                    }
                }
                try {

                    if (typeof node.supported_job_types == undefined || !node.supported_job_types.deploy) {

                        if (selectedDeploySupport.length !== 0 && !_.contains(selectedDeploySupport, 'unknown')) {
                            pass = false;
                        }
                    }
                    else {
                        if (selectedDeploySupport.length !== 0 && !_.contains(selectedDeploySupport, node.supported_job_types.deploy.toString())) {
                            pass = false;
                        }
                    }

                }
                catch (err) {
                    pass = false;
                    //console.log('Missing node.supported_job_types.deploy in '+node.uid);
                }
            }

            if (!_.isEmpty($scope.filter.selectedBestEffortSupport)) {
                var selectedBestEffortSupport = [];
                for (var key in $scope.filter.selectedBestEffortSupport) {
                    if ($scope.filter.selectedBestEffortSupport[key] == true) {
                        selectedBestEffortSupport.push(key.toLowerCase());
                    }
                }
                try {

                    if (typeof node.supported_job_types == undefined || !node.supported_job_types.besteffort) {

                        if (selectedBestEffortSupport.length !== 0 && !_.contains(selectedBestEffortSupport, 'unknown')) {
                            pass = false;
                        }
                    }
                    else {
                        if (selectedBestEffortSupport.length !== 0 && !_.contains(selectedBestEffortSupport, node.supported_job_types.besteffort.toString())) {
                            pass = false;
                        }
                    }
                }
                catch (err) {
                    pass = false;
                    //console.log('Missing node.supported_job_types.besteffort in '+node.uid);
                }
            }

            var nodeString = $scope.nodeStringMap[node.uid];
            if (nodeString && nodeString.indexOf($scope.filter.search) < 0) {
                pass = false;
            }

            if (!_.isEmpty($scope.filter.selectedNetAdap1)) {
                var selectedNetAdap1 = [];
                for (var key in $scope.filter.selectedNetAdap1) {
                    if ($scope.filter.selectedNetAdap1[key] == true) {
                        selectedNetAdap1.push(key.toLowerCase());
                    }
                }
                try {
                    if (typeof node.network_adapters[0] == undefined || !node.network_adapters[0].interface) {

                        if (selectedNetAdap1.length !== 0 && !_.contains(selectedNetAdap1, 'unknown')) {
                            pass = false;
                        }
                    }
                    else {
                        if (selectedNetAdap1.length !== 0 && !_.contains(selectedNetAdap1, node.network_adapters[0].interface.toLowerCase())) {
                            pass = false;
                        }
                    }
                }
                catch (err) {
                    pass = false;
                    //console.log('Missing node.network_adapters[0] in '+node.uid);
                }
            }

            if (!_.isEmpty($scope.filter.selectedNetAdap2)) {
                var selectedNetAdap2 = [];
                for (var key in $scope.filter.selectedNetAdap2) {
                    if ($scope.filter.selectedNetAdap2[key] == true) {
                        selectedNetAdap2.push(key.toLowerCase());
                    }
                }
                try {

                    if (typeof node.network_adapters[1] == undefined || !node.network_adapters[1].interface) {

                        if (selectedNetAdap2.length !== 0 && !_.contains(selectedNetAdap2, 'unknown')) {
                            pass = false;
                        }
                    }
                    else {
                        if (selectedNetAdap2.length !== 0 && !_.contains(selectedNetAdap2, node.network_adapters[1].interface.toLowerCase())) {
                            pass = false;
                        }
                    }
                }
                catch (err) {
                    pass = false;
                    //console.log('Missing node.network_adapters[1] in '+node.uid);
                }
            }

            if (!_.isEmpty($scope.filter.selectedNetAdap3)) {
                var selectedNetAdap3 = [];
                for (var key in $scope.filter.selectedNetAdap3) {
                    if ($scope.filter.selectedNetAdap3[key] == true) {
                        selectedNetAdap3.push(key.toLowerCase());
                    }
                }
                try {

                    if (typeof node.network_adapters[2] == undefined || !node.network_adapters[2].interface) {

                        if (selectedNetAdap3.length !== 0 && !_.contains(selectedNetAdap3, 'unknown')) {
                            pass = false;
                        }
                    }
                    else {
                        if (selectedNetAdap3.length !== 0 && !_.contains(selectedNetAdap3, node.network_adapters[2].interface.toLowerCase())) {
                            pass = false;
                        }
                    }
                }
                catch (err) {
                    pass = false;
                    //console.log('Missing node.network_adapters[2] in '+node.uid);
                }
            }

            if (!_.isEmpty($scope.filter.selectedStorageDevInf1)) {
                var selectedStorageDevInf1 = [];
                for (var key in $scope.filter.selectedStorageDevInf1) {
                    if ($scope.filter.selectedStorageDevInf1[key] == true) {
                        selectedStorageDevInf1.push(key.toLowerCase());
                    }
                }
                try {

                    if (typeof node.storage_devices[0] == undefined || !node.storage_devices[0].interface) {

                        if (selectedStorageDevInf1.length !== 0 && !_.contains(selectedStorageDevInf1, 'unknown')) {
                            pass = false;
                        }
                    }
                    else {
                        if (selectedStorageDevInf1.length !== 0 && !_.contains(selectedStorageDevInf1, node.storage_devices[0].interface.toLowerCase())) {
                            pass = false;
                        }
                    }
                }
                catch (err) {
                    pass = false;
                    //console.log('Missing node.storage_devices[0].interface in '+node.uid);
                }
            }

            if (!_.isEmpty($scope.filter.selectedStorageDevInf2)) {
                var selectedStorageDevInf2 = [];
                for (var key in $scope.filter.selectedStorageDevInf2) {
                    if ($scope.filter.selectedStorageDevInf2[key] == true) {
                        selectedStorageDevInf2.push(key.toLowerCase());
                    }
                }
                try {

                    if (typeof node.storage_devices[1] == undefined || !node.storage_devices[1].interface) {

                        if (selectedStorageDevInf2.length !== 0 && !_.contains(selectedStorageDevInf2, 'unknown')) {
                            pass = false;
                        }
                    }
                    else {
                        if (selectedStorageDevInf2.length !== 0 && !_.contains(selectedStorageDevInf2, node.storage_devices[1].interface.toLowerCase())) {
                            pass = false;
                        }
                    }
                }
                catch (err) {
                    pass = false;
                    //console.log('Missing node.storage_devices[1].interface in '+node.uid);
                }
            }

            if (!_.isEmpty($scope.filter.selectedStorageDevSize1)) {
                var selectedStorageDevSize1 = [];
                for (var key in $scope.filter.selectedStorageDevSize1) {
                    if ($scope.filter.selectedStorageDevSize1[key] == true) {
                        selectedStorageDevSize1.push(key);
                    }
                }
                try {

                    if (typeof node.storage_devices[0] == undefined || !node.storage_devices[0].size) {

                        if (selectedStorageDevSize1.length !== 0 && !_.contains(selectedStorageDevSize1, 'unknown')) {
                            pass = false;
                        }
                    }
                    else {
                        var storage_size = Math.round(node.storage_devices[0].size / (1024 * 1024 * 1024));
                        if (selectedStorageDevSize1.length !== 0 && !_.contains(selectedStorageDevSize1, storage_size.toString())) {
                            pass = false;
                        }
                    }
                }
                catch (err) {
                    pass = false;
                    //console.log('Missing node.storage_devices[0].size in '+node.uid);
                }
            }

            if (!_.isEmpty($scope.filter.selectedStorageDevSize2)) {
                var selectedStorageDevSize2 = [];
                for (var key in $scope.filter.selectedStorageDevSize2) {
                    if ($scope.filter.selectedStorageDevSize2[key] == true) {
                        selectedStorageDevSize2.push(key);
                    }
                }
                try {

                    if (typeof node.storage_devices[1] == undefined || !node.storage_devices[1].size) {

                        if (selectedStorageDevSize2.length !== 0 && !_.contains(selectedStorageDevSize2, 'unknown')) {
                            pass = false;
                        }
                    }
                    else {
                        var storage_size = Math.round(node.storage_devices[1].size / (1024 * 1024 * 1024));
                        if (selectedStorageDevSize2.length !== 0 && !_.contains(selectedStorageDevSize2, storage_size.toString())) {
                            pass = false;
                        }
                    }
                }
                catch (err) {
                    pass = false;
                    //console.log('Missing node.storage_devices[1].size in '+node.uid);
                }
            }

            if (!_.isEmpty($scope.filter.selectedCpus)) {
                var selectedCpus = [];
                for (var key in $scope.filter.selectedCpus) {
                    if ($scope.filter.selectedCpus[key] == true) {
                        selectedCpus.push(key);
                    }
                }

                try {

                    if (typeof node.architecture.smp_size == undefined || !node.architecture.smp_size) {

                        if (selectedCpus.length !== 0 && !_.contains(selectedCpus, 'unknown')) {
                            pass = false;
                        }
                    }
                    else {
                        if (selectedCpus.length !== 0 && !_.contains(selectedCpus, node.architecture.smp_size.toString())) {
                            pass = false;
                        }
                    }
                }
                catch (err) {
                    pass = false;
                    //console.log('Missing node.architecture.smp_size in '+node.uid);
                }
            }

            if (!_.isEmpty($scope.filter.selectedCores)) {
                var selectedCores = [];
                for (var key in $scope.filter.selectedCores) {
                    if ($scope.filter.selectedCores[key] == true) {
                        selectedCores.push(key);
                    }
                }

                try {
                    if (typeof node.architecture.smt_size == undefined || !node.architecture.smt_size) {

                        if (selectedCores.length !== 0 && !_.contains(selectedCores, 'unknown')) {
                            pass = false;
                        }
                    }
                    else {
                        if (selectedCores.length !== 0 && !_.contains(selectedCores, node.architecture.smt_size.toString())) {
                            pass = false;
                        }
                    }
                }
                catch (err) {
                    pass = false;
                    //console.log('Missing node.architecture.smp_size in '+node.uid);
                }
            }

            if (!_.isEmpty($scope.filter.selectedRams)) {
                var selectedRams = [];
                for (var key in $scope.filter.selectedRams) {
                    if ($scope.filter.selectedRams[key] == true) {
                        selectedRams.push(key);
                    }
                }

                try {

                    if (typeof node.architecture.smt_size == undefined || !node.main_memory.ram_size) {

                        if (selectedRams.length !== 0 && !_.contains(selectedRams, 'unknown')) {
                            pass = false;
                        }
                    }
                    else {
                        var ramSize = Math.round(node.main_memory.ram_size / (1024 * 1024)).toString();
                        if (selectedRams.length !== 0 && !_.contains(selectedRams, ramSize)) {
                            pass = false;
                        }
                    }

                }
                catch (err) {
                    pass = false;
                    //console.log('Missing node.main_memory.ram_size in '+node.uid);
                }
            }

            if (!_.isEmpty($scope.filter.selectedClockSpeed)) {
                var selectedClockSpeed = [];
                for (var key in $scope.filter.selectedClockSpeed) {
                    if ($scope.filter.selectedClockSpeed[key] == true) {
                        selectedClockSpeed.push(key);
                    }
                }
                try {

                    if (typeof node.processor.clock_speed == undefined || !node.processor.clock_speed) {

                        if (selectedClockSpeed.length !== 0 && !_.contains(selectedClockSpeed, 'unknown')) {
                            pass = false;
                        }
                    }
                    else {
                        var clockSpeed = (node.processor.clock_speed / (1000000000).toFixed(2)).toString();
                        if (selectedClockSpeed.length !== 0 && !_.contains(selectedClockSpeed, clockSpeed)) {
                            pass = false;
                        }
                    }
                }
                catch (err) {
                    pass = false;
                    //console.log('Missing node.processor.clock_speed in '+node.uid);
                }
            }

            if (!_.isEmpty($scope.filter.selectedProcessorModels)) {
                var selectedProcessorModels = [];
                for (var key in $scope.filter.selectedProcessorModels) {
                    if ($scope.filter.selectedProcessorModels[key] == true) {
                        selectedProcessorModels.push(key.toLowerCase());
                    }
                }
                try {
                    if (typeof node.processor.model == undefined || !node.processor.model) {

                        if (selectedProcessorModels.length !== 0 && !_.contains(selectedProcessorModels, 'unknown')) {
                            pass = false;
                        }
                    }
                    else {
                        if (selectedProcessorModels.length !== 0 && !_.contains(selectedProcessorModels, node.processor.model.toLowerCase())) {
                            pass = false;
                        }
                    }
                }
                catch (err) {
                    pass = false;
                    //console.log('Missing node.processor.model in '+node.uid);
                }
            }

            if (!_.isEmpty($scope.filter.selectedCachel1d)) {
                var selectedCachel1d = [];
                for (var key in $scope.filter.selectedCachel1d) {
                    if ($scope.filter.selectedCachel1d[key] == true) {
                        selectedCachel1d.push(key);
                    }
                }
                try {
                    if (typeof node.processor.cache_l1d == undefined || !node.processor.cache_l1d) {

                        if (selectedCachel1d.length !== 0 && !_.contains(selectedCachel1d, 'unknown')) {
                            pass = false;
                        }
                    }
                    else {
                        if (selectedCachel1d.length !== 0 && !_.contains(selectedCachel1d, Math.round(node.processor.cache_l1d / 1024).toString())) {
                            pass = false;
                        }
                    }
                }
                catch (err) {
                    pass = false;
                    //console.log('Missing node.processor.cache_l1d in '+node.uid);
                }
            }

            if (!_.isEmpty($scope.filter.selectedCachel1i)) {
                var selectedCachel1i = [];
                for (var key in $scope.filter.selectedCachel1i) {
                    if ($scope.filter.selectedCachel1i[key] == true) {
                        selectedCachel1i.push(key);
                    }
                }
                try {
                    if (typeof node.processor.cache_l1i == undefined || !node.processor.cache_l1i) {

                        if (selectedCachel1i.length !== 0 && !_.contains(selectedCachel1i, 'unknown')) {
                            pass = false;
                        }
                    }
                    else {
                        if (selectedCachel1i.length !== 0 && !_.contains(selectedCachel1i, Math.round(node.processor.cache_l1i / 1024).toString())) {
                            pass = false;
                        }
                    }
                }
                catch (err) {
                    pass = false;
                    //console.log('Missing node.processor.cache_l1i in '+node.uid);
                }
            }

            if (!_.isEmpty($scope.filter.selectedCachel1)) {
                var selectedCachel1 = [];
                for (var key in $scope.filter.selectedCachel1) {
                    if ($scope.filter.selectedCachel1[key] == true) {
                        selectedCachel1.push(key);
                    }
                }
                try {
                    if (typeof node.processor.cache_l1 == undefined || !node.processor.cache_l1) {

                        if (selectedCachel1.length !== 0 && !_.contains(selectedCachel1, 'unknown')) {
                            pass = false;
                        }
                    }
                    else {
                        if (selectedCachel1.length !== 0 && !_.contains(selectedCachel1, Math.round(node.processor.cache_l1 / 1024).toString())) {
                            pass = false;
                        }
                    }
                }
                catch (err) {
                    pass = false;
                    //console.log('Missing node.processor.cache_l1 in '+node.uid);
                }
            }

            if (!_.isEmpty($scope.filter.selectedCachel2)) {
                var selectedCachel2 = [];
                for (var key in $scope.filter.selectedCachel2) {
                    if ($scope.filter.selectedCachel2[key] == true) {
                        selectedCachel2.push(key);
                    }
                }
                try {
                    if (typeof node.processor.cache_l2 == undefined || !node.processor.cache_l2) {

                        if (selectedCachel2.length !== 0 && !_.contains(selectedCachel2, 'unknown')) {
                            pass = false;
                        }
                    }
                    else {
                        if (selectedCachel2.length !== 0 && !_.contains(selectedCachel2, Math.round(node.processor.cache_l2 / 1024).toString())) {
                            pass = false;
                        }
                    }
                }
                catch (err) {
                    pass = false;
                    //console.log('Missing node.processor.cache_l2 in '+node.uid);
                }
            }

            if (!_.isEmpty($scope.filter.selectedCachel3)) {
                var selectedCachel3 = [];
                for (var key in $scope.filter.selectedCachel3) {
                    if ($scope.filter.selectedCachel3[key] == true) {
                        selectedCachel3.push(key);
                    }
                }
                try {
                   if (typeof node.processor.cache_l3 == undefined || !node.processor.cache_l3) {

                        if (selectedCachel3.length !== 0 && !_.contains(selectedCachel3, 'unknown')) {
                            pass = false;
                        }
                    }
                    else {
                        if (selectedCachel3.length !== 0 && !_.contains(selectedCachel3, Math.round(node.processor.cache_l3 / 1024).toString())) {
                            pass = false;
                        }
                    }
                }
                catch (err) {
                    pass = false;
                    //console.log('Missing node.processor.cache_l3 in '+node.uid);
                }
            }
            return pass;
        }

        $scope.applyFilter = function (isFirstTimeOnly, updateNodeCount, noResetFilter) {

            $scope.selectednodes = _.filter($scope.allnodes, function (node) {
                var pass = false;
                if (_.isEmpty($scope.filter.selectedSitesClusters)) {
                    //no filters applied, returning all
                    //check other filters
                    pass = $scope.applyOtherFilters(node);
                }
                else {
                    for (var site in $scope.filter.selectedSitesClusters) {
                        if (site === node.site) {
                            if (!$scope.filter.selectedSitesClusters[site]
                                || $scope.filter.selectedSitesClusters[site].length === 0) {
                                //check other filters
                                pass = $scope.applyOtherFilters(node);
                            }
                            else {
                                if (_.contains($scope.filter.selectedSitesClusters[site], node.cluster)) {
                                    //check other fiters
                                    pass = $scope.applyOtherFilters(node);
                                }
                            }
                        }
                    }
                }

                return pass;
            });

            if (updateNodeCount) {
                $scope.suggestednodes = _.filter($scope.allnodes, function (node) {
                    return $scope.applyOtherFilters(node);
                });
            }
            console.log('filter', $scope.filter);
            $scope.init_var(noResetFilter);
            _.each($scope.selectednodes, function (node) {
                $scope.processNode(node, isFirstTimeOnly, noResetFilter);
            });
        }
        $scope.applySiteFilter = function (site_uid) {

            if ($scope.filter.selectedSites.hasOwnProperty(site_uid)) {

                var siteObj = _.find($scope.sites, function (s) {
                    return s.name.toLowerCase() === site_uid.toLowerCase();
                });

                if ($scope.filter.selectedSites[site_uid] === true) {
                    site_uid = site_uid.toLowerCase();
                    $scope.filter.selectedSitesClusters[site_uid] = [];

                    _.each(siteObj.clusters, function (cluster, index) {
                        $scope.filter.selectedSitesClusters[site_uid][index] = cluster.uid.toLowerCase();
                        $scope.filter.selectedClusters[cluster.uid.toLowerCase()] = true;
                    });
                }
                else if ($scope.filter.selectedSites[site_uid] === false) {
                    delete $scope.filter.selectedSites[site_uid]
                    site_uid = site_uid.toLowerCase();
                    delete $scope.filter.selectedSitesClusters[site_uid];
                    _.each(siteObj.clusters, function (cluster) {
                        delete $scope.filter.selectedClusters[cluster.uid.toLowerCase()];
                    });
                }
            }
            $scope.applyFilter();
        };

        $scope.applyClusterFilter = function (site_uid, cluster_uid) {
            var siteObj = _.find($scope.sites, function (s) {
                return s.name.toLowerCase() === site_uid.toLowerCase();
            });
            if ($scope.filter.selectedClusters[cluster_uid] === true) {
                //add
                $scope.filter.selectedSitesClusters[site_uid.toLowerCase()]
                    = _.union($scope.filter.selectedSitesClusters[site_uid.toLowerCase()], [cluster_uid]);
                if (!$scope.filter.selectedSites[site_uid]) {
                    $scope.filter.selectedSites[site_uid] = true;
                }

            }
            else if ($scope.filter.selectedClusters[cluster_uid] === false) {
                //remove
                delete $scope.filter.selectedClusters[cluster_uid];
                $scope.filter.selectedSitesClusters[site_uid.toLowerCase()]
                    = _.without($scope.filter.selectedSitesClusters[site_uid.toLowerCase()], cluster_uid);
                if ($scope.filter.selectedSitesClusters[site_uid.toLowerCase()].length == 0) {
                    delete $scope.filter.selectedSitesClusters[site_uid.toLowerCase()];
                    delete $scope.filter.selectedSites[site_uid];

                }
            }
            $scope.applyFilter();
        }
        $scope.resetNodeCounts = function () {
            _.each($scope.filteredSites, function (site) {
                delete site.node_count;
                _.each(site.clusters, function (cluster) {
                    delete cluster.node_count;
                });
            });
        }

        $scope.recountSiteCluster = function () {
            $scope.resetNodeCounts();
            var sitesCopy = angular.copy($scope.sites);
            $scope.filteredSites = [];
            _.each($scope.suggestednodes, function (node) {
                var siteObj = _.find(sitesCopy, function (s) {
                    return s.uid.toLowerCase() === node.site;
                });

                if (!_.contains($scope.filteredSites, siteObj)) {
                    delete siteObj.node_count;
                    _.each(siteObj.clusters, function (cluster) {
                        delete cluster.node_count;
                    });
                    $scope.filteredSites.push(siteObj);
                }

                if (!siteObj.node_count) {
                    siteObj.node_count = 1;
                }
                else {
                    siteObj.node_count++;
                }

                var clusterObj = _.find(siteObj.clusters, function (c) {
                    return c.uid.toLowerCase() === node.cluster;
                });

                if (!clusterObj.node_count) {
                    clusterObj.node_count = 1;
                }
                else {
                    clusterObj.node_count++;
                }

            });
        }

        $scope.preApplyOtherFilters = function (noResetFilter) {
            var updateNodeCount = true;
            var isFirstTimeOnly = false;
            $scope.applyFilter(isFirstTimeOnly, updateNodeCount, noResetFilter);
            $scope.recountSiteCluster();
        }

        //Step I: Fetch sites
        var promises = [];
        var promise_sites = $http({method: 'GET', url: 'sites.json', cache: 'true'})
            .then(function (response) {
                $scope.sites = response.data.items;
                //initially make all selected
                $scope.filteredSites = angular.copy($scope.sites);

                _.each($scope.sites, function (site, parentIndex) {
                    var links = site.links;
                    cluster_link = _.findWhere(links, {rel: 'clusters'});

                    if (cluster_link) {
                        cluster_link_href = (cluster_link.href.substring(1)) + '.json';

                        //Step II: Fetch Clusters
                        var promise_clusters = $http({method: 'GET', url: cluster_link_href, cache: 'true'})
                            .then(function (response) {
                                site.clusters = response.data.items;
                                var filtered_site = _.findWhere($scope.filteredSites, {uid: site.uid});
                                filtered_site.clusters = angular.copy(site.clusters);

                                _.each(site.clusters, function (cluster, index) {
                                    var links = cluster.links
                                    node_link = _.findWhere(links, {rel: 'nodes'});
                                    nodes_link_href = (node_link.href.substring(1)) + '.json';
                                    //Step III: Fetch Nodes
                                    var promise_nodes = $http({method: 'GET', url: nodes_link_href, cache: 'true'})
                                        .then(function (response) {
                                            if ((parentIndex == $scope.sites.length - 1) && (index == site.clusters.length - 1)) {
                                                checkIfAllResolved();
                                            }
                                            $scope.nodes = response.data.items;
                                            _.each($scope.nodes, function (node) {
                                                var isFirstTimeOnly = true;
                                                $scope.processNode(node, isFirstTimeOnly);
                                                $scope.allnodes.push(node);
                                            });
                                        },
                                        function (error) {
                                            console.log('There was an error fetching nodes. ' + error);
                                            $scope.loadingError = true;
                                            $scope.loading = false;
                                        });
                                    promises.push(promise_nodes);
                                });
                            },
                            function (error) {
                                console.log('There was an error fetching clusters. ' + error);
                                $scope.loadingError = true;
                                $scope.loading = false;
                            });

                        promises.push(promise_clusters);
                    }
                    else {
                        console.log('cluster link is missing.');
                        $scope.loadingError = true;
                        $scope.loading = false;
                    }
                });
            },
            function (error) {
                console.log('There was an error fetching sites. ' + error);
                $scope.loadingError = true;
                $scope.loading = false;
            });

        promises.push(promise_sites);

        var checkIfAllResolved = function () {
            $q.all(promises).then(function () {
                    console.log('Inside $q success');
                    $scope.loading = false;
                    //save the map backup when all counting is probably done.
                    $scope.mapOrg = angular.copy($scope.map);
                },
                function (error) {
                    console.log('Inside $q failure');
                    $scope.loading = false;
                });
            return true;
        }
    }]);