'use strict';
(function( window, $, undefined ) {
    var used = parseInt($("#progressbar").attr("used"));
    console.log(used);
    $( "#progressbar" ).progressbar({
        max: 20000,
        value: used
    });
})( this, $ );