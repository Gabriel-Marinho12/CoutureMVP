// Protected rendering for Couture designs.
//
// The server sends each design as a shuffled tile sprite plus the tile
// order. It is decoded straight into an ImageBitmap (never an <img>, never a
// URL), reassembled on a canvas, and overlaid with a per-session watermark.
// Pixel read-back APIs are disabled on protected canvases, and the browser's
// save, drag, copy and print paths are closed.
//
// This deters casual saving and generic scrapers. Screenshots cannot be
// prevented on the web; the on-chain registration is what proves authorship.
(function () {
  'use strict';

  const SESSION = (crypto.randomUUID ? crypto.randomUUID() : String(Math.random()).slice(2)).slice(0, 8).toUpperCase();

  async function bitmapFromSprite(base64) {
    const bytes = Uint8Array.from(atob(base64), (c) => c.charCodeAt(0));
    return createImageBitmap(new Blob([bytes], { type: 'image/webp' }));
  }

  // Demo mode only: shuffle a plain image client-side so the same renderer applies.
  async function viewFromImageUrl(url, grid = 8) {
    const image = new Image();
    image.referrerPolicy = 'no-referrer';
    image.src = url;
    await image.decode();
    const tileW = Math.floor(image.naturalWidth / grid);
    const tileH = Math.floor(image.naturalHeight / grid);
    const order = [...Array(grid * grid).keys()].sort(() => Math.random() - 0.5);
    const sprite = new OffscreenCanvas(tileW * grid, tileH * grid);
    const ctx = sprite.getContext('2d');
    order.forEach((slot, tile) => {
      ctx.drawImage(image,
        (tile % grid) * tileW, Math.floor(tile / grid) * tileH, tileW, tileH,
        (slot % grid) * tileW, Math.floor(slot / grid) * tileH, tileW, tileH);
    });
    return { bitmap: sprite.transferToImageBitmap(), order, cols: grid, rows: grid, width: tileW * grid, height: tileH * grid };
  }

  async function viewFromApi(payload) {
    return { ...payload, bitmap: await bitmapFromSprite(payload.sprite) };
  }

  function render(canvas, view, { watermark = true, cssWidth } = {}) {
    harden(canvas);
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    const displayWidth = cssWidth || view.width;
    const scale = (displayWidth * ratio) / view.width;
    canvas.width = Math.round(view.width * scale);
    canvas.height = Math.round(view.height * scale);
    canvas.style.aspectRatio = `${view.width} / ${view.height}`;

    const ctx = canvas.getContext('2d', { willReadFrequently: false });
    ctx.imageSmoothingQuality = 'high';
    const tileW = view.width / view.cols;
    const tileH = view.height / view.rows;
    const pad = view.pad || 0;
    // Integer destination edges shared by neighbouring tiles: no gaps, no overlaps.
    const edgeX = (i) => Math.round((i * canvas.width) / view.cols);
    const edgeY = (i) => Math.round((i * canvas.height) / view.rows);
    view.order.forEach((slot, tile) => {
      const col = tile % view.cols;
      const row = Math.floor(tile / view.cols);
      const sx = (slot % view.cols) * (tileW + 2 * pad) + pad;
      const sy = Math.floor(slot / view.cols) * (tileH + 2 * pad) + pad;
      const dx = edgeX(col);
      const dy = edgeY(row);
      ctx.drawImage(view.bitmap, sx, sy, tileW, tileH, dx, dy, edgeX(col + 1) - dx, edgeY(row + 1) - dy);
    });
    if (watermark) drawWatermark(ctx, canvas.width, canvas.height);
  }

  function drawWatermark(ctx, width, height) {
    const stamp = `COUTURE · ${SESSION} · ${new Date().toISOString().slice(0, 10)}`;
    const size = Math.max(10, Math.round(width / 70));
    ctx.save();
    ctx.font = `400 ${size}px Jost, sans-serif`;
    ctx.fillStyle = 'rgba(236, 230, 218, 0.055)';
    ctx.translate(width / 2, height / 2);
    ctx.rotate(-Math.PI / 6);
    const stepX = ctx.measureText(stamp).width + size * 6;
    const stepY = size * 9;
    const reach = Math.hypot(width, height);
    for (let y = -reach; y < reach; y += stepY) {
      for (let x = -reach + ((y / stepY) % 2) * (stepX / 2); x < reach; x += stepX) ctx.fillText(stamp, x, y);
    }
    ctx.restore();
  }

  const hardened = new WeakSet();
  function harden(canvas) {
    if (hardened.has(canvas)) return;
    hardened.add(canvas);
    const refuse = () => { throw new DOMException('Protected by Couture', 'SecurityError'); };
    Object.defineProperties(canvas, {
      toDataURL: { value: refuse },
      toBlob: { value: refuse },
      captureStream: { value: refuse },
      transferControlToOffscreen: { value: refuse },
    });
    const ctx = canvas.getContext('2d');
    Object.defineProperty(ctx, 'getImageData', { value: refuse });
    ['contextmenu', 'dragstart', 'selectstart', 'copy'].forEach((type) =>
      canvas.addEventListener(type, (event) => event.preventDefault()));
  }

  // Page-wide guards, active while the document shows protected work.
  function installGuards({ onExposure } = {}) {
    const block = (event) => {
      if (event.target.closest && event.target.closest('input, textarea')) return;
      event.preventDefault();
    };
    ['contextmenu', 'dragstart', 'copy', 'cut'].forEach((type) => document.addEventListener(type, block));

    document.addEventListener('keydown', (event) => {
      const key = event.key.toLowerCase();
      const mod = event.metaKey || event.ctrlKey;
      if ((mod && ['s', 'p', 'u'].includes(key)) || (mod && event.shiftKey && ['i', 'j', 'c', 's'].includes(key)) || key === 'f12') {
        event.preventDefault();
      }
      if (key === 'printscreen') {
        onExposure?.();
        navigator.clipboard?.writeText('').catch(() => {});
      }
    });
    document.addEventListener('keyup', (event) => {
      if (event.key.toLowerCase() === 'printscreen') navigator.clipboard?.writeText('').catch(() => {});
    });
  }

  window.CoutureCanvas = { render, viewFromApi, viewFromImageUrl, installGuards, session: SESSION };
})();
