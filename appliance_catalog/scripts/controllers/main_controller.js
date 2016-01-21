/**
 * author agauli
 */
'use strict';
angular.module('appCatalogApp')
    .controller('AppCatalogController', ['$scope', '$http', '$timeout', 'moment', '_', 'UtilFactory', 'ApplianceFactory', 'NotificationFactory', function ($scope, $http, $timeout, moment, _, UtilFactory, ApplianceFactory, NotificationFactory) {
        $scope.messages = [];
        $scope.$on('appliance:notifyMessage', function () {
            $scope.messages = NotificationFactory.getMessages();
        });
        $scope.loading = {};
        $scope.$on('appliance:notifyLoading', function () {
            $scope.loading = NotificationFactory.getLoading();
        });
        $scope.close = UtilFactory.closeMessage;
        $scope.isEmpty = UtilFactory.isEmpty;
        $scope.hasMessage = UtilFactory.hasMessage;
        $scope.isLoading = UtilFactory.isLoading;
        $scope.getMessages = UtilFactory.getMessages;
        $scope.getClass = UtilFactory.getClass;
        $scope.filter = {
            active: false,
            inactive: false,
            pending: false,
            rejected: false,
            search: ''
        };

         $scope.reset = function(){
             $scope.filter = {
                selectedKeywords: [],
                searchKey: '',
                searchType: 'and'
            };
         };
        $scope.reset();

        var setupPagination = function () {
            $scope.appsPerPage = 15;
            $scope.totalPages = Math.ceil($scope.filteredAppliances.length / $scope.appsPerPage);
            $scope.appsCurrentPage = 1;
            $scope.appsPageChanged($scope.appsCurrentPage);
        };
        $scope.appsPageChanged = function (pageNum) {
            var startIndex = (pageNum - 1) * $scope.appsPerPage;
            var endIndex = startIndex + $scope.appsPerPage;
            if (endIndex > ($scope.filteredAppliances.length - 1)) {
                endIndex = $scope.filteredAppliances.length;
            }
            $scope.appsThisPage = $scope.filteredAppliances.slice(startIndex, endIndex);
        };

        $scope.appliances = [];
        $scope.filteredAppliances = [];
        $scope.getAppliances = function () {
            ApplianceFactory.getAppliances().then(function () {
                $scope.appliances = ApplianceFactory.appliances;
                $scope.filteredAppliances = angular.copy($scope.appliances);
                setupPagination();
            });
        };
        $scope.getAppliances();

        $scope.getKeywords = function () {
            $scope.keywords = [];
            ApplianceFactory.getKeywords().then(function () {
                $scope.keywords = ApplianceFactory.keywords;
                console.log('$scope.keywords', $scope.keywords);
            });
        };
        $scope.getKeywords();

        $scope.getPageIndex = function () {
            var x = ($scope.appsCurrentPage - 1) * $scope.appsPerPage + 1;
            var y = ($scope.appsCurrentPage * $scope.appsPerPage < $scope.filteredAppliances.length) ? $scope.appsCurrentPage * $scope.appsPerPage : $scope.filteredAppliances.length;
            return x + '-' + y;
        };
        $scope.multiselectSettings = {
            smartButtonMaxItems: 15,
            scrollableHeight: '400px',
            scrollable: true,
            enableSearch: true,
            smartButtonTextConverter: function (itemText) {
                if (itemText.length > 20) {
                    return itemText.substring(0, 17) + '...';
                }

                return itemText;
            }
        };
        $scope.multiselectCustomTexts = {
            buttonDefaultText: 'Search by keywords'
        };
        $scope.updateFiltered = function () {
            console.log($scope.filter);
            $scope.filteredAppliances = UtilFactory.updateFiltered($scope.appliances, $scope.filteredAppliances, $scope.filter);
            setupPagination();
        };

    }]);
