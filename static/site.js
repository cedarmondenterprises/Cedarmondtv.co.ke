(() => {
  const copy = document.querySelector('#copy-link');
  const status = document.querySelector('#share-status');
  copy?.addEventListener('click', async () => {
    try { await navigator.clipboard.writeText(location.href); status.textContent = 'Link copied.'; }
    catch { status.textContent = 'Copy the address from your browser.'; }
  });
  const save = document.querySelector('#save-story');
  if (save) {
    const key = 'cedarmond-saved-' + save.dataset.slug;
    try {
      const refresh = () => { const saved = localStorage.getItem(key) === '1'; save.setAttribute('aria-pressed', String(saved)); save.textContent = saved ? 'Saved ✓' : 'Save story'; };
      refresh(); save.addEventListener('click', () => { try { localStorage.getItem(key) === '1' ? localStorage.removeItem(key) : localStorage.setItem(key, '1'); refresh(); } catch { status.textContent = 'Saving is unavailable in this browser.'; } });
    } catch { save.hidden = true; }
  }
  const progress = document.querySelector('.reading-progress');
  if (progress) { const update = () => { const total = document.documentElement.scrollHeight - innerHeight; progress.style.width = (total > 0 ? Math.min(100, scrollY / total * 100) : 100) + '%'; }; addEventListener('scroll', update, {passive:true}); update(); }
  const ticker = document.querySelector('.breaking-ticker');
  const tickerToggle = ticker?.querySelector('.ticker-toggle');
  tickerToggle?.addEventListener('click', () => {
    const paused = ticker.classList.toggle('is-paused');
    tickerToggle.setAttribute('aria-pressed', String(paused));
    tickerToggle.setAttribute('aria-label', paused ? 'Resume breaking news animation' : 'Pause breaking news animation');
    tickerToggle.textContent = paused ? 'Resume' : 'Pause';
  });
})();
