/**
 * Created by agauli on 2/26/15.
 */
angular.module('discoveryApp')
.controller('AppController', ['$scope', '$http', '_', function($scope, $http, _) {
        $scope.selectednodes = $scope.allnodes  = [];
        $scope.loading = true;
        $scope.init_var = function() {
            $scope.virtual_support = {};
            $scope.best_effort_support = {};
            $scope.deploy_support = {};
            $scope.net_adap_inf_1 = {};
            $scope.net_adap_inf_2 = {};
            $scope.net_adap_inf_3 = {};
            $scope.storage_dev_inf = {};
            $scope.storage_dev_size = {};
            $scope.cpus = {};
            $scope.cores = {};
            $scope.rams = {};
            $scope.clocks = {};
            $scope.processor_models = {};
            $scope.cache_l1d = {};
            $scope.cache_l1i = {};
            $scope.cache_l1 = {};
            $scope.cache_l2 = {};
        }
        $scope.init_var();

        $scope.resetFilters = function(){
            $scope.filter = {
            selectedSites : {},
            selectedClusters : {},
            selectedSitesClusters : {},
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
            selectedCachel11: {},
            selectedCachel12: {}
        };
             $scope.selectednodes = $scope.allnodes;
        }
        $scope.resetFilters();

        $scope.processNode = function(node, updateNodeCount){

            try {
                var storage_interface = node.storage_devices[0].interface;
                if (!$scope.storage_dev_inf.hasOwnProperty(storage_interface)) {
                    $scope.storage_dev_inf[storage_interface] = {count: 1};
                }
                else {
                    $scope.storage_dev_inf[storage_interface].count = $scope.storage_dev_inf[storage_interface].count + 1;
                }
            }
            catch(err){
               //pass
            }

            var storage_size = node.storage_devices[0].size;
            storage_size = Math.round(storage_size/(1024*1024*1024));
                if (! $scope.storage_dev_size.hasOwnProperty(storage_size)){
                    $scope.storage_dev_size[storage_size] = {count:1};
                }
            else{
                    $scope.storage_dev_size[storage_size].count = $scope.storage_dev_size[storage_size].count+1;
                }

            try{
                    var net_adap = node.network_adapters[0].interface;
                    if (! $scope.net_adap_inf_1.hasOwnProperty(net_adap)){
                    $scope.net_adap_inf_1[net_adap] = {count:1};
                    }
                   else{
                    $scope.net_adap_inf_1[net_adap].count = $scope.net_adap_inf_1[net_adap].count+1;
                    }
                }
            catch(err){
                    //pass
               }

            try{
                    var net_adap = node.network_adapters[1].interface;
                    if (! $scope.net_adap_inf_2.hasOwnProperty(net_adap)){
                    $scope.net_adap_inf_2[net_adap] = {count:1};
                    }
                   else{
                    $scope.net_adap_inf_2[net_adap].count = $scope.net_adap_inf_2[net_adap].count+1;
                    }
                }
            catch(err){
                    //pass
               }

            try{
                    var net_adap = node.network_adapters[2].interface;
                    if (! $scope.net_adap_inf_3.hasOwnProperty(net_adap)){
                    $scope.net_adap_inf_3[net_adap] = {count:1};
                    }
                   else{
                    $scope.net_adap_inf_3[net_adap].count = $scope.net_adap_inf_3[net_adap].count+1;
                    }
                }
            catch(err){
                    //pass
               }

            try {
                var cpu = node.architecture.smp_size;
                if (!$scope.cpus.hasOwnProperty(cpu)) {
                    $scope.cpus[cpu] = {count: 1};
                }
                else {
                    $scope.cpus[cpu].count = $scope.cpus[cpu].count + 1;
                }
            }
            catch(err){
               //pass
            }

            try {
                var core = node.architecture.smt_size;
                if (!$scope.cores.hasOwnProperty(core)) {
                    $scope.cores[core] = {count: 1};
                }
                else {
                    $scope.cores[core].count = $scope.cores[core].count + 1;
                }
            }
            catch(err){
               //pass
            }

            try {
                var ram = Math.round(node.main_memory.ram_size/(1024*1024));

                if (!$scope.rams.hasOwnProperty(ram)) {
                    $scope.rams[ram] = {count: 1};
                }
                else {
                    $scope.rams[ram].count = $scope.rams[ram].count + 1;
                }
            }
            catch(err){
               //pass
            }

            try {
                var clock = node.processor.clock_speed/(1000000000).toFixed(2);

                if (!$scope.clocks.hasOwnProperty(clock)) {
                    $scope.clocks[clock] = {count: 1};
                }
                else {
                    $scope.clocks[clock].count = $scope.clocks[clock].count + 1;
                }
            }
            catch(err){
               //pass
            }

            try {
                var processor_model =node.processor.model;

                if (!$scope.processor_models.hasOwnProperty(processor_model)) {
                    $scope.processor_models[processor_model] = {count: 1};
                }
                else {
                    $scope.processor_models[processor_model].count = $scope.processor_models[processor_model].count + 1;
                }
            }
            catch(err){
               //pass
            }

             try {
                var cache =node.processor.cache_l1;
                 if(cache){
                     cache = Math.round(cache/1000);
                 }

                if (!$scope.cache_l1.hasOwnProperty(cache)) {
                    $scope.cache_l1[cache] = {count: 1};
                }
                else {
                    $scope.cache_l1[cache].count = $scope.cache_l1[cache].count + 1;
                }
            }
            catch(err){
               //pass
            }

            try {
                var cache =node.processor.cache_l2;
                if(cache){
                     cache = Math.round(cache/1000);
                 }
                if (!$scope.cache_l2.hasOwnProperty(cache)) {
                    $scope.cache_l2[cache] = {count: 1};
                }
                else {
                    $scope.cache_l2[cache].count = $scope.cache_l2[cache].count + 1;
                }
            }
            catch(err){
               //pass
            }

            try {
                var cache =node.processor.cache_l1d;
                if(cache){
                     cache = Math.round(cache/1000);
                 }
                if (!$scope.cache_l1d.hasOwnProperty(cache)) {
                    $scope.cache_l1d[cache] = {count: 1};
                }
                else {
                    $scope.cache_l1d[cache].count = $scope.cache_l1d[cache].count + 1;
                }
            }
            catch(err){
               //pass
            }

            try {
                var cache =node.processor.cache_l1i;
                if(cache){
                     cache = Math.round(cache/1000);
                 }
                if (!$scope.cache_l1i.hasOwnProperty(cache)) {
                    $scope.cache_l1i[cache] = {count: 1};
                }
                else {
                    $scope.cache_l1i[cache].count = $scope.cache_l1i[cache].count + 1;
                }
            }
            catch(err){
               //pass
            }
            if(updateNodeCount) {
                try {
                    var link = node.links[0].href;
                    if (link) {
                        var site_index = link.indexOf('/sites/');
                        var cluster_index = link.indexOf('/clusters/');
                        var node_index = link.indexOf('/nodes/');
                        var site = link.substring(site_index + 7, cluster_index);
                        node.site = site;
                        var cluster = '';

                        if (node_index !== -1) {
                            cluster = link.substring(cluster_index + 10, node_index);
                        }
                        else {
                            cluster = link.substring(cluster_index + 10);
                        }
                        node.cluster = cluster;

                        var siteObj = _.find($scope.filtered_sites, function (s) {
                            return s.name.toLowerCase() === site.toLowerCase();
                        });

                        if (!siteObj.node_count) {
                            siteObj.node_count = 1;
                        }
                        else {
                            siteObj.node_count++;
                        }

                        var clusterObj = _.find(siteObj.clusters, function (c) {
                            return c.uid.toLowerCase() === cluster.toLowerCase()
                        });
                        if (!clusterObj.node_count) {
                            clusterObj.node_count = 1;
                        }
                        else {
                            clusterObj.node_count++;
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

             if(!_.isEmpty($scope.filter.selectedNetAdap1)){
                 var selectedNetAdap1 = [];
                 for(var key in $scope.filter.selectedNetAdap1){
                     if($scope.filter.selectedNetAdap1[key] == true){
                         selectedNetAdap1.push(key.toLowerCase());
                     }
                 }
                 try{

                 if(!_.contains(selectedNetAdap1, node.network_adapters[0].interface.toLowerCase())){
                     pass = false;
                 }
                 }
                 catch(err){
                     pass = false;
                     //console.log('Missing node.network_adapters[0] in '+node.uid);
                 }

             }
           return pass;
        }

        $scope.applyFilter = function(updateNodeCount){

            $scope.selectednodes = _.filter($scope.allnodes,function(node){
               var pass = false;
               if(_.isEmpty($scope.filter.selectedSitesClusters)){
                  //no filters applied, returning all
                   //check other filters
                   pass = $scope.applyOtherFilters(node);
               }
                else{
                   for(var site in $scope.filter.selectedSitesClusters){
                       if(site === node.site){
                          if(!$scope.filter.selectedSitesClusters[site]
                              || $scope.filter.selectedSitesClusters[site].length === 0){
                              //check other filters
                              pass = $scope.applyOtherFilters(node);
                          }
                           else{
                               if(_.contains($scope.filter.selectedSitesClusters[site], node.cluster)){
                                    //check other fiters
                                   pass = $scope.applyOtherFilters(node);
                               }
                          }
                       }
                   }
               }
                return pass;

            });
            console.log('filter',$scope.filter);
            console.log('sites',$scope.filter.selectedSites);
            console.log('clusters',$scope.filter.selectedClusters);
            console.log('site cluster',$scope.filter.selectedSitesClusters);
            $scope.init_var();
            _.each($scope.selectednodes, function(node){
                $scope.processNode(node, updateNodeCount);
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
            var updateNodeCount = false;
            $scope.applyFilter(updateNodeCount);
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
            var updateNodeCount = false;
            $scope.applyFilter(updateNodeCount);
        }

        $scope.preApplyOtherFilters = function(){
            var updateNodeCount = false;
            $scope.applyFilter(updateNodeCount);
        }

        var totalClusters = 0;
        var iterationCount = 0;
        //Step I: Fetch sites
        $http.get('sites.json')
            .success(function(data, status){
                $scope.sites = data.items;
                //initially make all selected
                $scope.filtered_sites = angular.copy($scope.sites);
                _.each($scope.sites, function(site, parentIndex){
                    var links = site.links;
                    cluster_link = _.findWhere(links,{rel:'clusters'});
                    if (cluster_link){
                        cluster_link_href = (cluster_link.href.substring(1))+'.json';
                        //Step II: Fetch Clusters
                        $http.get(cluster_link_href)
                            .success(function(data, status){
                                site.clusters = data.items;
                                totalClusters += site.clusters.length;
                                var filtered_site = _.findWhere($scope.filtered_sites,{uid:site.uid});
                                filtered_site.clusters = site.clusters;
                                _.each(site.clusters, function(cluster, index){
                                    //console.log('Cluster: ',cluster);
                                    var links = cluster.links
                                    node_link = _.findWhere(links,{rel:'nodes'});
                                    nodes_link_href = (node_link.href.substring(1))+'.json';
                                    //Step III: Fetch Nodes
                                    $http.get(nodes_link_href)
                                        .success(function(data, status){
                                            iterationCount++;
                                            $scope.nodes = data.items;
                                            //console.log('Nodes: ', $scope.nodes);
                                            _.each($scope.nodes, function(node){
                                                var updateNodeCount = true;
                                                $scope.processNode(node, updateNodeCount);
                                                $scope.allnodes.push(node);
                                            });
                                            //display UI when all nodes are collected
                                            if(totalClusters == iterationCount){
                                                $scope.loading = false;
                                            }
                                        })
                                        .error(function(data, status){
                                            console.log('There was an error fetching nodes.');
                                        })
                                });
                            })
                            .error(function(data, status){
                               console.log('There was an error fetching clusters.');
                            })
                    }
                });
            })
            .error(function(data,status){
                console.log('There was an error fetching sites.');
            })
}]);