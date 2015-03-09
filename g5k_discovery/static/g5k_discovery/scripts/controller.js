/**
 * Created by agauli on 2/26/15.
 */
angular.module('discoveryApp')
.controller('AppController', ['$scope', '$http', '_', '$q', '$timeout', function($scope, $http, _, $q, $timeout) {
        $scope.selectednodes = $scope.allnodes  = [];
        $scope.loading = true;
        $scope.loadingError = false;
        $scope.nodeStringMap = {};
        $scope.map = {};
        //keeps the node count for each filter
        $scope.init_var = function(noResetFilter) {

            if(!noResetFilter || noResetFilter !== 'sites_nodecount'){
                $scope.map.sites_nodecount = {};
            }
            if(!noResetFilter || noResetFilter !== 'clusters_nodecount'){
                $scope.map.clusters_nodecount = {};
            }
            if(!noResetFilter || noResetFilter !== 'virtual_support'){
                $scope.map.virtual_support = {};
            }
            if(!noResetFilter || noResetFilter !== 'virtual_support'){
                $scope.map.virtual_support = {};
            }
            if(!noResetFilter || noResetFilter !== 'best_effort_support'){
               $scope.map.best_effort_support = {};
            }
            if(!noResetFilter || noResetFilter !== 'deploy_support'){
                $scope.map.deploy_support = {};
            }
            if(!noResetFilter || noResetFilter !== 'net_adap_inf_1'){
               $scope.map.net_adap_inf_1 = {};
            }
            if(!noResetFilter || noResetFilter !== 'net_adap_inf_2'){
               $scope.map.net_adap_inf_2 = {};
            }
            if(!noResetFilter || noResetFilter !== 'net_adap_inf_3'){
               $scope.map.net_adap_inf_3 = {};
            }
            if(!noResetFilter || noResetFilter !== 'storage_dev_inf'){
               $scope.map.storage_dev_inf = {};
            }
            if(!noResetFilter || noResetFilter !== 'storage_dev_size'){
               $scope.map.storage_dev_size = {};
            }
            if(!noResetFilter || noResetFilter !== 'cpus'){
               $scope.map.cpus = {};
            }
             if(!noResetFilter || noResetFilter !== 'cores'){
               $scope.map.cores = {};
            }
             if(!noResetFilter || noResetFilter !== 'rams'){
               $scope.map.rams = {};
            }
             if(!noResetFilter || noResetFilter !== 'clocks'){
               $scope.map.clocks = {};
            }
            if(!noResetFilter || noResetFilter !== 'processor_models'){
               $scope.map.processor_models = {};
            }
            if(!noResetFilter || noResetFilter !== 'cache_l1d'){
               $scope.map.cache_l1d = {};
            }
            if(!noResetFilter || noResetFilter !== 'cache_l1i'){
               $scope.map.cache_l1i = {};
            }
            if(!noResetFilter || noResetFilter !== 'cache_l1'){
               $scope.map.cache_l1 = {};
            }
            if(!noResetFilter || noResetFilter !== 'cache_l2'){
               $scope.map.cache_l2 = {};
            }
        }
        $scope.init_var();

        $scope.resetFilters = function(){
            $scope.filter = {
            selectedSites : {},
            selectedClusters : {},
            selectedSitesClusters : {},
            search : '',
            hasVirtualSupport : undefined,
            hasBestEffortSupport: undefined,
            hasDeploySupport: undefined,
            selectedNetAdap1: {},
            selectedNetAdap2: {},
            selectedNetAdap3: {},
            selectedStorageDevInf: {},
            selectedStorageDevSize: {},
            selectedCpus: {},
            selectedCores: {},
            selectedRams: {},
            selectedClockSpeed: {},
            selectedProcessorModels: {},
            selectedCachel1d: {},
            selectedCachel1i: {},
            selectedCachel1: {},
            selectedCachel2: {}
        };
            $scope.selectednodes = $scope.allnodes;
            $scope.filteredSites = $scope.sites;
        }
        $scope.resetFilters();

        $scope.resetUI = function(){
            $scope.resetFilters();
            $scope.map = angular.copy($scope.mapOrg);
        }

        var searchTimeout = null;
        $scope.search = function(){
        if (searchTimeout) {
            $timeout.cancel(searchTimeout);
        }
        searchTimeout = $timeout(function() {
            $scope.preApplyOtherFilters();
        }, 500); // delay 250 ms

        }
        $scope.processNode = function(node, isFirstTimeOnly, noResetFilter){

            if(!noResetFilter || noResetFilter !== 'storage_dev_inf') {
                try {
                    var storage_interface = node.storage_devices[0].interface;
                    if (!$scope.map.storage_dev_inf.hasOwnProperty(storage_interface)) {
                        $scope.map.storage_dev_inf[storage_interface] = {count: 1};
                    }
                    else {
                        $scope.map.storage_dev_inf[storage_interface].count = $scope.map.storage_dev_inf[storage_interface].count + 1;
                    }
                }
                catch (err) {
                    //pass
                }
            }

           if(!noResetFilter || noResetFilter !== 'storage_dev_size') {
               try {
                   var storage_size = node.storage_devices[0].size;
                   storage_size = Math.round(storage_size / (1024 * 1024 * 1024));
                   if (!$scope.map.storage_dev_size.hasOwnProperty(storage_size)) {
                       $scope.map.storage_dev_size[storage_size] = {count: 1};
                   }
                   else {
                       $scope.map.storage_dev_size[storage_size].count = $scope.map.storage_dev_size[storage_size].count + 1;
                   }
               }
               catch (err) {
                    //pass
                }
           }

             if(!noResetFilter || noResetFilter !== 'net_adap_inf_1') {
                 try {
                     var net_adap = node.network_adapters[0].interface;
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
           if(!noResetFilter || noResetFilter !== 'net_adap_inf_2') {
               try {
                   var net_adap = node.network_adapters[1].interface;
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
            if(!noResetFilter || noResetFilter !== 'net_adap_inf_3') {
                try {
                    var net_adap = node.network_adapters[2].interface;
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

            if(!noResetFilter || noResetFilter !== 'cpus') {
                try {
                    var cpu = node.architecture.smp_size;
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

            if(!noResetFilter || noResetFilter !== 'cores') {
                try {
                    var core = node.architecture.smt_size;
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

            if(!noResetFilter || noResetFilter !== 'rams') {
                try {
                    var ram = Math.round(node.main_memory.ram_size / (1024 * 1024));

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

            if(!noResetFilter || noResetFilter !== 'clocks') {
                try {
                    var clock = node.processor.clock_speed / (1000000000).toFixed(2);

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

            if(!noResetFilter || noResetFilter !== 'processor_models') {
                try {
                    var processor_model = node.processor.model;

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

            if(!noResetFilter || noResetFilter !== 'cache_l1') {
                try {
                    var cache = node.processor.cache_l1;
                    if (cache) {
                        cache = Math.round(cache / 1000);
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

            if(!noResetFilter || noResetFilter !== 'cache_l2') {
                try {
                    var cache = node.processor.cache_l2;
                    if (cache) {
                        cache = Math.round(cache / 1000);
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

            if(!noResetFilter || noResetFilter !== 'cache_l1d') {
                try {
                    var cache = node.processor.cache_l1d;
                    if (cache) {
                        cache = Math.round(cache / 1000);
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

            if(!noResetFilter || noResetFilter !== 'cache_l1i') {
                try {
                    var cache = node.processor.cache_l1i;
                    if (cache) {
                        cache = Math.round(cache / 1000);
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
            if(isFirstTimeOnly) {

                $scope.nodeStringMap[node.uid] = JSON.stringify(node);
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

         $scope.applyOtherFilters = function(node){
            var pass = true;
             if($scope.filter.hasVirtualSupport !== node.hasVirtualSupport){
                 //pass = false;
             }
             if($scope.filter.hasBestEffortSupport !== node.hasBestEffortSupport){
                 //pass = false;
             }
             if($scope.filter.hasDeploySupport !== node.hasDeploySupport){
                 //pass = false;
             }

             var nodeString = $scope.nodeStringMap[node.uid];
             if(nodeString && nodeString.indexOf($scope.filter.search) < 0){
                pass = false;
             }

             if(!_.isEmpty($scope.filter.selectedNetAdap1)){
                 var selectedNetAdap1 = [];
                 for(var key in $scope.filter.selectedNetAdap1){
                     if($scope.filter.selectedNetAdap1[key] == true){
                         selectedNetAdap1.push(key.toLowerCase());
                     }
                 }
                 try{

                 if(selectedNetAdap1.length !==0 && !_.contains(selectedNetAdap1, node.network_adapters[0].interface.toLowerCase())){
                     pass = false;
                 }
                 }
                 catch(err){
                     pass = false;
                     //console.log('Missing node.network_adapters[0] in '+node.uid);
                 }
             }

             if(!_.isEmpty($scope.filter.selectedNetAdap2)){
                 var selectedNetAdap2 = [];
                 for(var key in $scope.filter.selectedNetAdap2){
                     if($scope.filter.selectedNetAdap2[key] == true){
                         selectedNetAdap2.push(key.toLowerCase());
                     }
                 }
                 try{

                 if(selectedNetAdap2.length !==0 && !_.contains(selectedNetAdap2, node.network_adapters[1].interface.toLowerCase())){
                     pass = false;
                 }
                 }
                 catch(err){
                     pass = false;
                     //console.log('Missing node.network_adapters[1] in '+node.uid);
                 }
             }

             if(!_.isEmpty($scope.filter.selectedNetAdap3)){
                 var selectedNetAdap3 = [];
                 for(var key in $scope.filter.selectedNetAdap3){
                     if($scope.filter.selectedNetAdap3[key] == true){
                         selectedNetAdap3.push(key.toLowerCase());
                     }
                 }
                 try{

                 if(selectedNetAdap3.length !==0 && !_.contains(selectedNetAdap3, node.network_adapters[2].interface.toLowerCase())){
                     pass = false;
                 }
                 }
                 catch(err){
                     pass = false;
                     //console.log('Missing node.network_adapters[2] in '+node.uid);
                 }
             }

             if(!_.isEmpty($scope.filter.selectedStorageDevInf)){
                 var selectedStorageDevInf = [];
                 for(var key in $scope.filter.selectedStorageDevInf){
                     if($scope.filter.selectedStorageDevInf[key] == true){
                         selectedStorageDevInf.push(key.toLowerCase());
                     }
                 }
                 try{

                 if(selectedStorageDevInf.length !==0 && !_.contains(selectedStorageDevInf, node.storage_devices[0].interface.toLowerCase())){
                     pass = false;
                 }
                 }
                 catch(err){
                     pass = false;
                     //console.log('Missing node.storage_devices[0].interface in '+node.uid);
                 }
             }

             if(!_.isEmpty($scope.filter.selectedStorageDevSize)){
                 var selectedStorageDevSize = [];
                 for(var key in $scope.filter.selectedStorageDevSize){
                     if($scope.filter.selectedStorageDevSize[key] == true){
                         selectedStorageDevSize.push(key);
                     }
                 }
                 try{
                 var storage_size = Math.round(node.storage_devices[0].size/ (1024 * 1024 * 1024));
                 if(selectedStorageDevSize.length !==0 && !_.contains(selectedStorageDevSize, storage_size.toString())){
                     pass = false;
                 }
                 }
                 catch(err){
                     pass = false;
                     //console.log('Missing node.storage_devices[0].size in '+node.uid);
                 }
             }

             if(!_.isEmpty($scope.filter.selectedCpus)){
                 var selectedCpus = [];
                 for(var key in $scope.filter.selectedCpus){
                     if($scope.filter.selectedCpus[key] == true){
                         selectedCpus.push(key);
                     }
                 }

                 try{

                 if(selectedCpus.length !==0 && !_.contains(selectedCpus, node.architecture.smp_size.toString())){
                     pass = false;
                 }
                 }
                 catch(err){
                     pass = false;
                     //console.log('Missing node.architecture.smp_size in '+node.uid);
                 }
             }

             if(!_.isEmpty($scope.filter.selectedCores)){
                 var selectedCores = [];
                 for(var key in $scope.filter.selectedCores){
                     if($scope.filter.selectedCores[key] == true){
                         selectedCores.push(key);
                     }
                 }

                 try{

                 if(selectedCores.length !==0 && !_.contains(selectedCores, node.architecture.smt_size.toString())){
                     pass = false;
                 }
                 }
                 catch(err){
                     pass = false;
                     //console.log('Missing node.architecture.smp_size in '+node.uid);
                 }
             }

             if(!_.isEmpty($scope.filter.selectedRams)){
                 var selectedRams = [];
                 for(var key in $scope.filter.selectedRams){
                     if($scope.filter.selectedRams[key] == true){
                         selectedRams.push(key);
                     }
                 }

                 try{

                 if(selectedRams.length !==0 && !_.contains(selectedRams, Math.round(node.main_memory.ram_size / (1024 * 1024)).toString())){
                     pass = false;
                 }
                 }
                 catch(err){
                     pass = false;
                     //console.log('Missing node.main_memory.ram_size in '+node.uid);
                 }
             }

             if(!_.isEmpty($scope.filter.selectedClockSpeed)){
                 var selectedClockSpeed = [];
                 for(var key in $scope.filter.selectedClockSpeed){
                     if($scope.filter.selectedClockSpeed[key] == true){
                         selectedClockSpeed.push(key);
                     }
                 }
                 try{

                 if(selectedClockSpeed.length !==0 && !_.contains(selectedClockSpeed, (node.processor.clock_speed / (1000000000).toFixed(2)).toString())){
                     pass = false;
                 }
                 }
                 catch(err){
                     pass = false;
                     //console.log('Missing node.processor.clock_speed in '+node.uid);
                 }
             }

             if(!_.isEmpty($scope.filter.selectedProcessorModels)){
                 var selectedProcessorModels = [];
                 for(var key in $scope.filter.selectedProcessorModels){
                     if($scope.filter.selectedProcessorModels[key] == true){
                         selectedProcessorModels.push(key.toLowerCase());
                     }
                 }
                 try{

                 if(selectedProcessorModels.length !==0 && !_.contains(selectedProcessorModels, node.processor.model.toLowerCase())){
                     pass = false;
                 }
                 }
                 catch(err){
                     pass = false;
                     //console.log('Missing node.processor.model in '+node.uid);
                 }
             }

             if(!_.isEmpty($scope.filter.selectedCachel1d)){
                 var selectedCachel1d = [];
                 for(var key in $scope.filter.selectedCachel1d){
                     if($scope.filter.selectedCachel1d[key] == true){
                         selectedCachel1d.push(key);
                     }
                 }
                 try{

                 if(selectedCachel1d.length !==0 && !_.contains(selectedCachel1d, Math.round(node.processor.cache_l1d / 1000).toString())){
                     pass = false;
                 }
                 }
                 catch(err){
                     pass = false;
                     //console.log('Missing node.processor.cache_l1d in '+node.uid);
                 }
             }

             if(!_.isEmpty($scope.filter.selectedCachel1i)){
                 var selectedCachel1i = [];
                 for(var key in $scope.filter.selectedCachel1i){
                     if($scope.filter.selectedCachel1i[key] == true){
                         selectedCachel1i.push(key);
                     }
                 }
                 try{

                 if(selectedCachel1i.length !==0 && !_.contains(selectedCachel1i, Math.round(node.processor.cache_l1i / 1000).toString())){
                     pass = false;
                 }
                 }
                 catch(err){
                     pass = false;
                     //console.log('Missing node.processor.cache_l1i in '+node.uid);
                 }
             }

             if(!_.isEmpty($scope.filter.selectedCachel1)){
                 var selectedCachel1 = [];
                 for(var key in $scope.filter.selectedCachel1){
                     if($scope.filter.selectedCachel1[key] == true){
                         selectedCachel1.push(key);
                     }
                 }
                 try{

                 if(selectedCachel1.length !==0 && !_.contains(selectedCachel1, Math.round(node.processor.cache_l1 / 1000).toString())){
                     pass = false;
                 }
                 }
                 catch(err){
                     pass = false;
                     //console.log('Missing node.processor.cache_l1 in '+node.uid);
                 }
             }

             if(!_.isEmpty($scope.filter.selectedCachel2)){
                 var selectedCachel2 = [];
                 for(var key in $scope.filter.selectedCachel2){
                     if($scope.filter.selectedCachel2[key] == true){
                         selectedCachel2.push(key);
                     }
                 }
                 try{

                 if(selectedCachel2.length !==0 && !_.contains(selectedCachel2, Math.round(node.processor.cache_l2 / 1000).toString())){
                     pass = false;
                 }
                 }
                 catch(err){
                     pass = false;
                     //console.log('Missing node.processor.cache_l2 in '+node.uid);
                 }
             }
           return pass;
        }

        $scope.applyFilter = function(isFirstTimeOnly, updateNodeCount, noResetFilter){

            $scope.selectednodes = _.filter($scope.allnodes,function(node) {
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

            if(updateNodeCount){
                $scope.suggestednodes = _.filter($scope.allnodes,function(node) {
                    return $scope.applyOtherFilters(node);
                });
            }
            console.log('filter',$scope.filter);
            $scope.init_var(noResetFilter);
            _.each($scope.selectednodes, function(node){
                $scope.processNode(node, isFirstTimeOnly, noResetFilter);
            });
        }
        $scope.applySiteFilter = function(site_uid){

                if ($scope.filter.selectedSites.hasOwnProperty(site_uid)) {

                    var siteObj = _.find($scope.sites, function(s){
                        return s.name.toLowerCase() === site_uid.toLowerCase();
                    });

                    if($scope.filter.selectedSites[site_uid] === true){
                        site_uid = site_uid.toLowerCase();
                        $scope.filter.selectedSitesClusters[site_uid]=[];

                        _.each(siteObj.clusters, function(cluster, index){
                            $scope.filter.selectedSitesClusters[site_uid][index]= cluster.uid.toLowerCase();
                            $scope.filter.selectedClusters[cluster.uid.toLowerCase()] = true;
                        });
                    }
                    else if($scope.filter.selectedSites[site_uid] === false){
                        delete $scope.filter.selectedSites[site_uid]
                         site_uid = site_uid.toLowerCase();
                        delete $scope.filter.selectedSitesClusters[site_uid];
                        _.each(siteObj.clusters, function(cluster){
                            delete $scope.filter.selectedClusters[cluster.uid.toLowerCase()];
                        });
                    }
                }
            $scope.applyFilter();
        };

        $scope.applyClusterFilter = function(site_uid, cluster_uid){
                    var siteObj = _.find($scope.sites, function(s){
                        return s.name.toLowerCase() === site_uid.toLowerCase();
                    });
                    if($scope.filter.selectedClusters[cluster_uid] === true){
                        //add
                        $scope.filter.selectedSitesClusters[site_uid.toLowerCase()]
                            = _.union($scope.filter.selectedSitesClusters[site_uid.toLowerCase()], [cluster_uid]);
                        if(!$scope.filter.selectedSites[site_uid]){
                            $scope.filter.selectedSites[site_uid] = true;
                        }

                    }
                    else if($scope.filter.selectedClusters[cluster_uid] === false){
                        //remove
                        delete $scope.filter.selectedClusters[cluster_uid];
                        $scope.filter.selectedSitesClusters[site_uid.toLowerCase()]
                            = _.without($scope.filter.selectedSitesClusters[site_uid.toLowerCase()], cluster_uid);
                        if($scope.filter.selectedSitesClusters[site_uid.toLowerCase()].length == 0){
                            delete $scope.filter.selectedSitesClusters[site_uid.toLowerCase()];
                            delete $scope.filter.selectedSites[site_uid];

                        }
                    }
            $scope.applyFilter();
        }
        $scope.resetNodeCounts = function(){
            _.each($scope.filteredSites, function(site){
                delete site.node_count;
                 _.each(site.clusters, function(cluster){
                     delete cluster.node_count;
                 });
            });
        }

        $scope.recountSiteCluster = function(){
            $scope.resetNodeCounts();
            var sitesCopy = angular.copy($scope.sites);
            $scope.filteredSites = [];
            _.each($scope.suggestednodes,function(node){
                var siteObj = _.find(sitesCopy, function (s) {
                            return s.uid.toLowerCase() === node.site;
                        });

                if(!_.contains($scope.filteredSites, siteObj)){
                    delete siteObj.node_count;
                    _.each(siteObj.clusters, function(cluster){
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

        $scope.preApplyOtherFilters = function(noResetFilter){
            var updateNodeCount = true;
            var isFirstTimeOnly = false;
            $scope.applyFilter(isFirstTimeOnly, updateNodeCount, noResetFilter);
            $scope.recountSiteCluster();
        }

        //Step I: Fetch sites
        var promises = [];
        var promise_sites = $http({method: 'GET', url: 'sites.json', cache: 'false'})
            .then(function(response){
                $scope.sites = response.data.items;
                //initially make all selected
                $scope.filteredSites = angular.copy($scope.sites);

                _.each($scope.sites, function(site, parentIndex){
                    var links = site.links;
                    cluster_link = _.findWhere(links,{rel:'clusters'});

                    if (cluster_link){
                        cluster_link_href = (cluster_link.href.substring(1))+'.json';

                        //Step II: Fetch Clusters
                        var promise_clusters = $http({method: 'GET', url: cluster_link_href, cache: 'false'})
                            .then(function(response){
                                site.clusters = response.data.items;
                                var filtered_site = _.findWhere($scope.filteredSites,{uid:site.uid});
                                filtered_site.clusters = angular.copy(site.clusters);

                                _.each(site.clusters, function(cluster, index){
                                    var links = cluster.links
                                    node_link = _.findWhere(links,{rel:'nodes'});
                                    nodes_link_href = (node_link.href.substring(1))+'.json';
                                    //Step III: Fetch Nodes
                                    var promise_nodes = $http({method: 'GET', url: nodes_link_href, cache: 'false'})
                                        .then(function(response){
                                            if((parentIndex == $scope.sites.length-1) && (index == site.clusters.length-1)){
                                              checkIfAllResolved();
                                            }
                                            $scope.nodes = response.data.items;
                                            _.each($scope.nodes, function(node){
                                                var isFirstTimeOnly = true;
                                                $scope.processNode(node, isFirstTimeOnly);
                                                $scope.allnodes.push(node);
                                            });

                                        },
                                        function(error){
                                            console.log('There was an error fetching nodes. '+error);
                                            $scope.loadingError = true;
                                            $scope.loading = false;
                                        });

                                    promises.push(promise_nodes);

                                });
                            },
                           function(error){
                               console.log('There was an error fetching clusters. '+error);
                                $scope.loadingError = true;
                                $scope.loading = false;
                            });

                        promises.push(promise_clusters);
                    }
                    else{
                        console.log('cluster link is missing.');
                        $scope.loadingError = true;
                        $scope.loading = false;
                    }
                });

            },
            function(error){
                console.log('There was an error fetching sites. '+ error);
                $scope.loadingError = true;
                $scope.loading = false;
            });

   promises.push(promise_sites);

   var checkIfAllResolved = function() {
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