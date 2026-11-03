(function () {
  'use strict';

  const API = window.COUTURE_CONFIG?.apiBase;
  const DEMO = API === null || API === undefined;
  const KEY_STORAGE = 'couture.accessKey';
  const DEFAULT_MAX_UPLOAD_MB = 50;
  const ORDER_REF = /^[A-Za-z0-9._:-]{1,64}$/;
  const WALLET = /^[1-9A-HJ-NP-Za-km-z]{32,44}$/;
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

  // keyStatus: 'none' (no key stored), 'unchecked', 'valid'. A key is only ever
  // stored after the API accepted it (GET /api/session has no side effects).
  const state = { health: null, accessKey: readKey(), keyStatus: readKey() ? 'unchecked' : 'none' };

  // ---- utilities ----------------------------------------------------------

  function readKey() {
    try { return localStorage.getItem(KEY_STORAGE) || ''; } catch { return ''; }
  }
  function storeKey(value) {
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
  const formatDate = (iso) => (iso ? new Intl.DateTimeFormat(undefined, { dateStyle: 'long', timeStyle: 'short' }).format(new Date(iso)) : '—');
  const formatBytes = (n) => (n < 1024 ** 2 ? `${(n / 1024).toFixed(0)} KB` : `${(n / 1024 ** 2).toFixed(1)} MB`);
  const networkName = () => (state.health?.cluster ? `Solana ${state.health.cluster}` : 'Solana');

  // Cryptographic values are shown in full (DESIGN.md: The Proof Is Mono) with a copy control.
  function proof(value) {
    if (!value) return '—';
    const button = el('button', { type: 'button', class: 'copy', 'aria-label': 'Copy to clipboard' }, 'Copy');
    button.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(value);
        button.textContent = 'Copied';
      } catch {
        button.textContent = 'Select to copy';
      }
      setTimeout(() => { button.textContent = 'Copy'; }, 1800);
    });
    return el('span', { class: 'proof' }, el('code', {}, value), button);
  }

  async function sha256Hex(file) {
    const digest = await crypto.subtle.digest('SHA-256', await file.arrayBuffer());
    return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('');
  }

  async function api(path, { key = state.accessKey, ...options } = {}) {
    const headers = { ...(options.headers || {}) };
    if (key) headers.Authorization = `Bearer ${key}`;
    let response;
    try {
      response = await fetch(`${API}${path}`, { ...options, headers });
    } catch {
      const error = new Error('network');
      error.status = 0;
      throw error;
    }
    if (!response.ok) {
      let detail = '';
      try { const body = await response.json(); detail = typeof body.detail === 'string' ? body.detail : ''; } catch { /* not JSON */ }
      const error = new Error(detail || `HTTP ${response.status}`);
      error.status = response.status;
      error.detail = detail;
      throw error;
    }
    return response;
  }

  // One place that turns failures into sentences people can act on. Raw
  // server text is only used for 4xx answers the API words for humans.
  function explain(error, what = 'This request') {
    switch (error.status) {
      case 0: return "Couture's server can't be reached. Check your connection and try again.";
      case 401: return 'Your studio access key was not accepted. Enter it again.';
      case 403: return error.detail || "You don't have permission to do this.";
      case 404: return error.detail || 'Not found.';
      case 409:
      case 422: return error.detail || `${what} was refused. Check the details and try again.`;
      case 411:
      case 413: return error.detail || 'The file is too large.';
      case 429: return error.detail || 'Too many requests. Wait a moment and try again.';
      case 503: return 'This service is temporarily unavailable. Try again in a few minutes.';
      default: return `${what} could not be completed (server error). Try again in a moment.`;
    }
  }

  // ---- studio access key --------------------------------------------------

  async function verifyKey(value) {
    if (DEMO || !state.health?.auth_required) return true;
    try {
      await api('/api/session', { key: value });
    } catch (error) {
      if (error.status === 401) return false;
      throw error;
    }
    return true;
  }

  async function setKey(value) {
    value = value.trim();
    if (!value) { forgetKey(); return false; }
    const ok = await verifyKey(value);
    if (ok) {
      state.accessKey = value;
      state.keyStatus = 'valid';
      storeKey(value);
      $('#key').value = value;
    }
    return ok;
  }

  function forgetKey() {
    state.accessKey = '';
    state.keyStatus = 'none';
    storeKey('');
    $('#key').value = '';
  }

  // Register's key field saves as soon as the key is entered, not on submit.
  $('#key').addEventListener('change', async (event) => {
    const status = $('#key-status');
    status.className = 'field-status';
    status.textContent = 'Checking key…';
    try {
      const ok = await setKey(event.target.value);
      status.className = `field-status${ok ? '' : ' is-error'}`;
      status.textContent = ok ? 'Key accepted and saved on this device.' : (event.target.value.trim() ? 'This key was not accepted.' : '');
    } catch (error) {
      status.className = 'field-status is-error';
      status.textContent = explain(error, 'Checking the key');
    }
  });

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
      const health = await (await api('/api/health', { key: '' })).json();
      state.health = health;
      node.dataset.state = health.status === 'ok' ? 'ok' : 'degraded';
      label.textContent = networkName();
      node.title = health.network === 'ok' ? `Connected to ${networkName()}` : 'Solana network unreachable';
      $('#key-field').hidden = !health.auth_required;
      $('#pre-seal').textContent = `Sealing publishes this file's fingerprint on ${networkName()}, where it cannot be removed. `
        + 'Your file and your name stay off-chain. Keep this exact file: any re-export changes its fingerprint.';
      if (health.auth_required && state.keyStatus === 'unchecked') {
        const ok = await verifyKey(state.accessKey).catch(() => true);
        if (ok) state.keyStatus = 'valid'; else forgetKey();
      }
      $('#key').value = state.accessKey;
    } catch {
      node.dataset.state = 'offline';
      label.textContent = 'Offline';
      node.title = "Couture's server can't be reached";
    }
  }

  // ---- collection ---------------------------------------------------------

  let galleryLoaded = false;
  let galleryLoading = false;
  async function loadGallery() {
    if (galleryLoaded || galleryLoading) return;
    galleryLoading = true;
    const gallery = $('#gallery');
    const status = $('#gallery-status');
    status.replaceChildren(el('p', { class: 'muted' }, 'Opening the archive…'));
    $('#gallery-empty').hidden = true;
    let pieces;
    try {
      pieces = DEMO ? DEMO_PIECES : await (await api('/api/designs')).json();
      galleryLoaded = true;
    } catch (error) {
      gallery.replaceChildren();
      status.replaceChildren(
        el('p', { class: 'muted' }, `The archive couldn't be loaded. ${explain(error, 'Loading the archive')}`),
        el('button', { type: 'button', class: 'button button-quiet', onclick: () => loadGallery() }, 'Try again'));
      galleryLoading = false;
      return;
    }
    galleryLoading = false;
    status.replaceChildren();
    gallery.replaceChildren(...pieces.map(pieceCard));
    $('#gallery-empty').hidden = pieces.length > 0;
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
    const card = el('button', { class: 'piece', type: 'button', onclick: () => openViewer(piece, card) },
      el('span', { class: 'piece-frame' }, piece.has_preview === false ? el('span', { class: 'piece-placeholder' }, 'No visual') : canvas),
      el('span', { class: 'piece-meta' },
        el('span', {}, el('span', { class: 'piece-title' }, piece.title), el('span', { class: 'piece-designer' }, piece.designer)),
        el('span', { class: 'piece-seal' }, piece.demo ? 'Sample' : piece.status === 'confirmed' ? 'Sealed' : 'Pending')));
    card.piece = piece;
    return card;
  }

  async function paintThumbnail(card) {
    const canvas = $('canvas', card);
    if (!canvas) return;
    try {
      const view = await loadView(card.piece, 640);
      window.CoutureCanvas.render(canvas, view, { cssWidth: canvas.clientWidth || 360 });
    } catch {
      canvas.replaceWith(el('span', { class: 'piece-placeholder' }, 'Preview unavailable'));
    }
  }

  async function loadView(piece, size) {
    if (piece.demo) return window.CoutureCanvas.viewFromImageUrl(piece.url.replace('w=900&h=1200', size <= 640 ? 'w=600&h=800' : 'w=1200&h=1600'));
    const payload = await (await api(`/api/designs/${piece.id}/view?size=${size}`)).json();
    return window.CoutureCanvas.viewFromApi(payload);
  }

  // ---- protected viewer ---------------------------------------------------

  const viewer = $('#viewer');
  const outside = [$('.masthead'), $('main'), $('.colophon')];
  let viewerPiece = null;
  let returnFocus = null;
  let removeGuards = null;

  async function openViewer(piece, opener) {
    viewerPiece = piece;
    returnFocus = opener || document.activeElement;
    viewer.hidden = false;
    outside.forEach((node) => { node.inert = true; });
    document.body.style.overflow = 'hidden';
    removeGuards = window.CoutureCanvas.installGuards($('#viewer-stage'), {
      onExposure: () => { veil(true); setTimeout(() => veil(false), 1500); },
    });
    $('#viewer-designer').textContent = piece.designer;
    $('#viewer-title').textContent = piece.title;
    renderFacts(piece);
    resetCertify(piece);
    const canvas = $('#viewer-canvas');
    const status = $('#viewer-status');
    canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
    $('#viewer-close').focus();
    if (piece.has_preview === false) { status.textContent = 'This design has no visual preview.'; return; }
    status.textContent = 'Preparing the protected view…';
    try {
      const view = await loadView(piece, 1600);
      if (viewerPiece !== piece) return;
      const stage = $('#viewer-stage');
      const fit = Math.min(stage.clientWidth - 48, (stage.clientHeight - 48) * (view.width / view.height));
      window.CoutureCanvas.render(canvas, view, { cssWidth: Math.max(240, Math.min(fit, view.width)) });
      status.textContent = '';
    } catch (error) {
      if (viewerPiece === piece) status.textContent = `The protected view couldn't be loaded. ${explain(error, 'Loading the view')}`;
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
      el('dt', {}, 'Fingerprint'), el('dd', {}, proof(piece.sha256)),
      el('dt', {}, 'Transaction'), el('dd', {}, proof(piece.signature), piece.explorer_url ? [' ', link(piece.explorer_url, 'View on explorer')] : null),
      el('dt', {}, 'Viewer'), el('dd', {}, `Session ${window.CoutureCanvas.session}`));
  }

  function closeViewer() {
    viewer.hidden = true;
    viewerPiece = null;
    removeGuards?.();
    removeGuards = null;
    outside.forEach((node) => { node.inert = false; });
    document.body.style.overflow = '';
    const canvas = $('#viewer-canvas');
    canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
    $('#viewer-status').textContent = '';
    if (returnFocus?.isConnected) returnFocus.focus();
    returnFocus = null;
  }

  $('#viewer-close').addEventListener('click', closeViewer);
  document.addEventListener('keydown', (event) => { if (event.key === 'Escape' && !viewer.hidden) closeViewer(); });

  // Veil protected work whenever the page is not in focus (screen-capture tools usually take it).
  const veil = (on) => viewer.classList.toggle('is-veiled', on);
  window.addEventListener('blur', () => veil(true));
  window.addEventListener('focus', () => veil(false));
  document.addEventListener('visibilitychange', () => veil(document.hidden));

  // ---- certificates -------------------------------------------------------
  // Locked (no key) -> form -> review (explicit confirm) -> result (form locked).

  const certifyForm = $('#certify-form');
  const review = $('#certify-review');

  function certifyNote(text, isError = false) {
    const node = $('#certify-note');
    node.className = `form-note${isError ? ' is-error' : ''}`;
    node.replaceChildren(...[text].flat());
  }

  function resetCertify(piece) {
    const available = !piece.demo && piece.status === 'confirmed' && state.health?.certificates_ready !== false;
    $('#certify').hidden = !available;
    if (!available) return;
    const locked = Boolean(state.health?.auth_required) && state.keyStatus !== 'valid';
    $('#certify-locked').hidden = !locked;
    certifyForm.hidden = locked;
    certifyForm.reset();
    certifyForm.querySelectorAll('input, button').forEach((node) => { node.disabled = false; });
    review.hidden = true;
    review.replaceChildren();
    certifyNote('');
  }

  $('#unlock-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const input = $('#unlock-key');
    const button = $('button', event.currentTarget);
    if (!input.value.trim()) return certifyNote('Enter your studio access key.', true);
    button.disabled = true;
    certifyNote('Checking key…');
    try {
      if (await setKey(input.value)) {
        input.value = '';
        resetCertify(viewerPiece);
        certifyNote('Key accepted and saved on this device.');
        $('#certify-owner').focus();
      } else {
        certifyNote('This key was not accepted.', true);
      }
    } catch (error) {
      certifyNote(explain(error, 'Checking the key'), true);
    } finally {
      button.disabled = false;
    }
  });

  certifyForm.addEventListener('submit', (event) => {
    event.preventDefault();
    const owner = $('#certify-owner').value.trim();
    const order = $('#certify-order').value.trim();
    if (!WALLET.test(owner)) return certifyNote("That doesn't look like a Solana wallet address (32 to 44 letters and digits).", true);
    if (!ORDER_REF.test(order)) return certifyNote('Order reference: up to 64 letters, numbers and . _ : - (no spaces).', true);
    certifyNote('');
    showReview(owner, order);
  });

  function showReview(owner, order) {
    const piece = viewerPiece;
    certifyForm.querySelectorAll('input, button').forEach((node) => { node.disabled = true; });
    review.replaceChildren(
      el('h5', {}, 'Review before issuing'),
      el('dl', { class: 'facts' },
        el('dt', {}, 'Piece'), el('dd', {}, piece.title),
        el('dt', {}, 'Buyer wallet'), el('dd', {}, el('code', {}, owner)),
        el('dt', {}, 'Order'), el('dd', {}, el('code', {}, order)),
        el('dt', {}, 'Network'), el('dd', {}, networkName())),
      el('p', { class: 'review-warning' }, 'This cannot be undone. A certificate sent to a wrong wallet cannot be recalled; check the address with the buyer.'),
      el('div', { class: 'review-actions' },
        el('button', { type: 'button', class: 'button', id: 'certify-confirm', onclick: () => issue(piece, owner, order) }, 'Issue certificate'),
        el('button', { type: 'button', class: 'link', onclick: editCertify }, 'Edit')));
    review.hidden = false;
    $('#certify-confirm').focus();
  }

  function editCertify() {
    review.hidden = true;
    review.replaceChildren();
    certifyForm.querySelectorAll('input, button').forEach((node) => { node.disabled = false; });
    $('#certify-owner').focus();
  }

  async function issue(piece, owner, order) {
    const confirm = $('#certify-confirm');
    confirm.disabled = true;
    certifyNote(`Issuing the certificate on ${networkName()}…`);
    try {
      const response = await api(`/api/designs/${piece.id}/certificates`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // The order reference is the idempotency key: retrying (or a second
        // click) returns the same certificate instead of minting another.
        body: JSON.stringify({ owner, order_id: order }),
      });
      if (viewerPiece !== piece) return;
      const cert = await response.json();
      const replay = response.status === 200;
      const headline = replay ? 'This order already has its certificate.'
        : cert.status === 'confirmed' ? 'Certificate delivered.'
          : cert.status === 'unconfirmed' ? 'Submitted; the network has not confirmed it yet. Check the transaction in a few minutes.'
            : "The certificate couldn't be issued. Try again with the same order reference; it will not be issued twice.";
      review.replaceChildren(
        el('h5', {}, headline),
        el('dl', { class: 'facts' },
          el('dt', {}, 'Buyer wallet'), el('dd', {}, proof(cert.owner)),
          el('dt', {}, 'Order'), el('dd', {}, el('code', {}, order)),
          cert.signature ? [el('dt', {}, 'Transaction'), el('dd', {}, proof(cert.signature), cert.explorer_url ? [' ', link(cert.explorer_url, 'View on explorer')] : null)] : [],
          cert.asset_explorer_url ? [el('dt', {}, 'Certificate'), el('dd', {}, link(cert.asset_explorer_url, 'View asset'))] : []),
        el('div', { class: 'review-actions' },
          el('button', { type: 'button', class: 'button button-quiet', onclick: () => resetCertify(piece) }, 'Issue another certificate')));
      certifyNote('');
    } catch (error) {
      if (viewerPiece !== piece) return;
      if (error.status === 401) {
        forgetKey();
        resetCertify(piece);
        certifyNote('Your studio access key was not accepted. Enter it again to continue.', true);
        return;
      }
      confirm.disabled = false;
      certifyNote(error.status === 502
        ? "The network rejected the certificate. Nothing was issued; confirm again to retry with the same order reference."
        : explain(error, 'Issuing the certificate'), true);
    }
  }

  // ---- register -------------------------------------------------------------

  const studio = $('#studio');
  const fileInput = $('#file');
  const timeline = $('#timeline');
  const maxUploadBytes = () => (state.health?.max_upload_mb || DEFAULT_MAX_UPLOAD_MB) * 1024 * 1024;

  function setFile(file) {
    $('#drop').hidden = Boolean(file);
    $('#file-chip').hidden = !file;
    $('#file-name').textContent = file ? `${file.name} · ${formatBytes(file.size)}` : '';
    if (file && !$('#title').value) $('#title').value = file.name.replace(/\.[^.]+$/, '').replace(/[-_]+/g, ' ');
    if (file && file.size > maxUploadBytes()) note(`This file is ${formatBytes(file.size)}; the limit is ${formatBytes(maxUploadBytes())}.`, true);
    else note('');
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
    node.replaceChildren(...[text].flat());
  }

  function resetStudio() {
    fileInput.value = '';
    setFile(null);
    $('#title').value = '';
    resetProgress();
    setStudioBusy(false);
    $('#drop').scrollIntoView({ block: 'center', behavior: 'smooth' });
  }

  function setStudioBusy(busy) {
    $('#submit').disabled = busy;
    studio.querySelectorAll('input:not([type="file"]), #file-clear').forEach((node) => { node.disabled = busy; });
  }

  let sealing = false;
  studio.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (sealing) return;
    const file = fileInput.files[0];
    const title = $('#title').value.trim();
    const designer = $('#designer').value.trim();
    if (!file) return note('Choose a design file first.', true);
    if (file.size === 0) return note('This file is empty.', true);
    if (file.size > maxUploadBytes()) return note(`This file is ${formatBytes(file.size)}; the limit is ${formatBytes(maxUploadBytes())}.`, true);
    if (!title || !designer) return note('Add the title and the designer.', true);
    if (state.health?.auth_required && state.keyStatus !== 'valid') {
      const typed = $('#key').value.trim();
      if (!typed) return note('Enter your studio access key.', true);
      try {
        if (!(await setKey(typed))) return note('This access key was not accepted.', true);
      } catch (error) {
        return note(explain(error, 'Checking the key'), true);
      }
    }

    sealing = true;
    resetProgress();
    timeline.hidden = false;
    setStudioBusy(true);
    step('received', 'active', `${file.name} · ${formatBytes(file.size)}`);
    const localHash = sha256Hex(file);

    if (DEMO) {
      step('received', 'done');
      step('hashed', 'done', proof(await localHash), ' (computed on this device)');
      step('submitted', 'pending', 'Demo mode: sealing needs a Couture server. Nothing was sent.');
      setStudioBusy(false);
      sealing = false;
      return;
    }

    const form = new FormData();
    form.append('file', file);
    form.append('title', title);
    form.append('designer', designer);

    let finished = false;
    try {
      const response = await api('/api/designs', { method: 'POST', body: form });
      await readEvents(response, async (event) => { finished = (await handleEvent(event, localHash)) || finished; });
      if (!finished) throw Object.assign(new Error('stream ended'), { status: 0 });
    } catch (error) {
      timeline.querySelector('.is-active')?.classList.replace('is-active', 'is-error');
      if (error.status === 401) forgetKey();
      note(error.status === 0 && timeline.querySelector('[data-step="submitted"].is-done')
        ? 'The connection dropped after the transaction was sent. It may still be sealed: look the file up in Verify in a few minutes.'
        : explain(error, 'Registration'), true);
    } finally {
      setStudioBusy(false);
      sealing = false;
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

  // Returns true once the stream reached an outcome the designer can act on.
  async function handleEvent(event, localHash) {
    switch (event.event) {
      case 'received':
        step('received', 'done');
        step('hashed', 'active');
        return false;
      case 'hashed': {
        const match = (await localHash) === event.sha256;
        step('hashed', 'done', proof(event.sha256), match ? ' · matches your browser' : '');
        if (!match) {
          note("The server's fingerprint differs from the one your browser computed, so the file changed in transit. "
            + "Don't rely on this registration: replace the file and seal it again.", true);
        }
        step('submitted', 'active', 'Preparing transaction…');
        return false;
      }
      case 'duplicate': {
        const design = event.design;
        step('submitted', 'done', 'Already on the ledger');
        if (design.status === 'confirmed') {
          step('confirmed', 'done', `Originally sealed ${formatDate(design.registered_at)}`);
          showSeal(design, true);
        } else if (design.status === 'failed') {
          step('confirmed', 'error', 'A previous registration of this file failed.');
          note('This file is held by another studio account and its registration did not complete. Contact Couture.', true);
        } else {
          step('confirmed', 'pending', 'Registration in progress');
          note(['This file is already being registered. ', el('a', { href: `#verify/${design.sha256}` }, 'Check its status in Verify'), '.']);
        }
        return true;
      }
      case 'submitting':
        step('submitted', 'active', 'Signing and broadcasting…');
        return false;
      case 'submitted':
        step('submitted', 'done', proof(event.signature), ' ', link(event.explorer_url, 'View on explorer'));
        step('confirmed', 'active', 'Awaiting network confirmation…');
        return false;
      case 'confirmed':
        step('confirmed', 'done', `Slot ${event.design.slot.toLocaleString()} · ${formatDate(event.design.registered_at)}`);
        showSeal(event.design, false);
        galleryLoaded = false;
        return true;
      case 'unconfirmed':
        // Not an endless pulse: a resting state with a way to check back.
        step('confirmed', 'pending', 'Sent; the network has not confirmed it yet.');
        note(['The transaction was broadcast and usually confirms within minutes. ',
          el('a', { href: `#verify/${event.design.sha256}` }, 'Check its status in Verify'), '.']);
        return true;
      case 'failed':
        timeline.querySelector('.is-active')?.classList.replace('is-active', 'is-error');
        note(event.retryable ? `${event.message} Your file was not sealed; you can submit it again.` : event.message, true);
        return true;
      default:
        return false;
    }
  }

  function showSeal(design, isDuplicate) {
    const seal = $('#seal');
    seal.classList.toggle('is-duplicate', isDuplicate);
    seal.replaceChildren(
      el('h3', { tabindex: '-1' }, isDuplicate ? 'This file was already registered' : design.title),
      el('p', {}, isDuplicate
        ? `Registered as “${design.title}” by ${design.designer} on ${formatDate(design.registered_at)}. A file can only be sealed once. If this registration isn't yours, keep your dated sketches and source files as evidence.`
        : `${design.designer} · ${formatDate(design.registered_at)}`),
      el('div', { class: 'seal-actions' },
        design.explorer_url ? link(design.explorer_url, 'View on Solana Explorer') : null,
        el('a', { href: `#verify/${design.sha256}` }, 'Verification record'),
        !isDuplicate && design.has_preview ? el('a', { href: '#collection' }, 'See it in the collection') : null,
        el('button', { type: 'button', class: 'link', onclick: resetStudio }, 'Seal another design')));
    seal.hidden = false;
    seal.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    $('h3', seal).focus({ preventScroll: true });
  }

  // ---- verify -------------------------------------------------------------

  $('#verify-file').addEventListener('change', async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    const verdict = $('#verdict');
    verdict.hidden = false;
    verdict.className = 'verdict';
    verdict.replaceChildren(el('p', {}, `Fingerprinting ${file.name} on this device…`));
    try {
      $('#verify-hash').value = await sha256Hex(file);
    } catch {
      verdict.replaceChildren(el('h3', {}, "This file couldn't be read."), el('p', {}, 'Try choosing it again.'));
      return;
    } finally {
      event.target.value = '';
    }
    lookup($('#verify-hash').value, file.name);
  });

  $('#verify-form').addEventListener('submit', (event) => {
    event.preventDefault();
    lookup($('#verify-hash').value.trim());
  });

  let lookupSeq = 0;
  async function lookup(hash, filename) {
    const seq = ++lookupSeq;
    const verdict = $('#verdict');
    hash = hash.trim().toLowerCase();
    $('#verify-hash').value = hash;
    verdict.hidden = false;
    if (!/^[0-9a-f]{64}$/.test(hash)) {
      verdict.className = 'verdict is-miss';
      verdict.replaceChildren(el('h3', {}, 'That is not a SHA-256 fingerprint.'), el('p', {}, 'A fingerprint has 64 characters, 0-9 and a-f.'));
      return;
    }
    if (DEMO) {
      verdict.className = 'verdict is-miss';
      verdict.replaceChildren(el('h3', {}, 'Verification needs a Couture server.'), el('p', {}, 'This page is running in demo mode; your fingerprint was computed on this device.'));
      return;
    }
    verdict.className = 'verdict';
    verdict.replaceChildren(el('p', {}, 'Consulting the registry…'));
    try {
      const design = await (await api(`/api/designs/by-hash/${hash}`)).json();
      if (seq !== lookupSeq) return;
      verdict.className = 'verdict is-match';
      verdict.replaceChildren(
        el('h3', {}, design.status === 'confirmed' ? 'Registered original.' : 'Registration in progress.'),
        el('dl', { class: 'facts' },
          filename ? [el('dt', {}, 'File'), el('dd', {}, filename)] : [],
          el('dt', {}, 'Piece'), el('dd', {}, design.title),
          el('dt', {}, 'Designer'), el('dd', {}, design.designer),
          el('dt', {}, 'Sealed'), el('dd', {}, formatDate(design.registered_at)),
          el('dt', {}, 'Fingerprint'), el('dd', {}, proof(design.sha256)),
          el('dt', {}, 'On-chain memo'), el('dd', {}, proof(design.memo)),
          el('dt', {}, 'Transaction'), el('dd', {}, proof(design.signature), design.explorer_url ? [' ', link(design.explorer_url, 'View on explorer')] : null)));
    } catch (error) {
      if (seq !== lookupSeq) return;
      verdict.className = 'verdict is-miss';
      verdict.replaceChildren(...(error.status === 404
        ? [el('h3', {}, 'No registered design matches.'),
          el('p', {}, 'This exact file has not been sealed with Couture. Any re-export, crop or compression changes the fingerprint, so ask the designer for the original file they sealed.')]
        : [el('h3', {}, 'The registry could not be reached.'), el('p', {}, explain(error, 'The lookup')),
          el('button', { type: 'button', class: 'button button-quiet', onclick: () => lookup(hash, filename) }, 'Try again')]));
    }
  }

  // ---- boot ---------------------------------------------------------------

  checkHealth();
  route();
})();
