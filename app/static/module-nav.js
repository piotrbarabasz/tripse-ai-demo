/* Server-rendered hint only; /hub and Document Studio enforce access independently. */
(() => {
  const link = document.getElementById('hub-return');
  if (link && document.body.dataset.hubNavigation === 'enabled') link.hidden = false;
})();
