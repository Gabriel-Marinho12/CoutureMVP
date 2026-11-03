# Couture: spec

> **Status:** v2, alinhado em 2026-11-03.
> Este documento substitui o direcionamento anterior ("registro de IP na
> Solana como produto principal") e a v1 deste spec (consignação). Quando
> houver conflito com `PRODUCT.md`, `CLAUDE.md` §1 ou briefs anteriores,
> **este spec vence** até que esses arquivos sejam atualizados.

---

## 1. O que a Couture é

**Uma marca e loja de roupas de luxo que transforma desenhos de designers
independentes em peças feitas sob encomenda.** Os designers são estudantes
de moda, artistas e criadores autorais sem estrutura de produção.

O site existe para **vender roupas**. Os outros elementos são diferenciais e
não são o produto principal:

| Elemento | Papel | Quando |
|---|---|---|
| Coleções sob encomenda de designers independentes | **Produto principal** | Fase 0 |
| Licença com royalty: o designer ganha com cada venda | Proposta ao designer | Fase 0 |
| Proteção da arte contra cópia (sigilo e arte protegida no site) | Diferencial ao designer | Fase 0 (contratos), Fase 1 (site) |
| Consultoria de marca para o designer | Linha de negócio futura | Fase 2 |
| Registro on-chain e certificado de autenticidade | Rastreabilidade da peça | Fase 2 |

### O problema que define o modelo
Os designers que a Couture quer atender **têm o desenho, não a peça.**
Exigir a peça pronta excluiria quase todos. Por isso a Couture assume o
caminho do desenho até a roupa e o designer licencia o design.

### Para quem
- **Cliente:** brasileiro que compra moda autoral de luxo e **aceita esperar
  algumas semanas** por uma peça feita para ele. Quer exclusividade, a
  história por trás da peça e uma compra confiável.
- **Designer:** tem talento e desenhos, mas não tem capital, ateliê nem
  marca. Quer ver o trabalho virar produto, receber por isso e não ter a
  ideia copiada.

---

## 2. Modelo de negócio

### 2.1 Coleções sob encomenda
1. **Curadoria.** A Couture seleciona os desenhos com mais potencial. Nem
   tudo entra, e isso faz parte do luxo.
2. **O designer entrega a ficha técnica:**
   - desenho técnico de frente e costas;
   - medidas principais;
   - tecido sugerido;
   - aviamentos (zíper, botões, forro);
   - detalhes de acabamento.

   É requisito da candidatura e funciona como filtro de seriedade.
3. **A Couture desenvolve uma vez por design:** modelagem profissional (§2.4)
   e uma peça-piloto. A piloto é aprovada pela Couture, não só pelo designer,
   e fotografada. **A foto da piloto é a foto da loja.** Não há estoque.
4. **Venda sob encomenda em tamanhos padrão**, com prazo de produção
   declarado (referência: cerca de 4 semanas). Só se produz depois do
   pagamento.
5. **Personalização a partir de um cardápio fechado:** tecido entre opções
   definidas, cor, comprimento, iniciais bordadas, numeração da edição
   ("peça 7 de 30"). Não há personalização livre. O sob medida com prova
   presencial é uma linha futura ("atelier").
6. **Edição limitada por design** (ex.: 30 peças), numerada.

### 2.2 Licença com royalty
- **Autoria e crédito:** o designer continua autor e é creditado sempre.
- **Licença:** a Couture recebe a licença para produzir e vender o design,
  com **exclusividade por um prazo** (referência: 2 anos).
- **Retorno dos direitos:** se a peça não vender num prazo combinado, os
  direitos voltam ao designer.
- **Royalty: 35–40% da margem por peça, desde a primeira venda.**
  - **Margem por peça** é o preço de venda menos produção da peça (costura,
    tecido, aviamentos, acabamento), taxas de pagamento, embalagem e frete
    subsidiado.
  - **Não é o lucro da empresa no mês.** O lucro desconta salários e
    marketing, pode ser zero no começo e o designer não consegue auditar.
  - Exemplo hipotético: preço de R$ 1.800 dá margem de cerca de R$ 1.030, e
    o designer recebe de R$ 360 a 410 por peça, cerca de 20–23% do preço.
    Isso fica acima do licenciamento comum de moda, que costuma ser de 5% a
    15%.
- **Transparência:** preço definido em comum acordo e extrato por venda com
  os custos descontados.
- **Molde:** o molde pertence à Couture (que paga por ele) enquanto durar a
  licença. O contrato define o que acontece ao fim.
- **Contratos com advogado (não improvisar):**
  - licença com royalty;
  - termo de sigilo com modelista e ateliê, porque o desenho passa por
    terceiros, que é exatamente o caminho por onde designs são copiados;
  - termos de venda.

### 2.3 Riscos assumidos conscientemente
- **Quem paga a piloto é a Couture.** Design que não vende é custo perdido, e
  a Fase 0 existe para medir esse risco.
- **Dependência do parceiro de produção:** é o maior risco operacional. Antes
  de escalar, ter pelo menos dois parceiros.
- **Prazo de semanas:** precisa ser comunicado com clareza em toda a jornada.
  O posicionamento "feito para você" justifica a espera.
- **Cartão parcelado:** a Couture recebe aos poucos, mas paga a produção
  agora. Por isso há desconto no Pix e capital de giro reservado.
- **Devolução de peça feita sob encomenda:** o direito de arrependimento de
  7 dias (CDC art. 49) vale para compras online. A aplicação a peças
  personalizadas é discutível. **Validar com advogado** e deixar a regra
  explícita antes da compra.

### 2.4 Papéis na cadeia

| Papel | Faz | Por que é necessário |
|---|---|---|
| Designer | Desenho e ficha técnica | A ideia e a autoria. |
| **Modelista** | Transforma a ficha técnica nos **moldes**, as peças de papel ou CAD que serão cortadas no tecido. Define caimento, folgas e costuras, gradua os tamanhos e acompanha as provas da piloto. | Sem molde não há peça reproduzível. A costureira improvisaria, e cada unidade sairia diferente. Uma "edição de 30" exige 30 peças idênticas. |
| Costureira ou ateliê | Corta e costura a piloto e cada peça vendida | O acabamento é o luxo. |
| Couture | Curadoria, aprovação de qualidade, foto, venda, atendimento, entrega, royalty | Dona da marca e da experiência. |

---

## 3. Fases

### Fase 0: validação (≈ 10–12 semanas, R$ 10.000)
**Pergunta a responder:** a Couture consegue produzir peças com qualidade de
luxo a partir de desenhos de estudantes e vendê-las sob encomenda, com
margem que paga o royalty?

| Semanas | Etapa |
|---|---|
| 1–2 | Encontrar o parceiro de produção (§3.1). Pedir orçamento de piloto e calibrar a tabela §3.2. Preparar os contratos modelo. |
| 2–3 | Chamada de designers em escolas de moda de SJC e SP. Escolher **2 designers com 2 desenhos cada**, de complexidade simples a média. |
| 3–7 | Modelagem, pilotos e provas, com acompanhamento presencial. |
| 7–8 | Fotografia das pilotos. Publicar a **vitrine** (§4). |
| 8–12 | Venda sob encomenda (Instagram, WhatsApp, link de pagamento Mercado Pago). Produção e entrega de cada pedido. |

**Critérios de sucesso (ajustáveis):**
- pelo menos 8 encomendas pagas em 4 semanas, somando as 4 peças;
- margem real igual ou maior que a planejada;
- prazo cumprido;
- nenhuma devolução por defeito;
- os 2 designers querem continuar.

**Se atingidos, vale investir na Fase 1. Se não, ajustar preço, peças ou
posicionamento antes de construir mais software.**

#### 3.1 Onde produzir
- **Pilotos:** de preferência **em São José dos Campos ou perto**. A piloto
  exige provas e correções presenciais, e a proximidade vale mais que o
  preço nesta fase.
- **Escala (Fase 1+):** São Paulo capital.
  - Bom Retiro: modelistas, oficinas, confecções.
  - Brás: tecidos e aviamentos.
  - Escolas técnicas de moda (Senai, Senac): indicação de modelistas.
- Alternativa para a Fase 0: ateliês de sob medida e de noivas, acostumados
  com acabamento de luxo.

#### 3.2 Orçamento da Fase 0

| Item | Valor | O que cobre |
|---|---|---|
| Desenvolvimento de 4 peças | R$ 4.000 | ≈ R$ 1.000 por peça: modelagem (≈ 300), costura da piloto (≈ 300), tecido e aviamentos (≈ 250), um ajuste (≈ 150). A ficha técnica vem do designer. |
| Fotografia | R$ 1.500 | Uma sessão com fotógrafo, modelo e tratamento. |
| Jurídico | R$ 1.200 | Licença com royalty, termo de sigilo, termos de venda. |
| Embalagem de luxo | R$ 500 | Caixa, papel de seda, cartão com a história da peça e do designer. |
| Divulgação | R$ 800 | Anúncios no Instagram durante a venda. |
| Deslocamentos | R$ 500 | Provas e compra de tecido. |
| Capital de giro | R$ 700 | Produção quando a venda é parcelada. |
| Reserva | R$ 800 | Segunda piloto, tecido mais caro, peça refeita. |
| **Total** | **R$ 10.000** | |

Valores são **estimativas de ordem de grandeza** até o primeiro orçamento
real. Se a modelagem vier acima, reduzir para 3 peças em vez de cortar foto
ou contratos. A produção de cada peça vendida não entra aqui: o cliente paga
antes.

### Fase 1: loja própria (só após a Fase 0 dar certo)
Loja completa construída pela Couture:
- FastAPI com PostgreSQL e páginas renderizadas no servidor (SEO);
- checkout com Pix e cartão parcelado via Mercado Pago, atrás de uma
  interface `PaymentProvider`;
- frete via Melhor Envio;
- NF-e via provedor de emissão, escolhido com o contador;
- painel administrativo interno.

**Particularidades de sob encomenda que mudam o software:**
- prazo de produção por produto, exibido antes da compra;
- pedido com etapas de produção:
  1. `pago`
  2. `em_producao`
  3. `pronto`
  4. `enviado`
  5. `entregue`
- opções de personalização com regras de preço;
- numeração da edição atribuída na compra;
- **royalty** por designer calculado sobre a margem de cada pedido, com
  extrato;
- **sem estoque físico:** o limite é a edição e a capacidade de produção por
  semana.

**Requisitos não funcionais herdados da v1:**
- SEO, com páginas no servidor e `schema.org/Product`;
- celular primeiro;
- WCAG 2.1 AA;
- CDC (preço total, arrependimento, dados do fornecedor), LGPD;
- tokenização de cartão (PCI SAQ-A) e webhooks assinados;
- preço sempre recalculado no servidor;
- regras de segurança do `CLAUDE.md` §3;
- textos extraídos para tradução.

### Fase 2
- consultoria de marca e candidatura online de designers;
- registro on-chain e certificado de autenticidade (módulo Solana atual,
  congelado);
- conta de cliente;
- linha "atelier" sob medida com prova presencial;
- inglês e venda internacional.

---

## 4. Vitrine da Fase 0 (em construção: `vitrine/`)

**Objetivo:** apresentar a marca, os designers e as peças com rigor de luxo e
levar o cliente a **encomendar com atendimento pessoal**. Não há checkout
próprio: o pedido é fechado pelo WhatsApp e pago por link do Mercado Pago.

- **Site estático**, gerado por um script Python sem dependências
  (`vitrine/build.py`) a partir de um catálogo editável
  (`vitrine/catalog.json`).
- **Hospedagem:** GitHub Pages. Funciona sem JavaScript. O JS só melhora o
  pedido, preenchendo tamanho e opção na mensagem.
- **Páginas:**
  - home: peças da coleção, como funciona a encomenda, designers;
  - página de cada peça:
    - fotos e preço (parcelado e Pix);
    - edição limitada e prazo de produção;
    - tamanhos com tabela de medidas e opções de personalização;
    - composição e cuidados;
    - sobre o designer;
    - botão **Encomendar**;
  - página de cada designer;
  - "Como funciona" (encomenda, prazo, pagamento, entrega, trocas);
  - privacidade.
- **Visual:** sistema Maison Archive (`DESIGN.md`) com as correções de
  contraste da crítica (texto secundário e bronze pequeno em AA).
- **Fotos de produto são normais:** nítidas e sem embaralhamento. A proteção
  da arte em alta resolução volta na Fase 1.
- **Conteúdo real é obrigatório antes de publicar.** Entradas marcadas
  `"exemplo": true` no catálogo aparecem com o selo "Exemplo" e não podem ir
  ao ar. Textos legais são **rascunhos** até revisão do advogado.

---

## 5. Onde a IA ajuda (e onde não)

| Etapa | IA ajuda? | Como | Limite |
|---|---|---|---|
| Escolher quais desenhos desenvolver | **Sim, pode cortar custo** | Gerar ilustrações realistas da peça a partir do desenho para testar interesse (enquete, lista de espera) **antes** de pagar a piloto. | Rotular como ilustração, nunca como foto da peça. Publicidade enganosa é risco pelo CDC. |
| Ficha técnica | Parcial | Organizar a ficha a partir das anotações do designer, revisar medidas e aviamentos faltantes. | O desenho técnico continua responsabilidade do designer. |
| Modelagem | Não substitui | CAD de moda (Audaces, CLO 3D) acelera o molde e a gradação. Simulação 3D reduz o número de pilotos físicas. | O caimento de luxo ainda exige modelista e prova em corpo real. |
| Peça-piloto | Não substitui | A simulação 3D pode evitar uma segunda piloto. | A peça física é a foto da loja e o teste de qualidade. |
| Fotografia | Só apoio | Moodboard e direção de arte. | Foto de produto deve ser real: luxo vive de confiança. |
| Textos (descrições, histórias, e-mails, inglês) | **Sim, quase todo** | Rascunho de descrições, histórias dos designers e traduções. | Revisão humana do tom. |
| Contratos | Parcial, reduz horas de advogado | Primeiro rascunho a partir das regras do §2.2. | Revisão e assinatura com advogado. |
| Atendimento (WhatsApp) | Depois | Respostas sobre prazo, tamanho e cuidados. | Na Fase 0 o atendimento pessoal é parte do luxo. |
| Proteção contra cópia | Futuro | Busca reversa de imagens para achar cópias das peças. | Fase 2. |
| Curadoria de designers | Não | É o julgamento da marca. | |

---

## 6. O que acontece com o código atual

| Parte | Destino |
|---|---|
| `backend/` (FastAPI, Solana, Metaplex, segurança) | **Congelado** para a Fase 2. Os testes continuam passando. As regras de segurança e o padrão de idempotência são reaproveitados na Fase 1. |
| `frontend/` (SPA Archive, Register, Verify) | **Congelado.** O visualizador protegido (`viewer.js`) volta na Fase 1 para a arte em alta resolução. |
| `vitrine/` | **Novo.** Site da Fase 0 (§4). |
| `DESIGN.md` | Base visual. Atualizar com os componentes da loja e as correções de contraste após a vitrine. |
| `PRODUCT.md`, `CLAUDE.md` §1 | Reescrever a partir deste spec. |
| `.impeccable/critique`, brief "Um campo só" | Obsoletos. Ficam como histórico. |

---

## 7. Decisões em aberto
1. **Parceiro de produção:** modelista e costureira ou ateliê (Fase 0,
   semanas 1–2).
2. **Contador:** regime tributário da Couture, NF-e, forma de pagar o
   royalty a designer pessoa física (RPA ou MEI).
3. **Advogado:** contratos do §2.2 e regra de devolução para peça sob
   encomenda.
4. **Política comercial:** desconto no Pix, parcelas sem juros, frete,
   tamanho da edição, prazo de produção declarado.
5. **Prazo de exclusividade e de retorno dos direitos** na licença.
6. **Nome da marca:** "Couture" continua?
7. **Dados do fornecedor para o rodapé** (CNPJ, endereço), exigidos pelo
   CDC.
