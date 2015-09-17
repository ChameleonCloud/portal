'use strict';
(function( window, $, undefined ) {
    $('button[name="allocation-display-toggle"]').on('click', function(e) {
      e.preventDefault();
      $('.allocation').toggleClass('show');
    });
})( this, $ );