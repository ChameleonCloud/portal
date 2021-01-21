'use strict';
angular
    .module('allocationsApp.service')
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
            } else if (status === 'active') {
                return 'label label-success';
            } else if (status === 'rejected') {
                return 'label label-danger';
            } else {
                return 'label label-default';
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
                        allocation.doNotShow = false;
                        var status = allocation.status.toLowerCase();
                        if (_.contains(chosenStatusFilters, status)) {
                            pass = true;
                        } else {
                            allocation.doNotShow = true;
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
        factory.getUserAllocations = function(username) {
            var errorMsg = 'There was an error loading allocations.';
            NotificationFactory.clearMessages('userAllocations');
            NotificationFactory.addLoading('userAllocations');
            return $http({
                    method: 'GET',
                    url: '/admin/allocations/user/' + username,
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

        factory.rejectAllocation = function(data) {
            var msgKey = 'rejectAllocation' + data.id;
            var errorMsg = 'There was an error rejecting this allocation. Please try again or file a ticket if this seems persistent.';
            NotificationFactory.clearMessages(msgKey);
            NotificationFactory.addLoading(msgKey);
            return $http({
                        method: 'POST',
                        url: '/admin/allocations/approval/',
                        data: data
                    })
                    .then(function(response) {
                            NotificationFactory.removeLoading(msgKey);
                            if (response.data.status === 'error') {
                                 NotificationFactory.addMessage(msgKey, errorMsg, 'danger');
                                 return null;
                            } else {
                                 NotificationFactory.addMessage(msgKey, 'This allocation request is rejected successfully.', 'success');
                                 return response.data.result;
                            }
                        },
                        function() {
                            NotificationFactory.removeLoading(msgKey);
                            NotificationFactory.addMessage(msgKey, errorMsg, 'danger');
                        });
        };
        factory.approveAllocation = function(data) {
            var msgKey = 'approveAllocation' + data.id;
            var errorMsg = 'There was an error approving this allocation. Please try again or file a ticket if this seems persistent.';
            NotificationFactory.clearMessages(msgKey);
            NotificationFactory.addLoading(msgKey);
            return $http({
                        method: 'POST',
                        url: '/admin/allocations/approval/',
                        data: data
                    })
                    .then(function(response) {
                            NotificationFactory.removeLoading(msgKey);
                            if (response.data.status === 'error') {
                                NotificationFactory.addMessage(msgKey, errorMsg, 'danger');
                                return null;
                            } else {
                                NotificationFactory.addMessage(msgKey, 'This allocation request is approved successfully.', 'success');
                                return response.data.result;
                            }
                        },
                        function() {
                            NotificationFactory.removeLoading(msgKey);
                            NotificationFactory.addMessage(msgKey, errorMsg, 'danger');
                        });
        };

        return factory;
    }]);
