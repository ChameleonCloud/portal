'use strict';
/*global $ */
var app = angular.module('allocationsApp');
app.directive('readMore', function() {
  return {
    restrict: 'A',
    transclude: true,
    replace: true,
    template: '<p></p>',
    scope: {
      moreText: '@',
      lessText: '@',
      words: '@',
      ellipsis: '@',
      char: '@',
      limit: '@',
      content: '@',
      textData: '@'
    },
    link: function(scope, elem, attr) {
      var moreText = angular.isUndefined(scope.moreText) ? ' <a class="read-more">Read More...</a>' : ' <a class="read-more">' + scope.moreText + '</a>',
        lessText = angular.isUndefined(scope.lessText) ? ' <a class="read-less">Less ^</a>' : ' <a class="read-less">' + scope.lessText + '</a>',
        ellipsis = angular.isUndefined(scope.ellipsis) ? '' : scope.ellipsis,
        limit = angular.isUndefined(scope.limit) ? 50 : scope.limit,
        textData = angular.isUndefined(scope.textData) ? '' : scope.textData.trim();

      function readmore() {
          var orig = textData,
          regex = /\s+/gi,
          charCount = textData.length,
          wordCount = textData.trim().replace(regex, ' ').split(' ').length,
          countBy = 'char',
          count = charCount,
          foundWords = [],
          markup = textData,
          more = '';

        if (!angular.isUndefined(attr.words)) {
          countBy = 'words';
          count = wordCount;
        }

        if (countBy === 'words') { // Count words

          foundWords = textData.split(/\s+/);

          if (foundWords.length > limit) {
            textData = foundWords.slice(0, limit).join(' ') + ellipsis;
            more = foundWords.slice(limit, count).join(' ');
            markup = textData + moreText + '<span class="more-text">' + more + lessText + '</span>';
          }

        } else { // Count characters

          if (count > limit) {
            textData = orig.slice(0, limit) + ellipsis;
            more = orig.slice(limit, count);
            markup = textData + moreText + '<span class="more-text">' + more + lessText + '</span>';
          }

        }

        elem.append(markup);
        elem.find('.more-text').hide().removeClass('show-inline');
        elem.find('.read-more').on('click', function() {
          $(this).hide();
          elem.find('.more-text').addClass('show-inline').slideDown();
        });
        elem.find('.read-less').on('click', function() {
          elem.find('.read-more').show();
          elem.find('.more-text').hide().removeClass('show-inline');
        });

      }
      readmore();
    }
  };
});

app.directive('autodismiss',function($timeout){
    return {
        link:function(scope, element, attrs){         
          var duration = 7000;
          if(attrs.autodismiss){
            duration = parseInt(attrs.autodismiss);
          }
          attrs.$observe('trShow', function(){
            if(scope.$eval(attrs.trShow) === true){             
              $timeout(function(){                 
                 element.fadeOut(1000);
                }, duration);
            }
          });
           
        }
      };
    });