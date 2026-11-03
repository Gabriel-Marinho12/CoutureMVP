// Ficha de encomenda: monta a mensagem do WhatsApp a partir do tamanho e das
// opções escolhidas. Sem este script a página continua funcionando: o botão
// abre o WhatsApp com o nome da peça e o tamanho é combinado na conversa.
(function () {
  'use strict';
  const form = document.getElementById('ficha');
  const button = document.getElementById('encomendar');
  if (!form) return;

  const slip = form.querySelector('.slip');
  const slipText = document.getElementById('slip-text');
  const note = document.getElementById('order-note');
  const defaultNote = note.textContent;
  const sizes = [...form.querySelectorAll('input[name="tamanho"]')];
  if (sizes.length === 1) sizes[0].checked = true;

  function choices() {
    const size = form.querySelector('input[name="tamanho"]:checked')?.value || null;
    const options = [...form.querySelectorAll('fieldset[data-option]')].map((set) => [
      set.dataset.option,
      set.querySelector('input:checked')?.value,
    ]).filter(([, value]) => value);
    return { size, options };
  }

  function update() {
    const { size, options } = choices();
    const parts = [size ? `Tamanho ${size}` : 'Tamanho a escolher', ...options.map(([name, value]) => `${name}: ${value}`)];
    slip.hidden = false;
    slipText.textContent = `${form.dataset.peca} · ${parts.join(' · ')}`;
    if (!button) return;
    const message = [
      `Olá! Quero encomendar a peça ${form.dataset.peca}, de ${form.dataset.designer}.`,
      size ? `Tamanho: ${size}.` : null,
      ...options.map(([name, value]) => `${name}: ${value}.`),
    ].filter(Boolean).join('\n');
    button.href = `${button.dataset.base}?text=${encodeURIComponent(message)}`;
    button.classList.toggle('is-waiting', !size);
    if (size) {
      note.textContent = defaultNote;
      note.classList.remove('is-error');
    }
  }

  form.addEventListener('change', update);
  button?.addEventListener('click', (event) => {
    if (choices().size) return;
    event.preventDefault();
    note.textContent = 'Escolha um tamanho para encomendar.';
    note.classList.add('is-error');
    sizes[0]?.focus();
  });
  update();
})();
