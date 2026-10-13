(function () {
  'use strict';

  const API = window.COUTURE_CONFIG?.apiBase;
  const DEMO = API === null || API === undefined;
  const KEY_STORAGE = 'couture.accessKey';
  const $ = (selector, root = document) => root.querySelector(selector);

  const DEMO_PIECES = [
    ['1539008835657-9e8e9680c956', 'Robe Nocturne', 'Maison Lune'],
    ['1566174053879-31528523f8ae', 'Velours Prune', 'Atelier Sable'],
    ['1550639525-c97d455acf70', 'Tailleur Encre', 'Maison Lune'],
    ['1496747611176-843222e1e57c', 'Plissé Rose', 'Studio Orée'],
    ['1581044777550-4cfa60707c03', 'Organza Poudré', 'Atelier Sable'],
    ['1483985988355-763728e1935b', 'Voile d’Été', 'Studio Orée'],
  ].map(([photo, title, designer]) => ({
    demo: true, id: photo, title, designer,
    url: `https://images.unsplash.com/photo-${photo}?auto=format&fit=crop&w=900&h=1200&q=80`,
  }));

  const state = { health: null, accessKey: readKey() };

  // ---- utilities ----------------------------------------------------------

  function readKey() {
    try { return localStorage.getItem(KEY_STORAGE) || ''; } catch { return ''; }
  }
  function saveKey(value) {
    try { value ? localStorage.setItem(KEY_STORAGE, value) : localStorage.removeItem(KEY_STORAGE); } catch { /* private mode */ }
  }

  function el(tag, attrs = {}, ...children) {
    const node = document.createElement(tag);
    for (const [name, value] of Object.entries(attrs)) {
      if (value === undefined || value === null || value === false) continue;
      if (name === 'class') node.className = value;
      else if (name.startsWith('on')) node.addEventListener(name.slice(2), value);
      else node.setAttribute(name, value === true ? '' : value);
    }
    for (const child of children.flat()) {
      if (child !== null && child !== undefined && child !== false) node.append(child);
    }
    return node;
  }

  const link = (href, text) => el('a', { href, target: '_blank', rel: 'noopener' }, text);
  const short = (value, head = 10, tail = 8) => (value && value.length > head + tail + 1 ? `${value.slice(0, head)}…${value.slice(-tail)}` : value);
  const formatDate = (iso) => (iso ? new Intl.DateTimeFormat(undefined, { dateStyle: 'long', timeStyle: 'short' }).format(new Date(iso)) : '—');
  const formatBytes = (n) => (n < 1024 ** 2 ? `${(n / 1024).toFixed(0)} KB` : `${(n / 1024 ** 2).toFixed(1)} MB`);

  async function sha256Hex(file) {
    const digest = await crypto.subtle.digest('SHA-256', await file.arrayBuffer());
    return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('');
  }

  async function api(path, options = {}) {
    const headers = { ...(options.headers || {}) };
    if (state.accessKey) headers.Authorization = `Bearer ${state.accessKey}`;
    const response = await fetch(`${API}${path}`, { ...options, headers });
    if (!response.ok) {
      let detail = `${response.status} ${response.statusText}`;
      try { const body = await response.json(); detail = typeof body.detail === 'string' ? body.detail : body.detail?.[0]?.msg || detail; } catch { /* not JSON */ }
      const error = new Error(detail);
      error.status = response.status;
      error.body = response;
      throw error;
    }
    return response;
  }

  // ---- routing ------------------------------------------------------------

  const views = [...document.querySelectorAll('[data-view]')];
  function route() {
    const [name, arg] = (location.hash.slice(1) || 'collection').split('/');
    const target = views.find((v) => v.dataset.view === name) ? name : 'collection';
    views.forEach((view) => { view.hidden = view.dataset.view !== target; });
    document.querySelectorAll('[data-route]').forEach((a) => a.dataset.route === target ? a.setAttribute('aria-current', 'page') : a.removeAttribute('aria-current'));
    if (target === 'verify' && arg) lookup(arg);
    if (target === 'collection') loadGallery();
    window.scrollTo({ top: 0 });
  }
  window.addEventListener('hashchange', route);

  // ---- network status -----------------------------------------------------

  async function checkHealth() {
    const node = $('#network');
    const label = $('.network-label', node);
    if (DEMO) {
      node.dataset.state = 'degraded';
      label.textContent = 'Demo';
      node.title = 'Demo mode: no backend configured';
      return;
    }
    try {
      const health = await (await api('/api/health')).json();
      state.health = health;
      node.dataset.state = health.status === 'ok' ? 'ok' : 'degraded';
      label.textContent = `Solana ${health.cluster}`;
      node.title = health.network === 'ok'
        ? `Platform wallet ${health.wallet} · ${health.balance_sol?.toFixed(4)} SOL`
        : 'Solana network unreachable';
      $('#key-field').hidden = !health.auth_required;
      $('#key').value = state.accessKey;
    } catch {
      node.dataset.state = 'offline';
      label.textContent = 'Offline';
    }
  }

  // ---- collection ---------------------------------------------------------

  let galleryLoaded = false;
  async function loadGallery() {
    if (galleryLoaded) return;
    galleryLoaded = true;
    const gallery = $('#gallery');
    let pieces = [];
    if (DEMO) pieces = DEMO_PIECES;
    else {
      try { pieces = await (await api('/api/designs')).json(); } catch { pieces = []; galleryLoaded = false; }
    }
    gallery.replaceChildren(...pieces.map(pieceCard));
    $('#gallery-empty').hidden = pieces.length > 0 || !galleryLoaded;
    const observer = new IntersectionObserver((entries) => {
      entries.filter((e) => e.isIntersecting).forEach((entry) => {
        observer.unobserve(entry.target);
        paintThumbnail(entry.target);
      });
    }, { rootMargin: '200px' });
    gallery.querySelectorAll('.piece').forEach((node) => observer.observe(node));
  }

  function pieceCard(piece) {
    const canvas = el('canvas');
    const card = el('button', { class: 'piece', type: 'button', onclick: () => openViewer(piece) },
      el('div', { class: 'piece-frame' }, piece.has_preview === false ? el('span', { class: 'piece-placeholder' }, 'No visual') : canvas),
      el('div', { class: 'piece-meta' },
        el('div', {}, el('div', { class: 'piece-title' }, piece.title), el('div', { class: 'piece-designer' }, piece.designer)),
        el('span', { class: 'piece-seal' }, piece.demo ? 'Sample' : 'Sealed')));
    card.piece = piece;
    return card;
  }

  async function paintThumbnail(card) {
    const canvas = $('canvas', card);
    if (!canvas) return;
    try {
      const view = await loadView(card.piece, 640);
      window.CoutureCanvas.render(canvas, view, { cssWidth: canvas.clientWidth || 360 });
    } catch { /* leave the frame empty */ }
  }

  async function loadView(piece, size) {
    if (piece.demo) return window.CoutureCanvas.viewFromImageUrl(piece.url.replace('w=900&h=1200', size <= 640 ? 'w=600&h=800' : 'w=1200&h=1600'));
    const payload = await (await api(`/api/designs/${piece.id}/view?size=${size}`)).json();
    return window.CoutureCanvas.viewFromApi(payload);
  }

  // ---- protected viewer ---------------------------------------------------

  const viewer = $('#viewer');
  let viewerPiece = null;

  async function openViewer(piece) {
    viewerPiece = piece;
    viewer.hidden = false;
    document.body.style.overflow = 'hidden';
    $('#viewer-designer').textContent = piece.designer;
    $('#viewer-title').textContent = piece.title;
    renderFacts(piece);
    $('#certify').hidden = piece.demo || piece.status !== 'confirmed';
    $('#certify-note').textContent = '';
    const canvas = $('#viewer-canvas');
    canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
    $('#viewer-close').focus();
    if (piece.has_preview === false) return;
    try {
      const view = await loadView(piece, 1600);
      if (viewerPiece !== piece) return;
      const stage = $('#viewer-stage');
      const fit = Math.min(stage.clientWidth - 48, (stage.clientHeight - 48) * (view.width / view.height));
      window.CoutureCanvas.render(canvas, view, { cssWidth: Math.max(240, Math.min(fit, view.width)) });
    } catch (error) {
      $('#viewer-facts').append(el('dt', {}, 'Rendering'), el('dd', {}, `Unavailable (${error.message})`));
    }
  }

  function renderFacts(piece) {
    const facts = $('#viewer-facts');
    if (piece.demo) {
      facts.replaceChildren(
        el('dt', {}, 'Status'), el('dd', {}, 'Sample piece (demo mode)'),
        el('dt', {}, 'Viewer'), el('dd', {}, `Session ${window.CoutureCanvas.session}`));
      return;
    }
    facts.replaceChildren(
      el('dt', {}, 'Sealed'), el('dd', {}, formatDate(piece.registered_at)),
      el('dt', {}, 'Fingerprint'), el('dd', {}, el('code', {}, piece.sha256)),
      el('dt', {}, 'Transaction'), el('dd', {}, piece.explorer_url ? link(piece.explorer_url, short(piece.signature, 12, 12)) : '—'),
      el('dt', {}, 'Viewer'), el('dd', {}, `Session ${window.CoutureCanvas.session}`));
  }

  function closeViewer() {
    viewer.hidden = true;
    viewerPiece = null;
    document.body.style.overflow = '';
    const canvas = $('#viewer-canvas');
    canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
  }

  $('#viewer-close').addEventListener('click', closeViewer);
  document.addEventListener('keydown', (event) => { if (event.key === 'Escape' && !viewer.hidden) closeViewer(); });

  // Veil protected work whenever the page is not in focus (screen-capture tools usually take it).
  const veil = (on) => viewer.classList.toggle('is-veiled', on);
  window.addEventListener('blur', () => veil(true));
  window.addEventListener('focus', () => veil(false));
  document.addEventListener('visibilitychange', () => veil(document.hidden));
  window.CoutureCanvas.installGuards({ onExposure: () => { veil(true); setTimeout(() => veil(false), 1500); } });

  $('#certify-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const note = $('#certify-note');
    const owner = $('#certify-owner').value.trim();
    const button = $('button', event.currentTarget);
    if (!/^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(owner)) {
      note.className = 'form-note is-error';
      note.textContent = 'Enter a valid Solana wallet address.';
      return;
    }
    button.disabled = true;
    note.className = 'form-note';
    note.textContent = 'Minting the certificate on Solana…';
    try {
      const response = await api(`/api/designs/${viewerPiece.id}/certificates`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ owner }),
      });
      const cert = await response.json();
      note.replaceChildren(
        cert.status === 'confirmed' ? 'Certificate delivered. ' : 'Submitted, awaiting confirmation. ',
        cert.explorer_url ? link(cert.explorer_url, 'View transaction') : '',
        cert.asset_explorer_url ? ' · ' : '',
        cert.asset_explorer_url ? link(cert.asset_explorer_url, 'View asset') : '');
    } catch (error) {
      note.className = 'form-note is-error';
      note.textContent = error.status === 401 ? 'A valid access key is required (set it in Register).' : error.message;
    } finally {
      button.disabled = false;
    }
  });

  // ---- register -------------------------------------------------------------

  const studio = $('#studio');
  const fileInput = $('#file');
  const timeline = $('#timeline');

  function setFile(file) {
    $('#drop').hidden = Boolean(file);
    $('#file-chip').hidden = !file;
    $('#file-name').textContent = file ? `${file.name} · ${formatBytes(file.size)}` : '';
    if (file && !$('#title').value) $('#title').value = file.name.replace(/\.[^.]+$/, '').replace(/[-_]+/g, ' ');
  }

  fileInput.addEventListener('change', () => setFile(fileInput.files[0]));
  $('#file-clear').addEventListener('click', () => { fileInput.value = ''; setFile(null); resetProgress(); });
  for (const drop of document.querySelectorAll('.drop')) {
    drop.addEventListener('dragover', () => drop.classList.add('is-over'));
    ['dragleave', 'drop'].forEach((type) => drop.addEventListener(type, () => drop.classList.remove('is-over')));
  }

  function step(name, status, ...detail) {
    const item = $(`[data-step="${name}"]`, timeline);
    item.className = status ? `is-${status}` : '';
    if (detail.length) $('.step-detail', item).replaceChildren(...detail);
  }

  function resetProgress() {
    timeline.hidden = true;
    $('#seal').hidden = true;
    timeline.querySelectorAll('li').forEach((li) => { li.className = ''; $('.step-detail', li).replaceChildren(); });
    note('');
  }

  function note(text, isError = false) {
    const node = $('#form-note');
    node.className = `form-note${isError ? ' is-error' : ''}`;
    node.textContent = text;
  }

  studio.addEventListener('submit', async (event) => {
    event.preventDefault();
    const file = fileInput.files[0];
    const title = $('#title').value.trim();
    const designer = $('#designer').value.trim();
    if (!file) return note('Choose a design file first.', true);
    if (!title || !designer) return note('Add the title and the designer.', true);
    if (state.health?.auth_required) {
      state.accessKey = $('#key').value.trim();
      if (!state.accessKey) return note('Enter your access key.', true);
      saveKey(state.accessKey);
    }

    resetProgress();
    timeline.hidden = false;
    const submit = $('#submit');
    submit.disabled = true;
    step('received', 'active', `${file.name} · ${formatBytes(file.size)}`);
    const localHash = sha256Hex(file);

    if (DEMO) {
      step('received', 'done');
      step('hashed', 'done', el('code', {}, await localHash), ' (computed locally)');
      step('submitted', 'error', 'Demo mode: connect a Couture backend to seal on Solana.');
      submit.disabled = false;
      return;
    }

    const form = new FormData();
    form.append('file', file);
    form.append('title', title);
    form.append('designer', designer);

    try {
      const response = await api('/api/designs', { method: 'POST', body: form });
      await readEvents(response, (event) => handleEvent(event, localHash));
    } catch (error) {
      const active = timeline.querySelector('.is-active');
      if (active) active.className = 'is-error';
      note(error.status === 401 ? 'This access key was not accepted.' : `Registration failed: ${error.message}`, true);
    } finally {
      submit.disabled = false;
    }
  });

  async function readEvents(response, onEvent) {
    const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
    let buffer = '';
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += value;
      let newline;
      while ((newline = buffer.indexOf('\n')) >= 0) {
        const line = buffer.slice(0, newline).trim();
        buffer = buffer.slice(newline + 1);
        if (line) await onEvent(JSON.parse(line));
      }
    }
  }

  async function handleEvent(event, localHash) {
    switch (event.event) {
      case 'received':
        step('received', 'done');
        step('hashed', 'active');
        break;
      case 'hashed': {
        const match = (await localHash) === event.sha256;
        step('hashed', 'done', el('code', {}, event.sha256), match ? ' · matches your browser' : ' · differs from local computation');
        step('submitted', 'active', 'Preparing transaction…');
        break;
      }
      case 'duplicate': {
        const design = event.design;
        step('submitted', 'done', 'Already on the ledger');
        step('confirmed', design.status === 'confirmed' ? 'done' : 'active',
          design.status === 'confirmed' ? `Originally sealed ${formatDate(design.registered_at)}` : 'Registration in progress');
        if (design.status === 'confirmed') showSeal(design, true);
        break;
      }
      case 'submitting':
        step('submitted', 'active', 'Signing and broadcasting…');
        break;
      case 'submitted':
        step('submitted', 'done', link(event.explorer_url, short(event.signature, 14, 14)));
        step('confirmed', 'active', 'Awaiting network confirmation…');
        break;
      case 'confirmed':
        step('confirmed', 'done', `Slot ${event.design.slot.toLocaleString()} · ${formatDate(event.design.registered_at)}`);
        showSeal(event.design, false);
        galleryLoaded = false;
        break;
      case 'unconfirmed':
        step('confirmed', 'active', event.message);
        note('The transaction was broadcast. It will appear in the collection once the network confirms it.');
        break;
      case 'failed':
        timeline.querySelector('.is-active')?.classList.replace('is-active', 'is-error');
        note(event.message, true);
        break;
      default:
        break;
    }
  }

  function showSeal(design, isDuplicate) {
    const seal = $('#seal');
    seal.replaceChildren(
      el('p', { class: 'eyebrow' }, isDuplicate ? 'Previously registered' : 'Sealed on Solana'),
      el('h3', {}, design.title),
      el('p', {}, `${design.designer} · ${formatDate(design.registered_at)}`),
      el('div', { class: 'seal-actions' },
        link(design.explorer_url, 'View on Solana Explorer'),
        el('a', { href: `#verify/${design.sha256}` }, 'Verification record'),
        design.has_preview ? el('a', { href: '#collection' }, 'See it in the collection') : null));
    seal.hidden = false;
  }

  // ---- verify -------------------------------------------------------------

  $('#verify-file').addEventListener('change', async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    $('#verify-hash').value = await sha256Hex(file);
    lookup($('#verify-hash').value, file.name);
    event.target.value = '';
  });

  $('#verify-form').addEventListener('submit', (event) => {
    event.preventDefault();
    lookup($('#verify-hash').value.trim());
  });

  async function lookup(hash, filename) {
    const verdict = $('#verdict');
    hash = hash.toLowerCase();
    $('#verify-hash').value = hash;
    verdict.hidden = false;
    if (!/^[0-9a-f]{64}$/.test(hash)) {
      verdict.className = 'verdict is-miss';
      verdict.replaceChildren(el('h3', {}, 'That is not a SHA-256 fingerprint.'), el('p', {}, 'A fingerprint has 64 hexadecimal characters.'));
      return;
    }
    if (DEMO) {
      verdict.className = 'verdict is-miss';
      verdict.replaceChildren(el('h3', {}, 'Verification needs the Couture backend.'), el('p', {}, 'This page is running in demo mode.'));
      return;
    }
    verdict.className = 'verdict';
    verdict.replaceChildren(el('p', {}, 'Consulting the registry…'));
    try {
      const design = await (await api(`/api/designs/by-hash/${hash}`)).json();
      verdict.className = 'verdict is-match';
      verdict.replaceChildren(
        el('h3', {}, design.status === 'confirmed' ? 'Registered original.' : 'Registration in progress.'),
        el('dl', { class: 'facts' },
          filename ? [el('dt', {}, 'File'), el('dd', {}, filename)] : [],
          el('dt', {}, 'Piece'), el('dd', {}, design.title),
          el('dt', {}, 'Designer'), el('dd', {}, design.designer),
          el('dt', {}, 'Sealed'), el('dd', {}, formatDate(design.registered_at)),
          el('dt', {}, 'Fingerprint'), el('dd', {}, el('code', {}, design.sha256)),
          el('dt', {}, 'On-chain memo'), el('dd', {}, el('code', {}, design.memo)),
          el('dt', {}, 'Transaction'), el('dd', {}, design.explorer_url ? link(design.explorer_url, short(design.signature, 12, 12)) : '—')));
    } catch (error) {
      verdict.className = 'verdict is-miss';
      verdict.replaceChildren(
        el('h3', {}, error.status === 404 ? 'No registered design matches.' : 'The registry could not be reached.'),
        el('p', {}, error.status === 404 ? 'This exact file has not been sealed with Couture.' : error.message));
    }
  }

  // ---- boot ---------------------------------------------------------------

  checkHealth();
  route();
})();
