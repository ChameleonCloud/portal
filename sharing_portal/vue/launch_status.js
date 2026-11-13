const ACTIVE = ['pending', 'running'];

function ready(fn) {
  if (document.readyState != 'loading') {
    fn();
  } else {
    document.addEventListener('DOMContentLoaded', fn);
  }
}

ready(() => {
  document.querySelectorAll('[data-copy]').forEach((button) => {
    button.addEventListener('click', async () => {
      await navigator.clipboard.writeText(button.dataset.copy);
      button.textContent = 'Copied';
      setTimeout(() => {
        button.textContent = 'Copy';
      }, 2000);
    });
  });

  const root = document.getElementById('launchStatus');
  if (!root || !ACTIVE.includes(root.dataset.status)) {
    return;
  }

  // The page is rendered server-side, so reload it whenever the launch changes
  const poll = async () => {
    try {
      const response = await fetch(root.dataset.statusUrl, {
        headers: { Accept: 'application/json' },
      });
      const launch = await response.json();
      if (
        launch.status !== root.dataset.status ||
        launch.events.length !== Number(root.dataset.events)
      ) {
        window.location.reload();
        return;
      }
    } catch (e) {
      // Retry on the next tick
    }
    setTimeout(poll, 5000);
  };
  setTimeout(poll, 5000);
});
