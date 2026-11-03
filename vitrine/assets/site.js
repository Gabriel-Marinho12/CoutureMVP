// Couture · navegação fluida.
// 1. Um único filete bronze desliza entre os itens do menu, seguindo o clique
//    e a seção visível na rolagem (scroll-spy).
// 2. Mede a barra do topo para a rolagem suave parar logo abaixo dela.
// 3. Registra o service worker (cache para navegação instantânea).
(function () {
  'use strict';
  document.documentElement.classList.add('js');

  const masthead = document.querySelector('.masthead');
  const nav = document.querySelector('.nav');
  const indicator = nav?.querySelector('.nav-indicator');
  const links = nav ? [...nav.querySelectorAll('a[data-nav]')] : [];

  // ---- altura da barra (para scroll-padding) ----------------------------------
  const setMastheadHeight = () => {
    if (masthead) document.documentElement.style.setProperty('--masthead-h', `${masthead.offsetHeight}px`);
  };
  setMastheadHeight();
  new ResizeObserver(setMastheadHeight).observe(masthead);

  // ---- filete deslizante ------------------------------------------------------
  let current = links.find((a) => a.hasAttribute('aria-current')) || null;

  function place(link) {
    if (!indicator) return;
    if (!link) { indicator.classList.remove('is-on'); return; }
    const navBox = nav.getBoundingClientRect();
    const box = link.getBoundingClientRect();
    indicator.style.setProperty('--ind-x', `${box.left - navBox.left}px`);
    indicator.style.setProperty('--ind-w', `${box.width}px`);
    indicator.classList.add('is-on');
  }

  function activate(link, { kind = 'location' } = {}) {
    if (link === current) return;
    links.forEach((a) => { if (a !== link) a.removeAttribute('aria-current'); });
    if (link) link.setAttribute('aria-current', kind);
    current = link;
    place(link);
  }

  place(current);
  // Ativa a transição só depois do primeiro posicionamento (sem "voo" ao carregar).
  requestAnimationFrame(() => requestAnimationFrame(() => indicator?.classList.add('is-ready')));
  window.addEventListener('resize', () => place(current));
  document.fonts?.ready.then(() => place(current));

  // ---- acompanhamento da rolagem (só na página com as seções) ----------------
  const sections = links
    .map((a) => ({ link: a, el: a.dataset.section && document.getElementById(a.dataset.section) }))
    .filter((s) => s.el);

  if (sections.length) {
    const hero = document.querySelector('.hero');
    const visible = new Map();
    let clickLock = 0;

    const pick = () => {
      if (Date.now() < clickLock) return;
      // A seção cujo topo passou mais recentemente pela faixa de leitura.
      let best = null;
      for (const s of sections) if (visible.get(s.el)) best = s;
      activate(best ? best.link : null);
    };

    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) visible.set(entry.target, entry.isIntersecting);
      pick();
    }, { rootMargin: '-35% 0px -60% 0px' });
    sections.forEach((s) => observer.observe(s.el));
    if (hero) observer.observe(hero);

    // Clique: o filete vai imediatamente para o destino e o scroll-spy espera
    // a rolagem suave terminar, para não fazer o filete passear pelo caminho.
    links.forEach((link) => link.addEventListener('click', () => {
      const target = sections.find((s) => s.link === link);
      if (!target) return;
      activate(link);
      clickLock = Date.now() + 900;
    }));
    window.addEventListener('scrollend', () => { clickLock = 0; pick(); });
  }

  // ---- service worker ---------------------------------------------------------
  if ('serviceWorker' in navigator && document.documentElement.dataset.sw) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register(document.documentElement.dataset.sw).catch(() => { /* sem cache offline */ });
    });
  }
})();
