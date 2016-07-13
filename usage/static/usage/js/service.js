'use strict';
angular
    .module('usageApp.service')
    .factory('NotificationFactory', ['$rootScope', '$timeout', '_', function($rootScope, $timeout, _) {
        var factory = {},
            messages = {},
            loading = {};
        factory.uuid = function() {
            /* jshint bitwise: false */
            return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
                var r = Math.random() * 16 | 0,
                    v = c === 'x' ? r : (r & 0x3 | 0x8);
                return v.toString(16);
            });
            /* jshint bitwise: true */
        };
        factory.addLoading = function(resourceName) {
            loading[resourceName] = true;
            $rootScope.$broadcast('allocation:notifyLoading');
        };
        factory.removeLoading = function(resourceName) {
            delete loading[resourceName];
            $rootScope.$broadcast('allocation:notifyLoading');
        };
        factory.getMessages = function() {
            return messages;
        };
        factory.getLoading = function() {
            return loading;
        };
        factory.clearMessages = function(key) {
            key = key || 'all';
            if (key === 'all') {
                messages = {};
            } else {
                messages[key] = [];
            }
            $rootScope.$broadcast('allocation:notifyMessage');
        };
        factory.removeMessage = function(key, messageObj, id) {
            if (typeof id !== 'undefined') {
                key = key + id;
            }
            var msgs = messages[key];
            if (!msgs || msgs.length < 1) {
                return;
            }
            messages[key] = _.reject(msgs, function(m) {
                return m._id === messageObj._id;
            });
            $rootScope.$broadcast('allocation:notifyMessage');
        };
        factory.addMessage = function(key, message, type) {
            var messageObj = {};
            messageObj.body = message;
            messageObj.type = type;
            messageObj._id = factory.uuid();
            if (typeof messages[key] === 'undefined') {
                messages[key] = [];
            }
            messages[key].push(messageObj);
            $rootScope.$broadcast('allocation:notifyMessage');
            var duration = messageObj.type === 'danger' ? 0 : 5000;
            if (duration > 0) {
                $timeout(function() {
                    factory.removeMessage(key, messageObj);
                }, duration);
            }

        };
        return factory;
    }])
    .factory('UtilFactory', ['_', 'moment', 'NotificationFactory', function(_, moment, NotificationFactory) {
        var factory = {};
        factory.getClass = function(allocation) {
            var status = allocation.status.toLowerCase();
            if (status === 'pending') {
                return 'label label-warning';
            } else if (status === 'rejected') {
                return 'label label-danger';
            } else {
                return 'label label-success';
            }
        };

        factory.isLoading = function(msgKey, model) {
            if (!msgKey || !model) {
                return false;
            }
            var key = msgKey + model.id;
            if (typeof NotificationFactory.getLoading()[key] === 'undefined') {
                return false;
            } else {
                return true;
            }
        };

        factory.closeMessage = function(key, msg, id) {
            id = (typeof id === 'undefined' || id === null) ? '' : id;
            key = key + id;
            NotificationFactory.removeMessage(key, msg);
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

        factory.hasMessage = function(arr, type) {
            var pass = false;
            if (typeof arr === 'undefined' || arr === null || arr === [] || typeof type === 'undefined' || type === null || type === '') {
                return pass;
            } else {
                for (var i in arr) {
                    if (arr[i].type === type) {
                        pass = true;
                        break;
                    }
                }
            }
            return pass;
        };

        factory.getMessages = function(msgKey, model) {
            if (!msgKey || !model) {
                return [];
            }
            var key = msgKey + model.id;
            var msgs = NotificationFactory.getMessages()[key];
            if (typeof msgs !== 'undefined' && msgs.length > 0) {
                return msgs;
            } else {
                return [];
            }
        };

        factory.search = function(projects, searchKey) {
            if (!searchKey) {
                return angular.copy(projects);
            } else {
                return _.filter(projects, function(project) {
                    var term = searchKey.toLowerCase();
                    var pass = false;
                    var projectTitle = project.title || '';
                    var chargeCode = project.chargeCode || '';
                    var pi = project.pi || false;
                    if (projectTitle.toLowerCase().indexOf(term) > -1) {
                        pass = true;
                    } else if (chargeCode.toLowerCase().indexOf(term) > -1) {
                        pass = true;
                    } else if (pi && (
                            pi.lastName.toLowerCase().indexOf(term) > -1 ||
                            pi.firstName.toLowerCase().indexOf(term) > -1 ||
                            pi.username.toLowerCase().indexOf(term) > -1 ||
                            pi.email.toLowerCase().indexOf(term) > -1)) {
                        pass = true;
                    }
                    return pass;
                });
            }
        };

        factory.updateSelected = function(projects, selectedProjects, filter) {
            var chosenStatusFilters = [];
            for (var key in filter) {
                if (filter[key] === true) {
                    chosenStatusFilters.push(key.toLowerCase());
                }
            }
            selectedProjects = factory.search(projects, filter.search);
            if (chosenStatusFilters.length !== 0) {
                selectedProjects = _.filter(selectedProjects, function(project) {
                    var pass = false;
                    _.each(project.allocations, function(allocation) {
                        allocation.doNotShow = true;
                        var status = allocation.status.toLowerCase();
                        if (_.contains(chosenStatusFilters, status)) {
                            allocation.doNotShow = false;
                            pass = true;
                        }
                    });
                    return pass;
                });
            } else {
                _.each(selectedProjects, function(project) {
                    _.each(project.allocations, function(allocation) {
                        allocation.doNotShow = false;
                    });
                });
            }
            return selectedProjects;
        };

        return factory;
    }])
    .factory('AllocationFactory', ['$http', '_', 'moment', 'NotificationFactory', function($http, _, moment, NotificationFactory) {
        var factory = {};
        factory.projects = [];
        factory.userProjects = [];

        //this endpoint is served by allocations app
        factory.getAllocations = function() {
            var errorMsg = 'There was an error loading allocations.';
            NotificationFactory.clearMessages('allocations');
            NotificationFactory.addLoading('allocations');
            return $http({
                    method: 'GET',
                    url: '/admin/allocations/view/',
                    cache: 'true'
                })
                .then(function(response) {
                        NotificationFactory.removeLoading('allocations');
                        factory.projects = response.data;
                    },
                    function() {
                        NotificationFactory.addMessage('allocations', errorMsg, 'danger');
                        NotificationFactory.removeLoading('allocations');
                    });
        };
        //this endpoint is served by allocations app
        factory.getUserAllocations = function(username) {
            var errorMsg = 'There was an error loading user allocations.';
            NotificationFactory.clearMessages('userAllocations');
            NotificationFactory.addLoading('userAllocations');
            return $http({
                    method: 'GET',
                    url: '/admin/allocations/user/' + username + '/',
                    cache: 'true'
                })
                .then(function(response) {
                        NotificationFactory.removeLoading('userAllocations');
                        if(response.data.status.toLowerCase() === 'error'){
                           NotificationFactory.addMessage('userAllocations', response.data.msg, 'danger');
                        }
                        else{
                           factory.userProjects = response.data.result;
                        }
                    },
                    function() {
                        NotificationFactory.addMessage('userAllocations', errorMsg, 'danger');
                        NotificationFactory.removeLoading('userAllocations');
                    });
        };

        factory.getProjectUsers = function(project) {
            var msgKey = 'projectUsers' + project.id;
            var errorMsg = 'There was an error loading project users.';
            NotificationFactory.clearMessages(msgKey);
            NotificationFactory.addLoading(msgKey);
            return $http({
                    method: 'GET',
                    url: '/admin/usage/projects/' + project.id + '/users/',
                    cache: 'true'
                })
                .then(function(response) {
                        NotificationFactory.removeLoading(msgKey);
                        project.users = response.data;
                    },
                    function() {
                        NotificationFactory.addMessage(msgKey, errorMsg, 'danger');
                        NotificationFactory.removeLoading(msgKey);
                    });
        };

        return factory;
    }])
    .factory('UsageFactory', ['$http', '_', 'moment', 'NotificationFactory', function($http, _, moment, NotificationFactory) {
        var factory = {};
        factory.projects = [];
        factory.userProjects = [];
        factory.downtimes = [];
        factory.usage = [];

        var processData = function(project, response) {
            var usage = {};
            var curatedUsage = [];
            _.each(response.data, function(datum) {
                if (datum[0] in usage) {
                    usage[datum[0]] += datum[1];
                } else {
                    usage[datum[0]] = datum[1];
                }
            });
            _.each(_.keys(usage), function(key) {
                var arr = [];
                arr[0] = parseInt(key, 10);
                arr[1] = usage[key];
                curatedUsage.push(arr);
            });
            project.selectedAllocation.usage = _.sortBy(curatedUsage, function(arr) {
                return arr[0];
            });
        };

        var processUsageByUsers = function(project, response) {
            var formattedUsageByUsers = {};
            var totalUsageByAUser = [];
            var queues = [];
            for (var user in response.data) {
                var usage = response.data[user];
                var totalUsage = 0.0;
                for (var queue in usage) {
                    if (!_.contains(queues, queue)) {
                        queues.push(queue);
                    }
                    totalUsage += usage[queue];

                }
                totalUsageByAUser.push({
                    'user': user,
                    'total': totalUsage
                });

            }

            totalUsageByAUser = _.sortBy(totalUsageByAUser, 'total').reverse();
            var users = _.pluck(totalUsageByAUser, 'user');
            _.each(users, function(key) {
                _.each(queues, function(queue) {
                    var val = response.data[key][queue] || 0;
                    if (!formattedUsageByUsers.hasOwnProperty(queue)) {
                        formattedUsageByUsers[queue] = [];
                    }
                    formattedUsageByUsers[queue].push(Math.round(val * 100) / 100);
                });
            });
            project.selectedAllocation.usageUsers = users;
            project.selectedAllocation.usageByUsers = formattedUsageByUsers;
        };

        factory.getAllocationUsage = function(project) {
            var msgKey = 'allocationUsage' + project.id;
            var errorMsg = 'There was an error loading allocation usage.';
            NotificationFactory.clearMessages(msgKey);
            NotificationFactory.addLoading(msgKey);
            var startDate = moment(project.selectedAllocation.start).utc().format('YYYY-MM-DD');
            var endDate = moment(project.selectedAllocation.end).utc().format('YYYY-MM-DD');
            return $http({
                    method: 'GET',
                    url: '/admin/usage/allocation/' + project.selectedAllocation.id +
                        '/?from=' + startDate + '&to=' + endDate,
                    cache: 'true'
                })
                .then(function(response) {
                        NotificationFactory.removeLoading(msgKey);
                        processData(project, response);
                    },
                    function() {
                        NotificationFactory.addMessage(msgKey, errorMsg, 'danger');
                        NotificationFactory.removeLoading(msgKey);
                    });
        };

        factory.getUsageByUsers = function(project) {
            var msgKey = 'usageByUsers' + project.id;
            var errorMsg = 'There was an error loading usage by users.';
            NotificationFactory.clearMessages(msgKey);
            NotificationFactory.addLoading(msgKey);
            var startDate = moment(project.from).utc().format('YYYY-MM-DD');
            var endDate = moment(project.to).utc().format('YYYY-MM-DD');
            return $http({
                    method: 'GET',
                    url: '/admin/usage/usage-by-users/' + project.selectedAllocation.id +
                        '/?from=' + startDate + '&to=' + endDate,
                    cache: 'true'
                })
                .then(function(response) {
                        NotificationFactory.removeLoading(msgKey);
                        processUsageByUsers(project, response);
                    },
                    function() {
                        NotificationFactory.addMessage(msgKey, errorMsg, 'danger');
                        NotificationFactory.removeLoading(msgKey);
                    });
        };

        factory.getAllocationUserUsage = function(project) {
            var msgKey = 'allocationUsage' + project.id;
            var errorMsg = 'There was an error loading user allocation usage.';
            NotificationFactory.clearMessages(msgKey);
            NotificationFactory.addLoading(msgKey);
            var startDate = moment(project.selectedAllocation.start).utc().format('YYYY-MM-DD');
            var endDate = moment(project.selectedAllocation.end).utc().format('YYYY-MM-DD');
            return $http({
                    method: 'GET',
                    url: '/admin/usage/allocation/' + project.selectedAllocation.id + '/username/' + project.selectedUser.username +
                        '/?from=' + startDate + '&to=' + endDate,
                    cache: 'true'
                })
                .then(function(response) {
                        NotificationFactory.removeLoading(msgKey);
                        processData(project, response);
                    },
                    function() {
                        NotificationFactory.addMessage(msgKey, errorMsg, 'danger');
                        NotificationFactory.removeLoading(msgKey);
                    });
        };

        factory.getAllocationUserQueueUsage = function(project) {
            var msgKey = 'allocationUsage' + project.id;
            var errorMsg = 'There was an error loading user queue allocation usage.';
            NotificationFactory.clearMessages(msgKey);
            NotificationFactory.addLoading(msgKey);
            var startDate = moment(project.selectedAllocation.start).utc().format('YYYY-MM-DD');
            var endDate = moment(project.selectedAllocation.end).utc().format('YYYY-MM-DD');
            return $http({
                    method: 'GET',
                    url: '/admin/usage/allocation/' + project.selectedAllocation.id + '/username/' +
                        project.selectedUser.username + '/queue/' + project.selectedQueue +
                        '/?from=' + startDate + '&to=' + endDate,
                    cache: 'true'
                })
                .then(function(response) {
                        NotificationFactory.removeLoading(msgKey);
                        processData(project, response);
                    },
                    function() {
                        NotificationFactory.addMessage(msgKey, errorMsg, 'danger');
                        NotificationFactory.removeLoading(msgKey);
                    });
        };

        factory.getAllocationQueueUsage = function(project) {
            var msgKey = 'allocationUsage' + project.id;
            var errorMsg = 'There was an error loading queue allocation usage.';
            NotificationFactory.clearMessages(msgKey);
            NotificationFactory.addLoading(msgKey);
            var startDate = moment(project.selectedAllocation.start).utc().format('YYYY-MM-DD');
            var endDate = moment(project.selectedAllocation.end).utc().format('YYYY-MM-DD');
            return $http({
                    method: 'GET',
                    url: '/admin/usage/allocation/' + project.selectedAllocation.id + '/queue/' + project.selectedQueue +
                        '/?from=' + startDate + '&to=' + endDate,
                    cache: 'true'
                })
                .then(function(response) {
                        NotificationFactory.removeLoading(msgKey);
                        processData(project, response);
                    },
                    function() {
                        NotificationFactory.addMessage(msgKey, errorMsg, 'danger');
                        NotificationFactory.removeLoading(msgKey);
                    });
        };

        factory.getDailyUsage = function(params) {
            var msgKey = 'utilization';
            var errorMsg = 'There was an error loading daily usage.';
            return $http({
                    method: 'GET',
                    url: '/admin/usage/daily-usage/',
                    params: params,
                    cache: 'true',
                })
                .then(function(response) {
                        factory.usage = response.data.result;
                        factory.usage = _.sortBy(factory.usage, function(obj) {
                            return moment(obj.date, 'YYYY-MM-DD');
                        });
                        //console.log('response', response);
                        //console.log('factory.usage', factory.usage);
                    },
                    function() {
                        NotificationFactory.addMessage(msgKey, errorMsg, 'danger');
                    });
        };

        factory.getDailyUsageUserBreakdown = function(params) {
            var msgKey = 'utilization';
            var errorMsg = 'There was an error loading daily usage.';
            return $http({
                    method: 'GET',
                    url: '/admin/usage/daily-usage-user-breakdown/',
                    params: params,
                    cache: 'true',
                })
                .then(function(response) {
                        factory.user_usage = response.data.result;
                        // TODO figure out how to sort by alpha
                        //factory.user_usage = _.sortBy(factory.user_usage, function(obj) {
                        //    return moment(obj.date, 'YYYY-MM-DD');
                        //});
                        //console.log('response', response);
                        //console.log('factory.user_usage', factory.user_usage);
                    },
                    function() {
                        NotificationFactory.addMessage(msgKey, errorMsg, 'danger');
                    });
        };

        factory.getDowntimes = function(params) {
            var msgKey = 'utilization';
            var errorMsg = 'There was an error loading downtimes.';
            return $http({
                    method: 'GET',
                    url: '/admin/usage/downtimes/',
                    params: params,
                    cache: 'true'
                })
                .then(function(response) {
                        factory.downtimes = response.data.result;
                        factory.downtimes = _.sortBy(factory.downtimes, function(obj) {
                            return moment(obj.date, 'YYYY-MM-DD');
                        });
                        //console.log('factory.downtimes', factory.downtimes);
                    },
                    function() {
                        NotificationFactory.addMessage(msgKey, errorMsg, 'danger');
                    });
        };
        return factory;
    }]);
