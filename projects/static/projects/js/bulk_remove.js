'use strict';
(function( window, $, undefined ) {
  $('button[name="remove_bulk_users_popup"]').on('click', function(e) {
    e.preventDefault();
    var $popup = $("#bulk_remove_popup");
    $popup.modal("show");
  });
})( this, $ );
