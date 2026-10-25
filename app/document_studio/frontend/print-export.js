/* Trusted pagination and browser export. No user-supplied code is evaluated. */
window.documentReady = false;
window.layoutErrors = [];
const pageRoot = document.querySelector('#pages');
function newPage() {
  const wrap = document.querySelector('#page-template').content.firstElementChild.cloneNode(true);
  pageRoot.append(wrap);
  return wrap.querySelector('.page-body');
}
function fits(body) { return body.scrollHeight <= body.clientHeight + 1; }
function fitPreview() {
  const width = document.body.classList.contains('format-social') ? 1080 : 794;
  const height = document.body.classList.contains('format-social') ? 1350 : 1122;
  const scale = Math.min(1, Math.max(200, document.documentElement.clientWidth - 24) / width);
  document.querySelectorAll('.sheet-wrap').forEach(wrap => {
    wrap.style.width = width * scale + 'px'; wrap.style.height = height * scale + 'px';
    wrap.firstElementChild.style.transform = `scale(${scale})`;
  });
}
async function prepareDocument() {
  await document.fonts.ready;
  // Load images while source blocks are hidden, before measuring pagination.
  const blocks = [...document.querySelector('#source-blocks').children];
  let body = newPage();
  for (const block of blocks) {
    body.append(block);
    if (!fits(body) && body.children.length > 1) {
      body.removeChild(block);
      const previous = body;
      body = newPage();
      // Keep a final CTA or closing note with context when both fit on a page.
      const keepWithPrevious = block.classList.contains('cta') || block.classList.contains('keep-with-previous');
      if (keepWithPrevious && previous.lastElementChild) {
        body.append(previous.lastElementChild);
      }
      body.append(block);
      if (!fits(body) && keepWithPrevious && body.children.length === 2) {
        previous.append(body.firstElementChild);
      }
    }
    if (!fits(body)) {block.classList.add('compact');}
    if (!fits(body)) window.layoutErrors.push('Karta zawiera zbyt dużo treści na jedną stronę. Skróć opis lub wyróżniki.');
  }
  const images = [...pageRoot.querySelectorAll('img')];
  await Promise.all(images.map(img => img.decode().catch(() => {window.layoutErrors.push('Nie udało się wczytać zdjęcia.');})));
  const pages = [...document.querySelectorAll('.sheet')];
  pages.forEach((sheet, i) => sheet.querySelector('.page-number').textContent = `${i + 1} / ${pages.length}`);
  fitPreview();
  const valid = document.body.dataset.valid === 'true' && !window.layoutErrors.length;
  document.body.classList.toggle('layout-error', !!window.layoutErrors.length);
  document.querySelector('#print-document').disabled = !valid;
  document.querySelector('#layout-status').textContent = window.layoutErrors.join(' ') || (valid ? `Gotowe · ${pages.length} str. W druku wybierz „Zapisz jako PDF”, skalę 100%, bez nagłówków przeglądarki.` : 'Eksport zablokowany: sprawdź uwagi do dokumentu.');
  window.documentReady = true;
}
document.querySelector('#print-document').addEventListener('click', () => {
  if (window.documentReady && !window.layoutErrors.length && document.body.dataset.valid === 'true') window.print();
});
window.addEventListener('resize', fitPreview);
prepareDocument().catch(() => {document.body.classList.add('layout-error');document.querySelector('#layout-status').textContent='Nie udało się przygotować podglądu.';});
