if (document.readyState !== 'loading') {
    $('[data-toggle=tooltip]').tooltip();
} else {
    document.addEventListener('DOMContentLoaded', function () {
        $('[data-toggle=tooltip]').tooltip();
    });
}
