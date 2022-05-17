'use strict';
(function( window, $, undefined ) {
  $('button[name="add_bulk_users_popup"]').on('click', function(e) {
    e.preventDefault()
    var $popup = $("#bulk_invite_popup");
    $popup.modal("show");
  });
})( this, $ );
