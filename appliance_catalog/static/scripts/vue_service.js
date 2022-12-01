
export class NotificationFactory {

    constructor($rootScope, $timeout, _) {
        this.$rootScope = $rootScope;
        this.$timeout = $timeout;
        this.factory = {};
        this.loading = {};
        this.messages = {};
        this.factory.uuid = function () {
            /* jshint bitwise: false */
            return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
                let r = Math.random() * 16 | 0,
                    v = c === 'x' ? r : (r & 0x3 | 0x8);
                return v.toString(16);
            });
            /* jshint bitwise: true */
        };
        this.factory.addLoading = function (resourceName) {
            this.loading[resourceName] = true;
            this.$rootScope.$broadcast('appliance:notifyLoading');
        };
        this.factory.removeLoading = function (resourceName) {
            delete this.loading[resourceName];
            $rootScope.$broadcast('appliance:notifyLoading');
        };
        this.factory.get.this.messages = function () {
            return this.messages;
        };
        this.factory.getLoading = function () {
            return this.loading;
        };
        this.factory.clear.this.messages = function (key) {
            key = key || 'all';
            if (key === 'all') {
                this.messages = {};
            } else {
                this.messages[key] = [];
            }
            $rootScope.$broadcast('appliance:notifyMessage');
        };
        this.factory.removeMessage = function (key, messageObj, id) {
            if (typeof id !== 'undefined') {
                key = key + id;
            }
            let msgs = this.messages[key];
            if (!msgs || msgs.length < 1) {
                return;
            }
            this.messages[key] = _.reject(msgs, function (m) {
                return m._id === messageObj._id;
            });
            $rootScope.$broadcast('appliance:notifyMessage');
        };
        this.factory.addMessage = function (key, message, type) {
            let messageObj = {};
            messageObj.body = message;
            messageObj.type = type;
            messageObj._id = this.factory.uuid();
            if (typeof this.messages[key] === 'undefined') {
                this.messages[key] = [];
            }
            this.messages[key].push(messageObj);
            $rootScope.$broadcast('appliance:notifyMessage');
            let duration = messageObj.type === 'danger' ? 0 : 5000;
            if (duration > 0) {
                this.$timeout(function () {
                    this.factory.removeMessage(key, messageObj);
                }, duration);
            }
        }
    }

    getAll() {
        return this.factory;
    }

}


// export class UtilFactory {
//
//
// }

export class ApplianceFactory {

    constructor($http, _, moment, NotificationFactory, djangoUrl) {
        this.$http = $http;
        this.moment = moment;
        this.NotificationFactory = NotificationFactory;
        this.djangoUrl = djangoUrl;
        this.factory = {}
        this.factory.appliances = [];
        this.factory.appliance = null;
        this.factory.keywords = [];
        this.getAppliances = function(keywords) {
            let url = djangoUrl.reverse('appliance_catalog:get_appliances');

            if(keywords){
                url += '&';
                for(let i in keywords){
                    url += 'keywords=' +keywords[i].id;
                    if(i < keywords.length-1){
                        url += '&';
                    }
                }
            }
            let errorMsg = 'There was an error loading appliance catalog.';
            NotificationFactory.clearMessages('appCatalog');
            NotificationFactory.addLoading('appCatalog');
            return $http({
                method: 'GET',
                url: url,
                cache: 'true'
            })
                .then(function(response) {
                        NotificationFactory.removeLoading('appCatalog');
                        this.factory.appliances = response.data.result;
                    },
                    function() {
                        NotificationFactory.addMessage('appCatalog', errorMsg, 'danger');
                        NotificationFactory.removeLoading('appCatalog');
                    });
        };
        this.factory.getKeywords = function() {
            let errorMsg = 'There was an error loading keywords.';
            NotificationFactory.clearMessages('keywords');
            NotificationFactory.addLoading('keywords');
            return $http({
                method: 'GET',
                url: djangoUrl.reverse('appliance_catalog:get_keywords'),
                cache: 'true'
            })
                .then(function (response) {
                        NotificationFactory.removeLoading('keywords');
                        let keywordsRaw = response.data.result;
                        for (let i in keywordsRaw) {
                            this.factory.keywords.push({
                                id: keywordsRaw[i].id,
                                label: keywordsRaw[i].id
                            });
                        }
                    },
                    function () {
                        NotificationFactory.addMessage('keywords', errorMsg, 'danger');
                        NotificationFactory.removeLoading('keywords');
                    });
        };
        this.factory.getAppliance = function(appliance_id) {
            var errorMsg = 'There was an error loading this appliance.';
            NotificationFactory.clearMessages('appliance');
            NotificationFactory.addLoading('appliance');
            return $http({
                method: 'GET',
                url: djangoUrl.reverse('appliance_catalog:get_appliance', [appliance_id]),
                cache: 'true'
            })
                .then(function (response) {
                        NotificationFactory.removeLoading('appliance');
                        this.factory.appliances = response.data.result;
                    },
                    function () {
                        NotificationFactory.addMessage('appliance', errorMsg, 'danger');
                        NotificationFactory.removeLoading('appliance');
                    });
        };
    }

    getAll() {
        return this.factory;
    }
}