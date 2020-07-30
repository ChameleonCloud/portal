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
    const terms = filter.split(' ').filter(Boolean);
    document.querySelectorAll('.cardItem').forEach((el) => {
      const matches = terms.some((term) => {
        return (term.length > 2) && el.dataset.search.includes(term);
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
