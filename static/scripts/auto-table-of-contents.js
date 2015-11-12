/*
 * Uses jQuery.TOC plugin to auto-enable a table of contents on a page if there is an
 * element with `data="enable-toc"` on the page.
 */
(function(window, $, undefined) {
  $(function() {
    var tocContent = $('.enable-toc');
    if (tocContent.length > 0) {
      var toggle = $('<button name="toggle-toc" class="btn-toggle-toc">');
      toggle.text('Toggle Table of Contents');
      toggle.on('click', function() {
        $('body').addClass('with-toc');
        $('<div id="toc">').appendTo('body').toc({
          'container': tocContent
        });
      });
      tocContent.prepend(toggle);
    }
  });
})(window, jQuery);