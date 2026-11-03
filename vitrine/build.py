"""Gera a vitrine estática da Fase 0 a partir de vitrine/catalog.json.

    python vitrine/build.py            gera vitrine/site/
    python vitrine/build.py --strict   falha (código 1) se algo impede a publicação

Sem dependências além da biblioteca padrão. As páginas funcionam sem
JavaScript; assets/encomenda.js só melhora o pedido pelo WhatsApp.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from html import escape
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "site"
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MEDIDAS = {"busto": "Busto", "cintura": "Cintura", "quadril": "Quadril", "comprimento": "Comprimento", "dimensoes": "Dimensões"}

# Content hash per asset, appended as ?v=: browsers may cache assets for as
# long as they like, and every rebuild that changes a file changes its URL.
ASSET_VERSION: dict[str, str] = {}

# Prerender same-site pages on hover/touch, so clicks open instantly
# (Speculation Rules API; ignored by browsers without support).
SPECULATION = json.dumps({"prerender": [{"where": {"href_matches": "/*"}, "eagerness": "moderate"}]})

SERVICE_WORKER = """// Gerado por vitrine/build.py: não edite à mão.
// Precache de todas as páginas e assets desta versão: navegação instantânea
// e funcionamento offline. Cada build muda VERSION, e o cache antigo é apagado.
const VERSION = '__VERSION__';
const PRECACHE = __PRECACHE__;
const FONTS = 'couture-fonts';

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(VERSION).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(caches.keys()
    .then((keys) => Promise.all(keys.filter((k) => k !== VERSION && k !== FONTS).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);

  // Google Fonts: serve from cache, refresh in the background.
  if (url.hostname === 'fonts.googleapis.com' || url.hostname === 'fonts.gstatic.com') {
    event.respondWith(caches.open(FONTS).then(async (cache) => {
      const cached = await cache.match(request);
      const network = fetch(request).then((response) => {
        if (response.ok) cache.put(request, response.clone());
        return response;
      }).catch(() => cached);
      return cached || network;
    }));
    return;
  }
  if (url.origin !== self.location.origin) return;

  // Pages and assets of this version: cache first, network as fallback.
  event.respondWith(caches.match(request, { cacheName: VERSION }).then((cached) => cached || fetch(request).then((response) => {
    if (response.ok && url.pathname.startsWith(new URL(self.registration.scope).pathname)) {
      const copy = response.clone();
      caches.open(VERSION).then((cache) => cache.put(request, copy));
    }
    return response;
  }).catch(() => caches.match(new URL('index.html', self.registration.scope).href))));
});
"""


def asset(root: str, name: str) -> str:
    return f"{root}assets/{name}?v={ASSET_VERSION.get(name, '0')}"


def e(value: object) -> str:
    return escape(str(value), quote=True)


def brl(value: float) -> str:
    whole, cents = f"{value:,.2f}".split(".")
    whole = whole.replace(",", ".")
    return f"R$ {whole}" if cents == "00" else f"R$ {whole},{cents}"


# ---- validação ----------------------------------------------------------------


def validate(cat: dict) -> tuple[list[str], list[str]]:
    """(erros que impedem o build, avisos que impedem a publicação)."""
    errors: list[str] = []
    blockers: list[str] = []
    marca = cat["marca"]
    designers = {d["slug"]: d for d in cat["designers"]}
    for item in [*cat["designers"], *cat["pecas"]]:
        if not SLUG.match(item.get("slug", "")):
            errors.append(f"slug inválido: {item.get('slug')!r} (use minúsculas, números e hífens)")
    for peca in cat["pecas"]:
        if peca["designer"] not in designers:
            errors.append(f"{peca['slug']}: designer {peca['designer']!r} não existe")
        if not peca.get("tamanhos"):
            errors.append(f"{peca['slug']}: precisa de pelo menos um tamanho")
        if not isinstance(peca.get("preco"), (int, float)) or peca["preco"] <= 0:
            errors.append(f"{peca['slug']}: preço inválido")
        if not peca.get("fotos"):
            blockers.append(f"{peca['slug']}: sem fotos da piloto")
    for item in [*cat["designers"], *cat["pecas"]]:
        if item.get("exemplo"):
            blockers.append(f"{item['slug']}: conteúdo de exemplo")
    for field, why in (("whatsapp", "o botão Encomendar não funciona"),
                       ("cnpj", "o CDC exige identificar o fornecedor"),
                       ("razao_social", "o CDC exige identificar o fornecedor"),
                       ("email", "canal de contato obrigatório")):
        if not marca.get(field):
            blockers.append(f"marca.{field} vazio: {why}")
    blockers.append("textos de trocas e privacidade são rascunhos: revisar com advogado")
    return errors, blockers


# ---- peças de layout ------------------------------------------------------------


def head(title: str, description: str, root: str, canonical: str | None, extra: str = "") -> str:
    canon = f'<link rel="canonical" href="{e(canonical)}">' if canonical else ""
    return f"""<!DOCTYPE html>
<html lang="pt-BR" data-sw="{root}sw.js">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="view-transition" content="same-origin">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta name="theme-color" content="#f4efe6">
{canon}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;1,300;1,400&family=Jost:wght@300;400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{asset(root, 'vitrine.css')}">
<script type="speculationrules">{SPECULATION}</script>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' fill='%23f4efe6'/%3E%3Ctext x='32' y='45' font-family='Georgia,serif' font-size='38' fill='none' stroke='%231c1915' stroke-width='1.2' text-anchor='middle'%3EC%3C/text%3E%3C/svg%3E">
{extra}
</head>
<body>
<a class="skip" href="#conteudo">Pular para o conteúdo</a>"""


def masthead(root: str, current: str, marca: dict) -> str:
    # data-section names the home-page section that lights this item while it
    # is in view (assets/site.js); `current` marks the item for this page.
    def item(href: str, label: str, key: str, section: str) -> str:
        cur = ' aria-current="page"' if key == current else ""
        return f'<a href="{root}{href}" data-nav="{key}" data-section="{section}"{cur}>{label}</a>'
    contato = (f'<a class="masthead-contact" href="{e(whatsapp_url(marca, None))}">Encomendas pelo WhatsApp</a>'
               if marca.get("whatsapp") else '<span class="masthead-contact">Encomendas sob consulta</span>')
    return f"""
<header class="masthead">
  <a class="wordmark" href="{root}index.html" aria-label="{e(marca['nome'])}, início"><span class="wordmark-initial" aria-hidden="true">C</span><span aria-hidden="true">outure</span></a>
  <nav class="nav" aria-label="Principal">
    {item('index.html#colecao', 'Coleção', 'colecao', 'colecao')}
    {item('como-funciona/index.html', 'Como funciona', 'como-funciona', 'encomenda')}
    {item('index.html#designers', 'Designers', 'designers', 'designers')}
    <span class="nav-indicator" aria-hidden="true"></span>
  </nav>
  {contato}
</header>
<main id="conteudo">"""


def footer(root: str, marca: dict, *, order: bool = False) -> str:
    fornecedor = " · ".join(e(x) for x in (marca.get("razao_social"), marca.get("cnpj") and f"CNPJ {marca['cnpj']}", marca.get("endereco")) if x)
    contatos = []
    if marca.get("email"):
        contatos.append(f'<a href="mailto:{e(marca["email"])}">{e(marca["email"])}</a>')
    if marca.get("instagram"):
        handle = marca["instagram"].lstrip("@")
        contatos.append(f'<a href="https://instagram.com/{e(handle)}" rel="noopener">@{e(handle)}</a>')
    return f"""
</main>
<footer class="colophon">
  <div class="colophon-brand">
    <p class="colophon-name">{e(marca['nome'])}</p>
    <p>{e(marca['descricao'])}</p>
  </div>
  <nav class="colophon-links" aria-label="Institucional">
    <a href="{root}como-funciona/index.html">Como funciona</a>
    <a href="{root}como-funciona/index.html#trocas">Trocas e devoluções</a>
    <a href="{root}privacidade/index.html">Privacidade</a>
    {''.join(contatos)}
  </nav>
  <p class="colophon-legal">{fornecedor or 'Dados do fornecedor a definir (razão social, CNPJ e endereço).'}</p>
  <p class="colophon-legal">Você desenha? Estamos selecionando designers para as próximas coleções. Escreva para nós.</p>
</footer>
<script src="{asset(root, 'site.js')}" defer></script>
{f'<script src="{asset(root, "encomenda.js")}" defer></script>' if order else ''}
</body>
</html>
"""


def whatsapp_url(marca: dict, text: str | None) -> str:
    digits = re.sub(r"\D", "", marca.get("whatsapp") or "")
    base = f"https://wa.me/{digits}"
    return f"{base}?text={quote(text)}" if text else base


def exemplo(item: dict) -> str:
    return '<span class="exemplo" title="Conteúdo de exemplo: substitua antes de publicar">Exemplo</span>' if item.get("exemplo") else ""


def placeholder(label: str) -> str:
    return f"""<svg class="placeholder" viewBox="0 0 300 400" role="img" aria-label="{e(label)}">
  <rect x="0.5" y="0.5" width="299" height="399" class="ph-ground"/>
  <rect x="18.5" y="18.5" width="263" height="363" class="ph-rule"/>
  <text x="150" y="232" text-anchor="middle" class="ph-mark">C</text>
  <text x="150" y="350" text-anchor="middle" class="ph-note">Foto da piloto em breve</text>
</svg>"""


def photo(src: str | None, alt: str, root: str, *, eager: bool = False) -> str:
    if not src:
        return placeholder(alt)
    loading = 'fetchpriority="high"' if eager else 'loading="lazy"'
    return f'<img src="{root}{e(src)}" alt="{e(alt)}" {loading} decoding="async">'


def price_lines(peca: dict, marca: dict) -> str:
    preco = peca["preco"]
    lines = [f'<p class="price">{brl(preco)}</p>']
    terms = []
    if marca.get("parcelas_sem_juros", 1) > 1:
        n = marca["parcelas_sem_juros"]
        terms.append(f"em até {n}× de {brl(round(preco / n, 2))} sem juros")
    if marca.get("desconto_pix_percentual"):
        pix = round(preco * (1 - marca["desconto_pix_percentual"] / 100))
        terms.append(f"{brl(pix)} no Pix")
    if terms:
        lines.append(f'<p class="price-terms">{" · ".join(terms)}</p>')
    return "".join(lines)


def card(peca: dict, designer: dict, marca: dict, root: str) -> str:
    alt = f"{peca['nome']}, de {designer['nome']}"
    return f"""
<li class="card">
  <a href="{root}pecas/{peca['slug']}/index.html">
    <span class="card-frame">{photo((peca.get('fotos') or [None])[0], alt, root)}</span>
    <span class="card-meta">
      <span class="card-name">{e(peca['nome'])} {exemplo(peca)}</span>
      <span class="card-designer">{e(designer['nome'])}</span>
      <span class="card-price">{brl(peca['preco'])}</span>
    </span>
  </a>
</li>"""


STEPS = (
    ("Escolha", "Escolha a peça, o tamanho e as opções. Nada é cobrado no site."),
    ("Confirmação", "Pelo WhatsApp, confirmamos medidas, prazo e pagamento (Pix ou cartão)."),
    ("Feita para você", "A peça é cortada e costurada à mão depois do pagamento, em edição numerada."),
    ("Entrega", "Enviamos com rastreio, em embalagem Couture, com o cartão do designer."),
)


def steps(prazo: int) -> str:
    items = "".join(
        f'<li><span class="step-name">{e(name)}</span><span class="step-text">{e(text)}</span></li>'
        for name, text in STEPS)
    return f'<ol class="steps">{items}</ol><p class="steps-note">Prazo de produção de referência: cerca de {prazo} semanas.</p>'


# ---- páginas ----------------------------------------------------------------------


def page_home(cat: dict) -> str:
    marca, designers = cat["marca"], {d["slug"]: d for d in cat["designers"]}
    root = ""
    pecas = cat["pecas"]
    destaque = pecas[0] if pecas else None
    hero_media = ""
    if destaque:
        d = designers[destaque["designer"]]
        hero_media = f"""
  <figure class="hero-media">
    <a href="pecas/{destaque['slug']}/index.html">{photo((destaque.get('fotos') or [None])[0], f"{destaque['nome']}, de {d['nome']}", root, eager=True)}</a>
    <figcaption><a href="pecas/{destaque['slug']}/index.html">{e(destaque['nome'])}</a>, por {e(d['nome'])} · edição de {destaque['edicao']} peças</figcaption>
  </figure>"""
    cards = "".join(card(p, designers[p["designer"]], marca, root) for p in pecas)
    designer_items = "".join(f"""
<li class="designer">
  <a href="designers/{d['slug']}/index.html">
    <span class="designer-frame">{photo(d.get('foto'), d['nome'], root)}</span>
    <span class="designer-name">{e(d['nome'])} {exemplo(d)}</span>
    <span class="designer-meta">{e(d.get('formacao', ''))} · {e(d.get('cidade', ''))}</span>
  </a>
</li>""" for d in cat["designers"])
    body = f"""
<section class="hero">
  <div class="hero-copy">
    <h1 class="display">{e(marca['frase'])}</h1>
    <p class="lede">{e(marca['descricao'])}</p>
    <a class="button" href="#colecao">Ver a coleção</a>
  </div>{hero_media}
</section>

<section class="section" id="colecao" aria-labelledby="colecao-titulo">
  <h2 class="title" id="colecao-titulo">Coleção</h2>
  {'<ul class="grid">' + cards + '</ul>' if pecas else '<p class="empty">A primeira coleção está sendo produzida.</p>'}
</section>

<section class="section section-rule" id="encomenda" aria-labelledby="encomenda-titulo">
  <h2 class="title" id="encomenda-titulo">Como funciona a encomenda</h2>
  {steps(marca['prazo_padrao_semanas'])}
  <p><a class="text-link" href="como-funciona/index.html">Prazos, pagamento e trocas</a></p>
</section>

<section class="section section-rule" id="designers" aria-labelledby="designers-titulo">
  <h2 class="title" id="designers-titulo">Designers</h2>
  <p class="lede">Cada designer licencia seus desenhos para a Couture e recebe parte de cada peça vendida.</p>
  <ul class="designers">{designer_items}</ul>
</section>"""
    return (head(f"{marca['nome']} · {marca['frase']}", marca["descricao"], root, marca.get("url_publica"))
            + masthead(root, "", marca) + body + footer(root, marca))


def page_piece(peca: dict, cat: dict) -> str:
    marca, designers = cat["marca"], {d["slug"]: d for d in cat["designers"]}
    designer = designers[peca["designer"]]
    root = "../../"
    prazo = peca.get("prazo_semanas") or marca["prazo_padrao_semanas"]
    fotos = peca.get("fotos") or [None]
    gallery = "".join(
        f'<li class="gallery-item">{photo(src, f"{peca["nome"]}, foto {i + 1}", root, eager=i == 0)}</li>'
        for i, src in enumerate(fotos))

    sizes = "".join(f"""
<label class="chip"><input type="radio" name="tamanho" value="{e(t['tamanho'])}" required><span>{e(t['tamanho'])}</span></label>"""
                    for t in peca["tamanhos"])
    cols = [k for k in MEDIDAS if any(k in t for t in peca["tamanhos"])]
    table = ""
    if cols:
        header = "".join(f"<th scope=\"col\">{MEDIDAS[k]}{'' if k == 'dimensoes' else ' (cm)'}</th>" for k in cols)
        rows = "".join("<tr><th scope=\"row\">" + e(t["tamanho"]) + "</th>"
                       + "".join(f"<td>{e(t.get(k, '—'))}</td>" for k in cols) + "</tr>" for t in peca["tamanhos"])
        table = f"""
<details class="measures">
  <summary>Tabela de medidas</summary>
  <div class="table-wrap"><table><thead><tr><th scope="col">Tamanho</th>{header}</tr></thead><tbody>{rows}</tbody></table></div>
  <p class="fine">Medidas do corpo. Na dúvida entre dois tamanhos, fale com a gente antes de pagar: ajustamos na produção.</p>
</details>"""

    options = "".join(f"""
<fieldset class="option" data-option="{e(o['nome'])}">
  <legend>{e(o['nome'])}</legend>
  <div class="chips">{''.join(f'<label class="chip chip-text"><input type="radio" name="opcao-{i}" value="{e(v)}"{" checked" if j == 0 else ""}><span>{e(v)}</span></label>' for j, v in enumerate(o['valores']))}</div>
</fieldset>""" for i, o in enumerate(peca.get("opcoes", [])))

    base_text = f"Olá! Quero encomendar a peça {peca['nome']}, de {designer['nome']}."
    if marca.get("whatsapp"):
        cta = (f'<a class="button" id="encomendar" href="{e(whatsapp_url(marca, base_text))}" '
               f'data-base="{e(whatsapp_url(marca, None))}" rel="noopener">Encomendar pelo WhatsApp</a>')
    else:
        cta = '<span class="button is-disabled" aria-disabled="true">Encomendas em breve</span>'

    ld = {
        "@context": "https://schema.org", "@type": "Product", "name": peca["nome"],
        "description": peca["descricao"], "category": peca.get("categoria"),
        "brand": {"@type": "Brand", "name": marca["nome"]},
        "offers": {"@type": "Offer", "priceCurrency": "BRL", "price": peca["preco"],
                   "availability": "https://schema.org/PreOrder"},
    }
    if marca.get("url_publica"):
        ld["url"] = f"{marca['url_publica'].rstrip('/')}/pecas/{peca['slug']}/"
    jsonld = '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False).replace("</", "<\\/") + "</script>"

    body = f"""
<nav class="crumbs" aria-label="Você está em"><a href="{root}index.html#colecao">Coleção</a><span aria-hidden="true">/</span><span aria-current="page">{e(peca['nome'])}</span></nav>
<article class="piece">
  <ul class="gallery" aria-label="Fotos da peça">{gallery}</ul>
  <div class="piece-panel">
    <h1 class="title piece-title">{e(peca['nome'])} {exemplo(peca)}</h1>
    <p class="piece-designer">por <a href="{root}designers/{designer['slug']}/index.html">{e(designer['nome'])}</a></p>
    {price_lines(peca, marca)}
    <ul class="facts">
      <li>Feita para você em cerca de {prazo} semanas</li>
      <li>Edição limitada de {peca['edicao']} peças, numeradas</li>
    </ul>
    <form class="order" id="ficha" data-peca="{e(peca['nome'])}" data-designer="{e(designer['nome'])}" novalidate>
      <fieldset class="option">
        <legend>Tamanho</legend>
        <div class="chips">{sizes}</div>
      </fieldset>
      {table}
      {options}
      <div class="slip" aria-live="polite" hidden>
        <p class="slip-title">Sua ficha de encomenda</p>
        <p class="slip-text" id="slip-text"></p>
      </div>
      {cta}
      <p class="fine" id="order-note">Você confirma tamanho, prazo e pagamento com a gente antes de pagar. Nada é cobrado agora.</p>
    </form>
  </div>
</article>

<section class="section section-rule piece-details">
  <div>
    <h2 class="subtitle">Sobre a peça</h2>
    <p>{e(peca['descricao'])}</p>
  </div>
  <div>
    <h2 class="subtitle">Composição e cuidados</h2>
    <p>{e(peca['composicao'])}</p>
    <p>{e(peca['cuidados'])}</p>
  </div>
  <div class="about-designer">
    <h2 class="subtitle">Sobre {e(designer['nome'])}</h2>
    <p>{e(designer['bio'])}</p>
    <p><a class="text-link" href="{root}designers/{designer['slug']}/index.html">Ver todas as peças</a></p>
  </div>
</section>"""
    title = f"{peca['nome']}, de {designer['nome']} · {marca['nome']}"
    return (head(title, peca["descricao"], root, marca.get("url_publica") and f"{marca['url_publica'].rstrip('/')}/pecas/{peca['slug']}/", jsonld)
            + masthead(root, "", marca) + body + footer(root, marca, order=True))


def page_designer(designer: dict, cat: dict) -> str:
    marca = cat["marca"]
    root = "../../"
    pecas = [p for p in cat["pecas"] if p["designer"] == designer["slug"]]
    cards = "".join(card(p, designer, marca, root) for p in pecas)
    body = f"""
<nav class="crumbs" aria-label="Você está em"><a href="{root}index.html#designers">Designers</a><span aria-hidden="true">/</span><span aria-current="page">{e(designer['nome'])}</span></nav>
<section class="designer-intro">
  <div class="designer-portrait">{photo(designer.get('foto'), designer['nome'], root, eager=True)}</div>
  <div>
    <h1 class="title">{e(designer['nome'])} {exemplo(designer)}</h1>
    <p class="designer-meta">{e(designer.get('formacao', ''))} · {e(designer.get('cidade', ''))}</p>
    <p class="lede">{e(designer['bio'])}</p>
  </div>
</section>
<section class="section section-rule" aria-labelledby="pecas-titulo">
  <h2 class="title" id="pecas-titulo">Peças</h2>
  {'<ul class="grid">' + cards + '</ul>' if pecas else '<p class="empty">As primeiras peças estão em produção.</p>'}
</section>"""
    return (head(f"{designer['nome']} · {marca['nome']}", designer["bio"][:155], root, None)
            + masthead(root, "designers", marca) + body + footer(root, marca))


def page_how(cat: dict) -> str:
    marca = cat["marca"]
    root = "../"
    prazo = marca["prazo_padrao_semanas"]
    body = f"""
<article class="prose">
  <h1 class="title">Como funciona</h1>
  <p class="lede">Cada peça Couture é produzida depois da sua encomenda, a partir do desenho original do designer.</p>
  {steps(prazo)}

  <h2 class="subtitle">Prazo</h2>
  <p>O prazo de produção aparece em cada peça e é confirmado com você antes do pagamento. A referência é de cerca de {prazo} semanas, mais o tempo de entrega.</p>

  <h2 class="subtitle">Pagamento</h2>
  <p>Pix ou cartão de crédito, por link seguro do Mercado Pago enviado no atendimento.{f" No Pix, {marca['desconto_pix_percentual']}% de desconto." if marca.get('desconto_pix_percentual') else ''}{f" No cartão, em até {marca['parcelas_sem_juros']}× sem juros." if marca.get('parcelas_sem_juros', 1) > 1 else ''} Nenhum dado de cartão passa pela Couture.</p>

  <h2 class="subtitle">Tamanhos e ajustes</h2>
  <p>Cada peça tem uma tabela de medidas do corpo. Se você estiver entre dois tamanhos, fale com a gente antes de pagar.</p>

  <h2 class="subtitle" id="trocas">Trocas e devoluções</h2>
  <!-- RASCUNHO: revisar com advogado antes de publicar (CDC art. 49 e peças sob encomenda/personalizadas). -->
  <p>Você pode desistir da compra em até 7 dias após receber a peça, como prevê o Código de Defesa do Consumidor, com reembolso integral. Se houver qualquer defeito de produção, refazemos ou reembolsamos a peça.</p>

  <h2 class="subtitle">Designers</h2>
  <p>Os designers licenciam seus desenhos para a Couture e recebem parte de cada peça vendida. O desenho continua sendo deles e o nome deles acompanha cada peça.</p>
</article>"""
    return (head(f"Como funciona · {marca['nome']}", "Encomenda, prazo de produção, pagamento e trocas.", root, None)
            + masthead(root, "como-funciona", marca) + body + footer(root, marca))


def page_privacy(cat: dict) -> str:
    marca = cat["marca"]
    root = "../"
    body = f"""
<article class="prose">
  <h1 class="title">Privacidade</h1>
  <!-- RASCUNHO: revisar com advogado antes de publicar (LGPD). -->
  <p class="lede">Este site não usa cookies de rastreamento e não coleta dados pessoais.</p>
  <p>Quando você encomenda, os dados que você nos envia pelo WhatsApp (nome, contato, endereço de entrega e medidas) são usados apenas para produzir, cobrar e entregar a sua peça, e para emitir a nota fiscal. O pagamento é processado pelo Mercado Pago, que tem a própria política de privacidade.</p>
  <p>Guardamos esses dados pelo tempo exigido por lei para fins fiscais. Você pode pedir acesso, correção ou exclusão dos seus dados a qualquer momento{f' pelo e-mail {e(marca["email"])}' if marca.get('email') else ''}.</p>
</article>"""
    return (head(f"Privacidade · {marca['nome']}", "Como a Couture trata os seus dados.", root, None)
            + masthead(root, "", marca) + body + footer(root, marca))


# ---- build ------------------------------------------------------------------------


def write(path: Path, html: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def build(strict: bool = False) -> int:
    cat = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
    errors, blockers = validate(cat)
    if errors:
        print("ERROS (o site não foi gerado):", *errors, sep="\n  - ")
        return 2
    # Empty the output folder instead of deleting it: on Windows a preview
    # server running inside site/ keeps the folder itself locked.
    OUT.mkdir(exist_ok=True)
    for child in OUT.iterdir():
        shutil.rmtree(child) if child.is_dir() else child.unlink()
    shutil.copytree(ROOT / "assets", OUT / "assets")
    if (ROOT / "fotos").is_dir():
        shutil.copytree(ROOT / "fotos", OUT / "fotos")
    ASSET_VERSION.clear()
    for path in (ROOT / "assets").iterdir():
        ASSET_VERSION[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()[:10]

    pages = {"index.html": page_home(cat),
             "como-funciona/index.html": page_how(cat),
             "privacidade/index.html": page_privacy(cat)}
    for peca in cat["pecas"]:
        pages[f"pecas/{peca['slug']}/index.html"] = page_piece(peca, cat)
    for designer in cat["designers"]:
        pages[f"designers/{designer['slug']}/index.html"] = page_designer(designer, cat)
    for rel, html in pages.items():
        write(OUT / rel, html)

    # Service worker: precache every page, asset and photo of this build.
    precache = ["./", *pages, *(f"assets/{name}?v={v}" for name, v in sorted(ASSET_VERSION.items()))]
    if (OUT / "fotos").is_dir():
        precache += [p.relative_to(OUT).as_posix() for p in sorted((OUT / "fotos").rglob("*")) if p.is_file()]
    version = hashlib.sha256("".join(pages.values()).encode() + "".join(ASSET_VERSION.values()).encode()).hexdigest()[:12]
    write(OUT / "sw.js", SERVICE_WORKER.replace("__VERSION__", f"couture-{version}")
          .replace("__PRECACHE__", json.dumps(precache, ensure_ascii=False)))
    print(f"vitrine gerada em {OUT} ({len(pages)} páginas, cache {version})")
    if blockers:
        print("\nNÃO PUBLICAR AINDA:", *blockers, sep="\n  - ")
        return 1 if strict else 0
    print("pronta para publicar")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows consoles default to cp1252
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--strict", action="store_true", help="falha se algo impede a publicação")
    sys.exit(build(parser.parse_args().strict))
