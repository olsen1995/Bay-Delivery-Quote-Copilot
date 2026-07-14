(() => {
  "use strict";

  const root = document.documentElement;
  const menuToggle = document.querySelector("[data-public-menu-toggle]");
  const mobileNav = document.querySelector("[data-public-menu]");
  const publicLogo = document.querySelector("[data-public-shell-logo]");

  if (!menuToggle || !mobileNav || !publicLogo) return;

  const desktopQuery = window.matchMedia("(min-width: 1180px)");
  let mobileControlHadFocus = false;

  const setMenuState = (isOpen) => {
    mobileNav.hidden = !isOpen;
    mobileNav.dataset.state = isOpen ? "open" : "closed";
    menuToggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
    if (isOpen) {
      menuToggle.setAttribute("aria-label", "Close navigation menu");
    } else {
      menuToggle.setAttribute("aria-label", "Open navigation menu");
    }
  };

  const moveFocusToLogo = () => {
    publicLogo.focus({ preventScroll: true });
    mobileControlHadFocus = false;
  };

  setMenuState(false);

  menuToggle.addEventListener("click", () => {
    const isOpen = menuToggle.getAttribute("aria-expanded") === "true";
    setMenuState(!isOpen);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    if (menuToggle.getAttribute("aria-expanded") !== "true") return;
    menuToggle.focus({ preventScroll: true });
    setMenuState(false);
  });

  mobileNav.addEventListener("click", (event) => {
    const link = event.target.closest("a");
    if (!link || !mobileNav.contains(link)) return;
    moveFocusToLogo();
    setMenuState(false);
  });

  document.addEventListener("focusin", (event) => {
    if (event.target === menuToggle || mobileNav.contains(event.target)) {
      mobileControlHadFocus = true;
      return;
    }
    if (event.target !== document.body && event.target !== root) {
      mobileControlHadFocus = false;
    }
  });

  desktopQuery.addEventListener("change", (event) => {
    if (!event.matches) return;
    if (
      document.activeElement === menuToggle ||
      mobileNav.contains(document.activeElement) ||
      mobileControlHadFocus
    ) {
      moveFocusToLogo();
    }
    setMenuState(false);
  });

  menuToggle.hidden = false;
  root.classList.replace("bd-no-js", "bd-js");
})();
