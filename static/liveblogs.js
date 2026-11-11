(() => {
  const root = document.querySelector('[data-live-status="live"]');
  if (!root) return;
  const list = root.querySelector('[data-live-updates]');
  const label = root.querySelector('[data-live-status-label]');
  if (!list) return;
  let lastId = Number(root.dataset.lastUpdateId || 0);
  let stopped = false;
  const append = (update) => {
    if (list.querySelector(`[data-update-id="${Number(update.id)}"]`)) return;
    const card = document.createElement('article');
    card.className = `live-update${update.pinned ? ' is-pinned' : ''}`;
    card.dataset.updateId = String(Number(update.id));
    const meta = document.createElement('div');
    meta.className = 'live-update-meta';
    const time = document.createElement('time');
    time.dateTime = update.published_at;
    time.textContent = update.display_time;
    meta.append(time);
    if (update.pinned) { const pin = document.createElement('span'); pin.textContent = 'KEY UPDATE'; meta.append(pin); }
    const author = document.createElement('span'); author.textContent = update.author; meta.append(author);
    const body = document.createElement('div');
    body.className = 'live-update-content';
    const template = document.createElement('template');
    template.innerHTML = update.content;
    body.append(template.content);
    card.append(meta, body);
    list.querySelector('.live-no-updates')?.remove();
    list.prepend(card);
  };
  const refresh = async () => {
    if (stopped || document.hidden) return;
    try {
      const response = await fetch(`${root.dataset.updatesUrl}?after=${lastId}`, { headers: { Accept: 'application/json' }, credentials: 'same-origin' });
      if (!response.ok) throw new Error('Update request failed');
      const data = await response.json();
      for (const update of data.updates) { append(update); lastId = Math.max(lastId, Number(update.id)); }
      root.dataset.lastUpdateId = String(lastId);
      if (data.status !== 'live') { stopped = true; if (label) label.textContent = 'This live report is closed'; }
      else if (data.updates.length && label) label.textContent = 'New newsroom update just published';
    } catch (_) { if (label) label.textContent = 'Updates will retry automatically'; }
  };
  window.setInterval(refresh, 45000);
})();
