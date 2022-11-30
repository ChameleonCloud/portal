/**
 * author agauli
 */
'use strict';
angular.module('appCatalogApp')
  .controller('AppCatalogController', ['$scope', '$http', '$timeout', 'moment', '_', 'UtilFactory', 'ApplianceFactory', 'NotificationFactory',
    function ($scope, $http, $timeout, moment, _, UtilFactory, ApplianceFactory, NotificationFactory) {
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

      $scope.viewType = 'grid';

      $scope.filterInit = function () {
        $scope.filter = {
          selectedKeywords: [],
          searchKey: '',
          andSearch: true,
          project_supported: false
        };
      };
      $scope.filterInit();

      $scope.sortAppliances = function (predicate) {
        if ($scope.reverse) {
          $scope.filteredAppliances = _.sortBy($scope.filteredAppliances, function (app) {
            return app[predicate].toLowerCase();
          });
        }
        else {
          $scope.filteredAppliances = _.sortBy($scope.filteredAppliances, function (app) {
            return app[predicate].toLowerCase();
          }).reverse();
        }
      };

      $scope.appsPageChanged = function (pageNum) {
        var startIndex = (pageNum - 1) * $scope.appsPerPage;
        var endIndex = startIndex + $scope.appsPerPage;
        if (endIndex > ($scope.filteredAppliances.length - 1)) {
          endIndex = $scope.filteredAppliances.length;
        }
        $scope.appsThisPage = $scope.filteredAppliances.slice(startIndex, endIndex);
      };

      $scope.setupPagination = function () {
        $scope.appsPerPage = 16;
        $scope.totalPages = Math.ceil($scope.filteredAppliances.length / $scope.appsPerPage);
        $scope.appsCurrentPage = 1;
        $scope.appsPageChanged($scope.appsCurrentPage);
      };

      $scope.reset = function () {
        $scope.filterInit();
        $scope.filteredAppliances = angular.copy($scope.appliances);
        $scope.orderInit();
        $scope.sortAppliances($scope.predicate);
        $scope.setupPagination();
      };

      $scope.orderInit = function () {
        $scope.predicate = 'name';
        $scope.reverse = true;
      };

      $scope.orderInit();
      $scope.appliances = [];
      $scope.filteredAppliances = [];

      $scope.getAppliances = function () {
        ApplianceFactory.getAppliances().then(function () {
          $scope.appliances = angular.copy(ApplianceFactory.appliances);
          $scope.filteredAppliances = angular.copy(ApplianceFactory.appliances);
          $scope.sortAppliances($scope.predicate);
          $scope.setupPagination();
        });
      };

      $scope.getAppliances();

      $scope.getKeywords = function () {
        $scope.keywords = [];
        ApplianceFactory.getKeywords().then(function () {
          $scope.keywords = ApplianceFactory.keywords;
        });
      };

      $scope.getKeywords();

      $scope.getPageIndex = function () {
        var x = ($scope.appsCurrentPage - 1) * $scope.appsPerPage + 1;
        var y = ($scope.appsCurrentPage * $scope.appsPerPage < $scope.filteredAppliances.length) ? $scope.appsCurrentPage *
        $scope.appsPerPage : $scope.filteredAppliances.length;
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


      $scope.viewDetail = function(appId) {
        window.location = appId + '/';
      };

      $scope.multiselectCustomTexts = {
        buttonDefaultText: 'Search by keywords'
      };

      /**
       * Updated the search filters applied to the list of applications.
       */
      $scope.updateFiltered = function () {
        /* reset filtered list to entire list */
        $scope.filteredAppliances = ApplianceFactory.appliances;

        /* first, filter the list by keyword matches */
        if ($scope.filter.selectedKeywords && $scope.filter.selectedKeywords.length > 0) {

          $scope.filteredAppliances = _.filter($scope.filteredAppliances, function(a) {

            if ($scope.filter.andSearch) {
              /* for AND searches, applications must match EVERY selected keyword */
              return _.every($scope.filter.selectedKeywords, function(keyword) {
                return _.contains(a.keywords, keyword.id);
              });
            } else {
              /* for OR searches, applications can match ANY selected keyword */
              return _.some($scope.filter.selectedKeywords, function(keyword) {
                return _.contains(a.keywords, keyword.id);
              });
            }
          });
        }

        /* second, filter the list according to simple phrase matching on name, description, author */
        if ($scope.filter.searchKey) {
          $scope.filteredAppliances = UtilFactory.search($scope.filteredAppliances, $scope.filter.searchKey);
        }

        if ($scope.filter.project_supported) {
          $scope.filteredAppliances = UtilFactory.filterProjectSupported($scope.filteredAppliances);
        }

        $scope.sortAppliances($scope.predicate);
        $scope.setupPagination();
      };

      // list view ordering

      $scope.changeOrder = function (predicate) {
        if ($scope.predicate === predicate) {
          $scope.reverse = !$scope.reverse;
        }
        else {
          $scope.predicate = predicate;
        }
        $scope.sortAppliances(predicate);
        $scope.setupPagination();
      };

      $scope.changeViewType = function () {
        if ($scope.viewType === 'grid') {
          $scope.viewType = 'table';
        }
        else {
          $scope.viewType = 'grid';
        }
      };

    }]);
