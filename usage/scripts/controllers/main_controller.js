/**
 * author agauli
 */
'use strict';

angular.module('usageApp')
    .controller('UsageController', ['$scope', '$http', '$timeout', '$location', '$filter', 'moment', 'highcharts',
        '_', '$modal', 'UtilFactory', 'AllocationFactory', 'NotificationFactory', 'UsageFactory',
        function($scope, $http, $timeout, $location, $filter, moment, highcharts, _, $modal, UtilFactory,
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

            var usageDowntimesChartConfig = angular.copy(usageChartConfig);
            // usageDowntimesChartConfig.options.xAxis = {
            //     type: 'datetime'
            //     //categories: ['1750', '1800', '1850', '1900', '1950', '1999', '2050'],
            //     tickmarkPlacement: 'on',
            //     title: {
            //         enabled: false
            //     }
            // };
            usageDowntimesChartConfig.options.yAxis = {
                title: {
                    text: 'Percent'
                }
            };
            usageDowntimesChartConfig.options.plotOptions.area.stacking = 'percent';
            usageDowntimesChartConfig.options.plotOptions.area.marker = {
                lineWidth: 1,
                lineColor: '#ffffff'
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

            $scope.downtimes = {
                from: null,
                to: null,
                startOpened: false,
                endOpened: false,
                selectedQueue: '',
                data: []
            };

            var getDowntimes = function() {
                $scope.downtimes.data = [];
                var kwargs = {};
                if ($scope.downtimes.from) {
                    kwargs.from = moment($scope.downtimes.from).utc().format('YYYY-MM-DDTHH:mm:ss') + 'Z';
                }
                if ($scope.downtimes.to) {
                    kwargs.to = moment($scope.downtimes.to).utc().format('YYYY-MM-DDTHH:mm:ss') + 'Z';

                }
                if ($scope.downtimes.selectedQueue) {
                    kwargs.queue = $scope.downtimes.selectedQueue;
                }
                UsageFactory.getDowntimes(kwargs).then(function() {
                    $scope.downtimes.data = UsageFactory.downtimes;
                    $scope.downtimes.unused = UsageFactory.unused;
                    drawDowntimesChart();
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

            var drawDowntimesChart = function() {
                $scope.downtimes.usageChartConfig = angular.copy(usageDowntimesChartConfig);
                $scope.downtimes.usageChartConfig.title.text = 'Downtimes and Usage';
                $scope.downtimes.usageChartConfig.series = [];
                $scope.downtimes.usageChartConfig.series.push({
                    id: 'unused',
                    name: 'Nodes not used',
                    data: $scope.downtimes.unused
                });
                $scope.downtimes.usageChartConfig.series.push({
                    id: 'downtimes',
                    name: 'Nodes down',
                    data: $scope.downtimes.data
                });
                $scope.downtimes.usageChartConfig.series.push({
                    id: 'usage',
                    name: 'Nodes used',
                    data: $scope.downtimes.data
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

            var setDefaultDowntimeDates = function() {
                $scope.downtimes.from = $scope.getMinDowntimeDate();
                $scope.downtimes.to = $scope.getMaxDowntimeDate();
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
                        project.from = moment().startOf('day').subtract(1, 'months').format('YYYY-MM-DDTHH:mm:ssZ');
                        project.to = moment().startOf('day').format('YYYY-MM-DDTHH:mm:ssZ');
                        break;
                    case '3m':
                        project.dateRange = '3m';
                        project.from = moment().startOf('day').subtract(3, 'months').format('YYYY-MM-DDTHH:mm:ssZ');
                        project.to = moment().startOf('day').format('YYYY-MM-DDTHH:mm:ssZ');
                        break;
                    case '6m':
                        project.dateRange = '6m';
                        project.from = moment().startOf('day').subtract(6, 'months').format('YYYY-MM-DDTHH:mm:ssZ');
                        project.to = moment().startOf('day').format('YYYY-MM-DDTHH:mm:ssZ');
                        break;
                    case 'ytd':
                        project.dateRange = 'ytd';
                        project.from = moment().startOf('day').startOf('year').format('YYYY-MM-DDTHH:mm:ssZ');
                        project.to = moment().startOf('day').format('YYYY-MM-DDTHH:mm:ssZ');
                        break;
                    case '1y':
                        project.dateRange = '1y';
                        project.from = moment().startOf('day').subtract(1, 'years').format('YYYY-MM-DDTHH:mm:ssZ');
                        project.to = moment().startOf('day').format('YYYY-MM-DDTHH:mm:ssZ');
                        break;
                    case 'all':
                        project.dateRange = 'all';
                        setDefaultDates(project);
                        break;
                    default:
                        project.dateRange = 'custom';
                        project.from = moment(project.from).startOf('day').format('YYYY-MM-DDTHH:mm:ssZ');
                        project.to = moment(project.to).startOf('day').format('YYYY-MM-DDTHH:mm:ssZ');
                        break;

                }
                getUsageByUsers(project);
            };

            $scope.updateDowntimesUsageChart = function(dateRange) {
                switch (dateRange) {
                    case '1m':
                        $scope.downtimes.dateRange = '1m';
                        $scope.downtimes.from = moment().startOf('day').subtract(1, 'months').format('YYYY-MM-DDTHH:mm:ssZ');
                        $scope.downtimes.to = moment().startOf('day').format('YYYY-MM-DDTHH:mm:ssZ');
                        break;
                    case '3m':
                        $scope.downtimes.dateRange = '3m';
                        $scope.downtimes.from = moment().startOf('day').subtract(3, 'months').format('YYYY-MM-DDTHH:mm:ssZ');
                        $scope.downtimes.to = moment().startOf('day').format('YYYY-MM-DDTHH:mm:ssZ');
                        break;
                    case '6m':
                        $scope.downtimes.dateRange = '6m';
                        $scope.downtimes.from = moment().startOf('day').subtract(6, 'months').format('YYYY-MM-DDTHH:mm:ssZ');
                        $scope.downtimes.to = moment().startOf('day').format('YYYY-MM-DDTHH:mm:ssZ');
                        break;
                    case 'ytd':
                        $scope.downtimes.dateRange = 'ytd';
                        $scope.downtimes.from = moment().startOf('day').startOf('year').format('YYYY-MM-DDTHH:mm:ssZ');
                        $scope.downtimes.to = moment().startOf('day').format('YYYY-MM-DDTHH:mm:ssZ');
                        break;
                    case '1y':
                        $scope.downtimes.dateRange = '1y';
                        $scope.downtimes.from = moment().startOf('day').subtract(1, 'years').format('YYYY-MM-DDTHH:mm:ssZ');
                        $scope.downtimes.to = moment().startOf('day').format('YYYY-MM-DDTHH:mm:ssZ');
                        break;
                    case 'all':
                        $scope.downtimes.dateRange = 'all';
                        setDefaultDowntimeDates();
                        break;
                    default:
                        $scope.downtimes.dateRange = 'custom';
                        $scope.downtimes.from = moment($scope.downtimes.from).startOf('day').format('YYYY-MM-DDTHH:mm:ssZ');
                        $scope.downtimes.to = moment($scope.downtimes.to).startOf('day').format('YYYY-MM-DDTHH:mm:ssZ');
                        break;

                }
                getDowntimes();
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
                var today = moment().startOf('day').format('YYYY-MM-DDTHH:mm:ssZ');
                if (moment(project.selectedAllocation.end).isAfter(today, 'day')) {
                    return today;
                } else {
                    return moment(project.selectedAllocation.end).startOf('day').format('YYYY-MM-DDTHH:mm:ssZ');
                }
            };

            $scope.getMinDate = function(project) {
                return moment(project.selectedAllocation.start).startOf('day').format('YYYY-MM-DDTHH:mm:ssZ');
            };

            $scope.getMaxDowntimeDate = function() {
                return moment().format('YYYY-MM-DDTHH:mm:ssZ');
            };

            $scope.getMinDowntimeDate = function() {
                return moment('12-01-2014', 'MM-DD-YYYY').format('YYYY-MM-DDTHH:mm:ssZ');
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

            $scope.isOpen4Downtimes = function($event, caltype) {
                $event.preventDefault();
                $event.stopPropagation();
                if (caltype === 'start') {
                    $scope.downtimes.endOpened = false;
                    $scope.downtimes.startOpened = true;
                } else if (caltype === 'end') {
                    $scope.downtimes.endOpened = true;
                    $scope.downtimes.startOpened = false;
                }
            };

            //if path show user allocation usage, if not show project allocation usage
            var path = $location.path();
            if (path) {
                $scope.selections.usernamemodel = path.substring(1);
                $scope.getUserAllocations();
            } else {
                if ($location.absUrl().indexOf('downtimes') !== -1) {
                    setDefaultDowntimeDates();
                    getDowntimes();
                } else {
                    $scope.getAllocations();
                }
            }
        }
    ]);
