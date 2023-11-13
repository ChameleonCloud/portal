(function() {
  document.addEventListener('DOMContentLoaded', () => {
    const filterInput = document.getElementById('cardFilter');

    if (filterInput) {
      filterInput.addEventListener('keyup', onFilterChange);
    }

    const queryParams = new URLSearchParams(window.location.search);
    const filter = queryParams.get('filter')
    if (filter) {
      applyQueryFilter(filter);
      if (filterInput) {
        filterInput.value = filter;
      }
    }
  });

  function onFilterChange(e) {
    applyQueryFilter(e.target.value);
  }

  function applyQueryFilter(filter) {
    const terms = filter.split(' ').filter((term) => term.length > 2).map((term) => term.toLowerCase());
    document.querySelectorAll('.cardItem').forEach((el) => {
      const matches = terms.every((term) => {
        return el.dataset.search.includes(term);
      });
      el.classList.toggle('hidden', terms.length > 0 && !matches);
    });

    if (history.replaceState) {
      const queryParams = new URLSearchParams(window.location.search);
      queryParams.set('filter', filter);
      history.replaceState(null, '', '?' + queryParams.toString());
    }
  }
})();

function filter_artifacts(badge_filter) {
  const filterInput = document.getElementById('cardFilter');
  filterInput.value = ""; // reset the value in field
  filterInput.value = badge_filter;
  filterInput.dispatchEvent(new KeyboardEvent('keyup')); // trigger a keyup to apply filter
}
