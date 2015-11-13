/*
 * Uses jQuery.TOC plugin to auto-enable a table of contents on a page if there is an
 * element with `data="enable-toc"` on the page.
 */
(function(window, $, undefined) {
  $(function() {
    var tocContent = $('.enable-toc');
    if (tocContent.length > 0) {
      $('body').addClass('with-toc');

      var firstHeader = $('h1,h2,h3,h4,h5,h6', tocContent).eq(0);
      var el = $('<div id="toc">')
      firstHeader.after(el);
      el.toc({
        'container': tocContent
      });

      var toggle = $('<button name="toc-toggle" class="toc-toggle">');
      toggle.html('<span>Table of Contents</span>');
      firstHeader.after(toggle);
      toggle.on('click', function() {
        $('body').toggleClass('with-toc');
      });
    }
  });
})(window, jQuery);