/* Convenience only; /hub and Document Studio always enforce access on the server. */
(() => {
  const link = document.getElementById('hub-return');
  if (link && ['localhost', '127.0.0.1', '[::1]'].includes(location.hostname)) link.hidden = false;
})();
