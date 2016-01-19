'use strict';
(function( window, $, undefined ) {
    $('button[name="allocation-display-toggle"]').on('click', function(e) {
      e.preventDefault();
      $('.allocation').toggleClass('show');
    });

    if ($('.allocation-active').length != 0 || $('.allocation-pending').length != 0) {
            $('.allocation-rejected').toggleClass('hide');
    }
})( this, $ );