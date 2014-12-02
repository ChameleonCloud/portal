'use strict';
(function ( window, $, undefined ) {
  var fgAddUserURL = $( 'input[name="fg_add_user_url"]' ).val();

  $( 'form[name="fg-user-add"]' ).on('submit', function( e ) {
    e.preventDefault();
    var form = $( this );
    var data = form.serialize();

    $.ajax({
      url: fgAddUserURL,
      type: 'post',
      data: data
    })
    .done(function( resp ) {
      if ( resp.status === 'success' ) {
        /* TODO: just refresh the page for now */
        window.location.reload();
      } else {
        if ( resp.result.error === 'user_not_found' ) {
          form.after( '<a class="btn btn-default btn-sm" href="mailto:' + form[0].email.value + '"><i class="fa fa-envelope"></i> Invite User</a>' );
        }
        form.after( '<p class="text-danger">' + resp.message + '</p>' );
        form.remove();
      }
    })
    .fail(function() {
      window.alert( 'An unexpected error occurred! Please try again.' );
    });
  });

})( this, $ );
