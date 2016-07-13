/**
 * author agauli
 */
'use strict';
/*global Highcharts */

angular.module('usageApp')
    .controller('UsageController', ['$scope', '$http', '$timeout', '$q', '$location', '$filter', 'moment', 'highcharts',
        '_', '$modal', 'UtilFactory', 'AllocationFactory', 'NotificationFactory', 'UsageFactory',
        function($scope, $http, $timeout, $q, $location, $filter, moment, highcharts, _, $modal, UtilFactory,
            AllocationFactory, NotificationFactory, UsageFactory) {
            $scope.messages = [];
            $scope.$on('allocation:notifyMessage', function() {
                $scope.messages = NotificationFactory.getMessages();
            });
            $scope.loading = {};
            $scope.$on('allocation:notifyLoading', function() {
                $scope.loading = NotificationFactory.getLoading();
            });
            $scope.close = UtilFactory.closeMessage;
            $scope.isEmpty = UtilFactory.isEmpty;
            $scope.hasMessage = UtilFactory.hasMessage;
            $scope.isLoading = UtilFactory.isLoading;
            $scope.getMessages = UtilFactory.getMessages;
            $scope.getClass = UtilFactory.getClass;

            $scope.filter = {
                active: true,
                inactive: true,
                search: ''
            };

            $scope.reset = function() {
                $scope.selectedProjects = $scope.projects;
                $scope.filter.active = false;
                $scope.filter.inactive = false;
                $scope.filter.search = '';
            };

            var usageChartConfig = {
                options: {
                    chart: {
                        zoomType: 'x',
                        type: 'area'
                    },
                    rangeSelector: {
                        enabled: true,
                        selected: 2
                    },
                    navigator: {
                        enabled: true
                    },
                    colors: ['#7cb5ec', '#778b9e', '#acf19d'],
                    credits: {
                        enabled: false
                    },
                    plotOptions: {
                        area: {
                            dataLabels: {
                                enabled: true,
                                color: (highcharts.theme && highcharts.theme.dataLabelsColor) || 'white',
                                style: {
                                    textShadow: '0 0 3px black'
                                }
                            },
                            fillOpacity: 0.5,
                            marker: {
                                enabled: true,
                                radius: 3
                            },
                            shadow: true,
                            tooltip: {
                                valueDecimals: 2,
                            }
                        },
                        series: {
                            lineWidth: 1,
                            dataLabels: {
                                format: '{point.y:,.2f}'
                            }
                        }
                    },
                },
                series: [],
                title: {
                    text: ''
                },
                useHighStocks: true
            };


            var utilizationChartConfig = {
                options: {
                    chart: {
                        type: 'column',
                        alignTicks: false
                    },
                    rangeSelector: {
                        enabled: false,
                        //selected: 2
                    },
                    navigator: {
                        enabled: true
                    },
                    yAxis: {
                        labels: {
                            formatter: function() {
                                return this.value + '%';
                            }
                        }
                    },
                    // unused: gray, downtime: yellow, used: blue
                    //colors: ['#cccccc','#ffff66','#0000ff'],
                    colors: ['#b4c0ca', '#acf19d', '#368fe2'],
                    credits: {
                        enabled: false
                    },
                    legend: {
                        enabled: true,
                    },
                    plotOptions: {
                        column: {
                            stacking: 'percent',
                            dataLabels: {
                                enabled: true,
                                color: (Highcharts.theme && Highcharts.theme.dataLabelsColor) || 'white',
                                style: {
                                    textShadow: '0 0 3px black'
                                }
                            }
                        }
                    },
                    tooltip: {
                        pointFormat: '<span style="color:{series.color}">{series.name}</span>: <b>{point.y}</b> ({point.percentage:.0f}%)<br/>',
                        shared: true
                    },
                },
                series: [],
                title: {
                    text: 'Chameleon Utilization (SUs)'
                },
                useHighStocks: true
            };

            var utilizationUserBreakdownChartConfig = {
                options: {
                    chart: {
                        type: 'column'
                    },
                    xAxis: {
                        categories: []
                    },
                    yAxis: {
                        min: 0,
                        title: {
                            text: 'Total SUs Used'
                        },
                        stackLabels: {
                            enabled: true,
                            style: {
                                fontWeight: 'bold',
                                color: (highcharts.theme && highcharts.theme.textColor) || 'gray'
                            }
                        }
                    },
                    legend: {
                        align: 'right',
                        x: -30,
                        verticalAlign: 'top',
                        y: 25,
                        floating: true,
                        backgroundColor: (highcharts.theme && highcharts.theme.background) || 'white',
                        borderColor: '#CCC',
                        borderWidth: 1,
                        shadow: false
                    },
                    plotOptions: {
                        column: {
                            stacking: 'normal',
                            dataLabels: {
                                enabled: true,
                                color: (highcharts.theme && highcharts.theme.dataLabelsColor) || 'white',
                                style: {
                                    textShadow: '0 0 3px black'
                                }
                            }
                        }
                    },
                    tooltip: {
                        formatter: function() {
                            return '<b>' + this.x + '</b><br/>' +
                                this.series.name + ': ' + this.y + '<br/>' +
                                'Total: ' + this.point.stackTotal;
                        }
                    },
                    credits: {
                        enabled: false
                    },
                },
                title: {
                    text: 'Chameleon Utilization (SUs) - User Breakdown'
                },
                series: []
            };

            var usageByUserChartConfig = {
                options: {
                    chart: {
                        type: 'column'
                    },
                    xAxis: {
                        categories: []
                    },
                    yAxis: {
                        min: 0,
                        title: {
                            text: 'Total SUs Used'
                        },
                        stackLabels: {
                            enabled: true,
                            style: {
                                fontWeight: 'bold',
                                color: (highcharts.theme && highcharts.theme.textColor) || 'gray'
                            }
                        }
                    },
                    legend: {
                        align: 'right',
                        x: -30,
                        verticalAlign: 'top',
                        y: 25,
                        floating: true,
                        backgroundColor: (highcharts.theme && highcharts.theme.background) || 'white',
                        borderColor: '#CCC',
                        borderWidth: 1,
                        shadow: false
                    },
                    plotOptions: {
                        column: {
                            stacking: 'normal',
                            dataLabels: {
                                enabled: true,
                                color: (highcharts.theme && highcharts.theme.dataLabelsColor) || 'white',
                                style: {
                                    textShadow: '0 0 3px black'
                                }
                            }
                        }
                    },
                    tooltip: {
                        formatter: function() {
                            return '<b>' + this.x + '</b><br/>' +
                                this.series.name + ': ' + this.y + '<br/>' +
                                'Total: ' + this.point.stackTotal;
                        }
                    },
                    credits: {
                        enabled: false
                    },
                },
                title: {
                    text: ''
                },
                series: []
            };

            var processAllocations = function(projects) {
                for (var i = 0; i < projects.length; i++) {
                    var project = projects[i];
                    project.hasActiveAllocation = false;
                    if (!_.isEmpty(project.allocations)) {
                        for (var j = 0; j < project.allocations.length; j++) {
                            project.allocations[j].hasUsage = false;
                            if (_.contains(['active', 'inactive'], project.allocations[j].status.toLowerCase())) {
                                project.hasActiveAllocation = true;
                                project.allocations[j].hasUsage = true;
                                if (!project.selectedAllocation) {
                                    project.selectedAllocation = project.allocations[j];
                                }
                            }
                        }
                    }
                }
            };

            $scope.getAllocations = function() {
                $scope.projects = [];
                AllocationFactory.getAllocations().then(function() {
                    $scope.projects = AllocationFactory.projects;
                    processAllocations($scope.projects);
                    $scope.updateSelected();
                });
            };

            $scope.utilization = {
                from: null,
                to: null,
                startOpened: false,
                endOpened: false,
                selectedQueue: '',
                downtimes: [],
                usage: [],
                user_usage: [],
            };

            var getUtilization = function() {
                $scope.utilization.data = [];
                var kwargs = {};
                if ($scope.utilization.from) {
                    // kwargs.from = moment($scope.utilization.from).utc().format('YYYY-MM-DD');
                    kwargs.from = moment($scope.utilization.from).format('YYYY-MM-DD');
                }
                if ($scope.utilization.to) {
                    kwargs.to = moment($scope.utilization.to).format('YYYY-MM-DD');

                }
                if ($scope.utilization.selectedQueue) {
                    kwargs.queue = $scope.utilization.selectedQueue;
                }
                var promises = [];
                NotificationFactory.clearMessages('utilization');
                NotificationFactory.addLoading('utilization');
                promises.push(UsageFactory.getDowntimes(kwargs));
                promises.push(UsageFactory.getDailyUsage(kwargs));
                promises.push(UsageFactory.getDailyUsageUserBreakdown(kwargs));
                $q.all(promises).then(function() {
                        NotificationFactory.removeLoading('utilization');
                        $scope.utilization.downtimes = UsageFactory.downtimes;
                        $scope.utilization.usage = UsageFactory.usage;
                        $scope.utilization.user_usage = UsageFactory.user_usage;
                        drawUtilizationChart();
                    },
                    function() {
                        NotificationFactory.removeLoading('utilization');
                    });
            };

            $scope.selections = {
                usernamemodel: '',
                username: ''
            };

            $scope.getUserAllocations = function() {
                $scope.projects = [];
                $scope.selections.username = $scope.selections.usernamemodel;
                $location.url('/' + $scope.selections.username);
                $scope.submitted = true;
                if ($scope.selections.username && $scope.selections.username.length > 0) {
                    AllocationFactory.getUserAllocations($scope.selections.username).then(function() {
                        $scope.projects = AllocationFactory.userProjects;
                        if ($scope.projects && $scope.projects.length > 0) {
                            processAllocations($scope.projects);
                            $scope.updateSelected();
                        }
                    });
                }
            };

            $scope.updateSelected = function() {
                $scope.selectedProjects = UtilFactory.updateSelected($scope.projects, $scope.selectedProjects, $scope.filter);
            };


            $scope.getAllocationsWithUsage = function(project) {
                return _.filter(project.allocations, function(allocation) {
                    return allocation.hasUsage && !allocation.doNotShow;
                });

            };

            var drawUsageChart = function(project) {
                project.usageChartConfig = angular.copy(usageChartConfig);
                project.usageChartConfig.title.text = 'Allocation Usage - ' +
                    project.selectedAllocation.resource + ' (' + $filter('date')(project.selectedAllocation.start, 'dd MMMM yyyy') +
                    ' - ' + $filter('date')(project.selectedAllocation.end, 'dd MMMM yyyy') + ')';
                project.usageChartConfig.series = [];
                project.usageChartConfig.series.push({
                    id: project.selectedAllocation.id,
                    name: 'SUs: ',
                    data: project.selectedAllocation.usage,
                    marker: {
                        enabled: true,
                        radius: 2
                    },
                    shadow: true,
                    tooltip: {
                        valueDecimals: 2,
                    }
                });
            };

            var drawUtilizationChart = function() {
                $scope.utilization.usageChartConfig = angular.copy(utilizationChartConfig);
                $scope.utilization.usageUserBreakdownChartConfig = angular.copy(utilizationUserBreakdownChartConfig);
                var downtimeData = [];
                var dailyUsageData = [];
                var unusedNodesData = [];
                var userBreakdownData = {};
                // nodes are fixed at 556, so this is node hours
                var totalNodes = 556 * 24;
                angular.forEach($scope.utilization.usage, function(usage) {
                    dailyUsageData.push([moment(usage.date, 'YYYY-MM-DD').valueOf(), usage.nodes_used]);
                     var downtime = _.findWhere($scope.utilization.downtimes, {date: usage.date});
                     var unusedNodes = 0;
                     if(downtime){
                        //console.log('downtime', downtime);
                        downtimeData.push([moment(downtime.date, 'YYYY-MM-DD').valueOf(), downtime.nodes_down]);
                        unusedNodes = totalNodes - usage.nodes_used - downtime.nodes_down;
                        //console.log("Total: " + totalNodes + ", Used: " + usage.nodes_used + ", Downtimes: " + downtime.nodes_down);
                        unusedNodesData.push([moment(usage.date, 'YYYY-MM-DD').valueOf(), unusedNodes]);
                     }
                     else{
                        unusedNodes = totalNodes - usage.nodes_used;
                        //console.log("Total: " + totalNodes + ", Used: " + usage.nodes_used);
                        unusedNodesData.push([moment(usage.date, 'YYYY-MM-DD').valueOf(), unusedNodes]);
                     }
                     
                });

                angular.forEach($scope.utilization.user_usage, function(user_usage) {
                  if (user_usage.queue in userBreakdownData) {
                    userBreakdownData[user_usage.queue].push(user_usage.nodes_used)
                  } else {
                    userBreakdownData[user_usage.queue] = [user_usage.nodes_used]
                  }
                  $scope.utilization.usageUserBreakdownChartConfig.options.xAxis.categories.push(user_usage.username);
                });

                $scope.utilization.usageChartConfig.series.push( {
                    name: 'Unused',
                    data: unusedNodesData,

                },{
                    name: 'Downtime',
                    data: downtimeData,

                },{
                    name: 'Used',
                    data: dailyUsageData,

                });

                $scope.utilization.usageUserBreakdownChartConfig.series.push({
                      name: 'kvm@tacc',
                      data: userBreakdownData['kvm@tacc'],
                      }, {
                      name: 'kvm@uc',
                      data: userBreakdownData['kvm@uc'],
                      }, {
                      name: 'chi@tacc',
                      data: userBreakdownData['chi@tacc'],
                      }, {
                      name: 'chi@uc',
                      data: userBreakdownData['chi@uc'],

                    });

            };

            var getData = function(project) {
                if (project.selectedUser) {
                    if (project.selectedQueue) {
                        UsageFactory.getAllocationUserQueueUsage(project).then(function() {
                            drawUsageChart(project);
                        });
                    } else {
                        UsageFactory.getAllocationUserUsage(project).then(function() {
                            drawUsageChart(project);
                        });
                    }

                } else if (project.selectedQueue) {
                    UsageFactory.getAllocationQueueUsage(project).then(function() {
                        drawUsageChart(project);
                    });

                } else {
                    UsageFactory.getAllocationUsage(project).then(function() {
                        drawUsageChart(project);
                    });
                }

            };

            $scope.viewUsage = function(project) {
                project.showUPUChart = false;
                project.showChart = true;
                AllocationFactory.getProjectUsers(project);
                getData(project);
            };

            var drawUsageByUsersChart = function(project) {
                project.usageByUserChartConfig = angular.copy(usageByUserChartConfig);
                project.usageByUserChartConfig.title.text = $filter('date')(project.from, 'dd MMMM yyyy') +
                    ' - ' + $filter('date')(project.to, 'dd MMMM yyyy');
                project.usageByUserChartConfig.series = [];
                project.usageByUserChartConfig.options.xAxis.categories = project.selectedAllocation.usageUsers;
                for (var key in project.selectedAllocation.usageByUsers) {
                    project.usageByUserChartConfig.series.push({
                        name: key,
                        data: project.selectedAllocation.usageByUsers[key]
                    });
                }
            };

            var getUsageByUsers = function(project) {
                UsageFactory.getUsageByUsers(project).then(function() {
                    drawUsageByUsersChart(project);
                });
            };

            var setDefaultDates = function(project) {
                project.from = $scope.getMinDate(project);
                project.to = $scope.getMaxDate(project);
            };

            var setDefaultDateRange = function() {
                $scope.utilization.from = moment().subtract(7, 'days').format('YYYY-MM-DD');
                $scope.utilization.to = $scope.getMaxUtilizationDate();
            };

            var setMaximumDateRange = function() {
                $scope.utilization.from = $scope.getMinUtilizationDate();
                $scope.utilization.to = $scope.getMaxUtilizationDate();
            };

            $scope.viewUsagePerUser = function(project) {
                if (!project.from || !project.to) {
                    project.dateRange = 'all';
                    setDefaultDates(project);
                }

                project.showChart = false;
                project.showUPUChart = true;
                getUsageByUsers(project);
            };

            $scope.updateUsageByUsersChart = function(project, dateRange) {
                switch (dateRange) {
                    case '1m':
                        project.dateRange = '1m';
                        project.from = moment().subtract(1, 'months').format('YYYY-MM-DD');
                        project.to = moment().format('YYYY-MM-DD');
                        break;
                    case '3m':
                        project.dateRange = '3m';
                        project.from = moment().subtract(3, 'months').format('YYYY-MM-DD');
                        project.to = moment().format('YYYY-MM-DD');
                        break;
                    case '6m':
                        project.dateRange = '6m';
                        project.from = moment().subtract(6, 'months').format('YYYY-MM-DD');
                        project.to = moment().format('YYYY-MM-DD');
                        break;
                    case 'ytd':
                        project.dateRange = 'ytd';
                        project.from = moment().startOf('year').format('YYYY-MM-DD');
                        project.to = moment().format('YYYY-MM-DD');
                        break;
                    case '1y':
                        project.dateRange = '1y';
                        project.from = moment().subtract(1, 'years').format('YYYY-MM-DD');
                        project.to = moment().format('YYYY-MM-DD');
                        break;
                    case 'all':
                        project.dateRange = 'all';
                        setDefaultDates(project);
                        break;
                    default:
                        project.dateRange = 'custom';
                        project.from = moment(project.from).format('YYYY-MM-DD');
                        project.to = moment(project.to).format('YYYY-MM-DD');
                        break;

                }
                getUsageByUsers(project);
            };

            $scope.updateUtilizationChart = function(dateRange) {
                switch (dateRange) {
                    case '1m':
                        $scope.utilization.dateRange = '1m';
                        $scope.utilization.from = moment().subtract(1, 'months').format('YYYY-MM-DD');
                        $scope.utilization.to = moment().startOf('day').format('YYYY-MM-DD');
                        break;
                    case '3m':
                        $scope.utilization.dateRange = '3m';
                        $scope.utilization.from = moment().subtract(3, 'months').format('YYYY-MM-DD');
                        $scope.utilization.to = moment().format('YYYY-MM-DD');
                        break;
                    case '6m':
                        $scope.utilization.dateRange = '6m';
                        $scope.utilization.from = moment().subtract(6, 'months').format('YYYY-MM-DD');
                        $scope.utilization.to = moment().format('YYYY-MM-DD');
                        break;
                    case 'ytd':
                        $scope.utilization.dateRange = 'ytd';
                        $scope.utilization.from = moment().startOf('year').format('YYYY-MM-DD');
                        $scope.utilization.to = moment().format('YYYY-MM-DD');
                        break;
                    case '1y':
                        $scope.utilization.dateRange = '1y';
                        $scope.utilization.from = moment().subtract(1, 'years').format('YYYY-MM-DD');
                        $scope.utilization.to = moment().format('YYYY-MM-DD');
                        break;
                    case 'all':
                        $scope.utilization.dateRange = 'all';
                        setMaximumDateRange();
                        break;
                    default:
                        $scope.utilization.dateRange = 'custom';
                        $scope.utilization.from = moment($scope.utilization.from).format('YYYY-MM-DD');
                        $scope.utilization.to = moment($scope.utilization.to).format('YYYY-MM-DD');
                        break;

                }
                getUtilization();
            };

            $scope.viewUserUsage = function(project) {
                project.showChart = true;
                project.selectedUser = {
                    username: $scope.selections.username
                };
                getData(project);
            };

            $scope.updateChart = function(project) {
                getData(project);
            };

            $scope.submitted = false;

            $scope.handleKeyPress = function(e) {
                var key = e.keyCode || e.which;
                if (key === 13) {
                    $scope.getUserAllocations();
                }
            };

            $scope.dateOptions = {
                formatYear: 'yy',
                startingDay: 1
            };

            $scope.format = 'dd MMMM yyyy';

            //calendar
            $scope.disabled = function(date, mode) {
                return (false && mode === 'day' && (date.getDay() === 0 || date.getDay() === 6));
            };

            $scope.getMaxDate = function(project) {
                var today = moment().format('YYYY-MM-DD');
                if (moment(project.selectedAllocation.end).isAfter(today, 'day')) {
                    return today;
                } else {
                    return moment(project.selectedAllocation.end).format('YYYY-MM-DD');
                }
            };

            $scope.getMinDate = function(project) {
                // return moment(project.selectedAllocation.start).startOf('day').format('YYYY-MM-DDTHH:mm:ssZ');
                return moment(project.selectedAllocation.start).format('YYYY-MM-DD');
            };

            $scope.getMaxUtilizationDate = function() {
                return moment().format('YYYY-MM-DD');
            };

            $scope.getMinUtilizationDate = function() {
                return moment('12-01-2014').format('YYYY-MM-DD');
            };

            $scope.open = {

            };

            $scope.isOpen = function($event, project, caltype) {
                $event.preventDefault();
                $event.stopPropagation();
                if (caltype === 'start') {
                    project.endOpened = false;
                    project.startOpened = true;
                } else if (caltype === 'end') {
                    project.startOpened = false;
                    project.endOpened = true;
                }
            };

            $scope.isOpen4Utilization = function($event, caltype) {
                $event.preventDefault();
                $event.stopPropagation();
                if (caltype === 'start') {
                    $scope.utilization.endOpened = false;
                    $scope.utilization.startOpened = true;
                } else if (caltype === 'end') {
                    $scope.utilization.endOpened = true;
                    $scope.utilization.startOpened = false;
                }
            };

            //if path show user allocation usage, if not show project allocation usage
            var path = $location.path();
            if (path) {
                $scope.selections.usernamemodel = path.substring(1);
                $scope.getUserAllocations();
            } else {
                if ($location.absUrl().indexOf('utilization') !== -1) {
                    setDefaultDateRange();
                    getUtilization();
                } else {
                    $scope.getAllocations();
                }
            }
        }
    ]);
