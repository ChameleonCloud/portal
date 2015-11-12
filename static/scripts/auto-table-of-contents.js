/*
 * Uses jQuery.TOC plugin to auto-enable a table of contents on a page if there is an
 * element with `data="enable-toc"` on the page.
 */
(function(window, $, undefined) {
  $(function() {
    var tocContent = $('.enable-toc');
    if (tocContent.length > 0) {
      $('body').addClass('with-toc');
      $('<div id="toc">').appendTo('body').toc({
        'container': tocContent
      });
      var toggle = $('<button name="toc-toggle" class="toc-toggle">');
      toggle.html('<span>Table of Contents</span>');
      tocContent.prepend(toggle);
      toggle.on('click', function() {
        $('body').toggleClass('with-toc');
      });
    }
  });
})(window, jQuery);