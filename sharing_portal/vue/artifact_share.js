/**
 * TODO(jason): this should ideally be using the VueJS framework, which has much
 * better support for more rich interactivity in forms and whatnot. However,
 * it is really difficult to get Vue to just bind to existing DOM structures
 * and not try to re-render everything. This wouldn't normally be such a big
 * deal, but Django needs to be rendering things like the forms in the HTML
 * template outputted by the server.
 *
 * One eventual solution might be to somehow serialize the Django form in JSON
 * and then rebuild it client-side along with whatever else is needed. That
 * requires additional plumbing and I'm unaware of any solid libraries that
 * can assist with that, oddly.
 */

function ready(fn) {
  if (document.readyState != 'loading'){
    fn();
  } else {
    document.addEventListener('DOMContentLoaded', fn);
  }
}

ready(() => {
  const form = document.getElementById('artifactShareForm');

  if (!form) {
    return
  }

  form.addEventListener('submit', (event) => {
    const formData = new FormData(event.target)
    for (var pair of formData.entries()) {
      if (pair[0].indexOf('request_doi') === 0 && pair[1] == 'on') {
        if (! confirm(['Are you sure you want to request a DOI? ',
                      'This will make this version of your ',
                      'artifact publicly available on ',
                      'Zenodo: https://zenodo.org.'].join(''))) {
          event.preventDefault();
        }
        return;
      }
    }
  });

  function togglePrivateShareOptions(on) {
    form.querySelector('#artifactShareFormPrivateOptions')
        .classList.toggle('hidden', !on)
  }

  togglePrivateShareOptions(!form.querySelector('[name=is_public]').checked)
  form.addEventListener('change', (event) => {
    if (event.target.name === 'is_public') {
      togglePrivateShareOptions(!event.target.checked)
    }
  });
});
