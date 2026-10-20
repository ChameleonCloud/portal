/*
 * Shows the Chameleon portal's site header on other sites (blog, docs, ...).
 *
 *   <script src="https://www.chameleoncloud.org/static/scripts/chameleon-header.js" defer></script>
 *   <chameleon-header>
 *     Optional fallback, shown until the header loads or if the portal is down.
 *   </chameleon-header>
 *
 * The site's origin must be listed in the portal's SITE_HEADER_ALLOWED_ORIGINS.
 *
 * The header is drawn inside a "shadow root", which stops the portal's CSS and
 * the host site's CSS from affecting each other.
 */

// The portal this script was loaded from, e.g. "https://www.chameleoncloud.org".
const PORTAL_URL = new URL(document.currentScript.src).origin;

class ChameleonHeader extends HTMLElement {
  // Runs when the <chameleon-header> tag is added to the page.
  async connectedCallback() {
    // Sending cookies lets the portal show the logged-in user's menu.
    const response = await fetch(`${PORTAL_URL}/header.html`, { credentials: "include" });
    if (!response.ok) return;

    // Links in the header are relative to the portal (e.g. "/login/"), so make them absolute.
    const html = (await response.text())
      .replaceAll('href="/', `href="${PORTAL_URL}/`)
      .replaceAll('src="/', `src="${PORTAL_URL}/`);

    // Fonts declared inside a shadow root are ignored, so the page has to load them.
    document.head.insertAdjacentHTML("beforeend", `
      <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@300;400;600&family=Inter:wght@400;500;600;700&display=swap">
      <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">`);

    // <slot> keeps showing the fallback while the portal's stylesheet loads, so the
    // header never appears unstyled. The :host style stops the page's fonts leaking in.
    const root = this.attachShadow({ mode: "open" });
    root.innerHTML = `
      <style>:host { display: block; font: 16px/1.6 "Source Sans Pro", Helvetica, sans-serif; color: #333; }</style>
      <link rel="stylesheet" href="${PORTAL_URL}/static/styles/main.css">
      <slot></slot>
      <div hidden>${html}</div>`;
    await new Promise((resolve) => root.querySelector("link").addEventListener("load", resolve));
    root.querySelector("slot").remove();
    root.querySelector("div[hidden]").hidden = false;

    // Bootstrap's JavaScript can't see inside the shadow root, so the mobile menu
    // button and the dropdown menus are handled here instead.
    root.addEventListener("click", (event) => {
      if (event.target.closest(".navbar-toggle")) {
        root.querySelector(".navbar-collapse").classList.toggle("in");
      }

      const dropdownToggle = event.target.closest(".dropdown-toggle");
      if (dropdownToggle) {
        event.preventDefault();
        const dropdown = dropdownToggle.parentElement;
        const wasOpen = dropdown.classList.contains("open");
        this.closeDropdowns();
        if (!wasOpen) dropdown.classList.add("open");
      }
    });

    // Clicking anywhere else on the page closes open dropdowns. (To the page, a
    // click inside the header looks like a click on <chameleon-header> itself.)
    document.addEventListener("click", (event) => {
      if (event.target !== this) this.closeDropdowns();
    });
  }

  closeDropdowns() {
    this.shadowRoot.querySelectorAll(".dropdown.open").forEach((dropdown) => dropdown.classList.remove("open"));
  }
}

customElements.define("chameleon-header", ChameleonHeader);
