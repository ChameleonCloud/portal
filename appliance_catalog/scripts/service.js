'use strict';
angular
    .module('appCatalogApp.service')
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
            $rootScope.$broadcast('appliance:notifyLoading');
        };
        factory.removeLoading = function(resourceName) {
            delete loading[resourceName];
            $rootScope.$broadcast('appliance:notifyLoading');
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
            $rootScope.$broadcast('appliance:notifyMessage');
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
            $rootScope.$broadcast('appliance:notifyMessage');
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
            $rootScope.$broadcast('appliance:notifyMessage');
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

        factory.search = function(appliances, searchKey) {
            if (!searchKey) {
                return angular.copy(appliances);
            } else {
                return _.filter(appliances, function(appliance) {
                    searchKey = searchKey.toLowerCase();
                    var pass = false;
                    var name = appliance.name || '';
                    var description = appliance.description || '';
                    var author = appliance.author_name || '';
                    if (name.toLowerCase().indexOf(searchKey) > -1) {
                        pass = true;
                    } else if (description.toLowerCase().indexOf(searchKey) > -1) {
                        pass = true;
                    } else if (author.toLowerCase().indexOf(searchKey) > -1) {
                        pass = true;
                    }
                    return pass;
                });
            }
        };

        factory.updateFiltered = function(appliances, filteredAppliances, filter) {
            filteredAppliances = factory.search(appliances, filter.searchKey);
            return filteredAppliances;
        };

        return factory;
    }])
    .factory('ApplianceFactory', ['$http', '_', 'moment', 'NotificationFactory', function($http, _, moment, NotificationFactory) {
        var factory = {};
        factory.appliances = [];
        factory.appliance = null;
        factory.keywords = [];
        factory.getAppliances = function() {
            var errorMsg = 'There was an error loading appliance catalog.';
            NotificationFactory.clearMessages('appCatalog');
            NotificationFactory.addLoading('appCatalog');
            return $http({
                    method: 'GET',
                    url: '/appliance-catalog/api/appliances/',
                    cache: 'true'
                })
                .then(function(response) {
                        NotificationFactory.removeLoading('appCatalog');
                        factory.appliances = response.data.result;
                    },
                    function() {
                        NotificationFactory.addMessage('appCatalog', errorMsg, 'danger');
                        NotificationFactory.removeLoading('appCatalog');
                    });
        };
        factory.getKeywords = function() {
            var errorMsg = 'There was an error loading keywords.';
            NotificationFactory.clearMessages('keywords');
            NotificationFactory.addLoading('keywords');
            return $http({
                    method: 'GET',
                    url: '/appliance-catalog/api/keywords/',
                    cache: 'true'
                })
                .then(function(response) {
                        NotificationFactory.removeLoading('keywords');
                        var keywordsRaw = response.data.result;
                        for (var i in keywordsRaw){
                                factory.keywords.push({
                                    id: keywordsRaw[i].id,
                                    label: keywordsRaw[i].id
                                });
                            }
                    },
                    function() {
                        NotificationFactory.addMessage('keywords', errorMsg, 'danger');
                        NotificationFactory.removeLoading('keywords');
                    });
        };
        factory.getAppliance = function(appliance_id) {
            var errorMsg = 'There was an error loading this appliance.';
            NotificationFactory.clearMessages('appliance');
            NotificationFactory.addLoading('appliance');
            return $http({
                    method: 'GET',
                    url: '/appliance-catalog/api/appliances/' + appliance_id + '/',
                    cache: 'true'
                })
                .then(function(response) {
                        NotificationFactory.removeLoading('appliance');
                        factory.appliances = response.data;
                    },
                    function() {
                        NotificationFactory.addMessage('appliance', errorMsg, 'danger');
                        NotificationFactory.removeLoading('appliance');
                    });
        };
        return factory;
    }]);
