(() => {
  const actions = document.querySelector(".homeMobileActions");
  const hero = document.querySelector(".homeHero");
  const footer = document.querySelector('[data-public-shell="footer"]');

  const hideActions = () => {
    if (actions) actions.hidden = true;
    document.body.classList.remove("homeMobileActionsVisible");
  };

  if (
    !actions ||
    !hero ||
    !footer ||
    typeof window.matchMedia !== "function" ||
    typeof window.requestAnimationFrame !== "function"
  ) {
    hideActions();
    return;
  }

  const mobileQuery = window.matchMedia("(max-width: 720px)");
  const supportsModernQueryListener = typeof mobileQuery.addEventListener === "function";
  const supportsLegacyQueryListener = typeof mobileQuery.addListener === "function";
  let scheduledFrame = null;

  if (!supportsModernQueryListener && !supportsLegacyQueryListener) {
    hideActions();
    return;
  }

  const updateActions = () => {
    scheduledFrame = null;
    const heroHasLeftViewport = hero.getBoundingClientRect().bottom <= 0;

    if (!mobileQuery.matches || !heroHasLeftViewport) {
      hideActions();
      return;
    }

    actions.hidden = false;
    document.body.classList.add("homeMobileActionsVisible");

    const actionHeight = actions.getBoundingClientRect().height;
    const footerTop = footer.getBoundingClientRect().top;
    if (footerTop <= window.innerHeight + actionHeight) {
      hideActions();
    }
  };

  const scheduleUpdate = () => {
    if (scheduledFrame !== null) return;
    scheduledFrame = window.requestAnimationFrame(updateActions);
  };

  window.addEventListener("scroll", scheduleUpdate, { passive: true });
  window.addEventListener("resize", scheduleUpdate);
  window.addEventListener("orientationchange", scheduleUpdate);
  if (supportsModernQueryListener) {
    mobileQuery.addEventListener("change", scheduleUpdate);
  } else {
    mobileQuery.addListener(scheduleUpdate);
  }

  scheduleUpdate();
})();
