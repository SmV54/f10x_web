# -*- coding: utf-8 -*-
"""Monta o HTML da demonstração comercial a partir do inventário + prints.

Por que é gerado e não escrito à mão: são 109 telas. Um HTML manual ficaria
desatualizado no dia em que uma tela entrasse no menu, e ninguém perceberia
— a demo continuaria vendendo o sistema de ontem. Aqui a fonte é sempre o
_demo_telas.json, que por sua vez sai do menu de verdade.

Roda sem os prints: as telas que faltam viram moldura vazia com o nome. Isso
permite ver a estrutura e o ritmo antes de capturar nada.

Entra:  _demo_telas.json           (python _demo_inventario.py)
        static/demo/*.jpg          (python _demo_capturar.py)
        _demo_tempos.json          (python _demo_narracao.py)
Sai:    demo_comercial.html

Rodar:  python _demo_montar.py
"""

import io
import json
import os
import re
import unicodedata

INVENTARIO = "_demo_telas.json"
TEMPOS = "_demo_tempos.json"
PASTA_PRINTS = os.path.join("static", "demo")
SAIDA = "demo_comercial.html"

# Conexões não tem nenhuma tela pronta e Diversos tem 1 de 5. Módulo vazio num
# vídeo de venda joga contra, então os dois saem do corpo e viram uma frase de
# promessa no fecho. Para mostrá-los assim mesmo, basta esvaziar este conjunto.
MODULOS_NO_FECHO = {"conexoes", "diversos"}

# Tela que aparece em tamanho cheio, com digitação simulada, em cada módulo.
# É a mais representativa — a que o cliente reconhece como "o sistema".
DESTAQUE = {
    "cadastros":     "/cad_funcionario",
    "novafolha":     "/cad_anomes",
    "eventuais":     "/calc_ferias",
    "movimento":     "/cad_mov",
    "movimentofixo": "/mov_fixo",
    "calculo":       "/calcular_folha",
    "relatorios":    "/resumo_folha",
    "esocial":       "/esocial_fila",
}

# O que é digitado na tela de destaque: (rótulo do campo, texto). O cartão é
# desenhado por cima do print — não tenta acertar a posição do campo real,
# que mudaria a cada captura.
DIGITACAO = {
    "cadastros":     [("CPF", "123.456.789-09"), ("Nome", "MARIA SOUZA LIMA")],
    "novafolha":     [("Mês/Ano", "08/2026")],
    "eventuais":     [("Início das férias", "01/09/2026"), ("Dias", "30")],
    "movimento":     [("Verba", "0011 Horas Extras"), ("Quantidade", "12,50")],
    "movimentofixo": [("Verba", "0033 Vale Transporte"), ("Valor", "180,00")],
    "calculo":       [("Competência", "07/2026")],
    "relatorios":    [("Período", "07/2026")],
    "esocial":       [("Evento", "S-1200 Remuneração")],
}

# Segundos de cada parte do bloco de um módulo. Só valem enquanto não houver
# narração: quando o _demo_tempos.json existe, quem manda é a fala -- cada
# fase dura o que a frase dela durou. Antes disso os tempos eram fixos e
# Movimento Fixo, com 3 telas, ficava tanto no ar quanto Eventuais, com 36.
T_GAVETA, T_MOSAICO, T_TELA = 12, 10, 20
T_ABERTURA, T_FECHO = 24, 22


def tempos_da_voz():
    """Os tempos medidos na narração, por chave de cena. {} se não houver."""
    if not os.path.exists(TEMPOS):
        return {}
    d = json.load(io.open(TEMPOS, encoding="utf-8"))
    return {s["chave"]: s for s in d["slides"]}


def slug(texto):
    t = unicodedata.normalize("NFD", texto)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", t.lower())).strip("_")


def arquivo_do(tela):
    return os.path.join(PASTA_PRINTS, "%s_%s.jpg"
                        % (tela["modulo"], slug(tela["href"])))


def esc(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def img_ou_moldura(tela, classe="tiro"):
    """<img> quando o print existe; moldura com o nome quando não."""
    caminho = arquivo_do(tela)
    if os.path.exists(caminho):
        return ('<div class="%s"><img src="/%s" alt="%s" loading="lazy"></div>'
                % (classe, caminho.replace("\\", "/"), esc(tela["nome"])))
    return ('<div class="%s falta"><span>%s</span></div>'
            % (classe, esc(tela["nome"])))


def bloco_gaveta(mod, telas):
    """A gaveta do módulo aberta, com as seções e todos os itens."""
    secoes, ordem = {}, []
    for t in telas:
        if t["secao"] not in secoes:
            secoes[t["secao"]] = []
            ordem.append(t["secao"])
        secoes[t["secao"]].append(t)
    partes = []
    for nome in ordem:
        itens = "".join(
            '<li%s>%s %s</li>' % (" class=\"nao\"" if not t["ok"] else "",
                                  esc(t["icone"]), esc(t["nome"]))
            for t in secoes[nome])
        partes.append('<div class="secao"><h4>%s</h4><ul>%s</ul></div>'
                      % (esc(nome or "Geral"), itens))
    return ('<div class="gaveta"><div class="gaveta-cab">%s %s</div>'
            '<div class="gaveta-corpo">%s</div></div>'
            % (esc(mod["icone"]), esc(mod["titulo"]), "".join(partes)))


def bloco_mosaico(telas):
    """Todas as telas do módulo em miniatura, entrando em cascata."""
    prontas = [t for t in telas if t["ok"]]
    celulas = "".join(
        '<figure style="--i:%d">%s<figcaption>%s</figcaption></figure>'
        % (i, img_ou_moldura(t, "tiro mini"), esc(t["nome"]))
        for i, t in enumerate(prontas))
    return '<div class="mosaico">%s</div>' % celulas


def bloco_tela(mod_chave, telas):
    """A tela representativa, em tamanho cheio, com o cartão de digitação."""
    href = DESTAQUE.get(mod_chave)
    tela = next((t for t in telas if t["href"] == href), None)
    if tela is None:
        tela = next((t for t in telas if t["ok"]), None)
    if tela is None:
        return ""
    campos = "".join(
        '<div class="campo" data-txt="%s"><label>%s</label>'
        '<div class="valor"><span></span><i></i></div></div>'
        % (esc(txt), esc(rot))
        for rot, txt in DIGITACAO.get(mod_chave, []))
    return ('<div class="cheia">%s<div class="cartao">%s</div></div>'
            % (img_ou_moldura(tela, "tiro grande"), campos))


def main():
    if not os.path.exists(INVENTARIO):
        raise SystemExit("ERRO: falta o %s. Rode antes:\n"
                         "  python _demo_inventario.py" % INVENTARIO)
    dados = json.load(io.open(INVENTARIO, encoding="utf-8"))
    modulos = [m for m in dados["modulos"]
               if m["chave"] not in MODULOS_NO_FECHO]
    telas = dados["telas"]

    voz = tempos_da_voz()
    slides, roteiro = [], []

    t_abertura = voz["abertura"]["dur"] if "abertura" in voz else T_ABERTURA
    slides.append((t_abertura, """
      <section class="slide on capa" data-dur="%s">
        <h1>Folha10-Simples</h1>
        <p class="lede">A folha inteira dentro do navegador — do cadastro do
        funcionário ao recibo do eSocial.</p>
        <div class="cab-demo">
          <div class="cab-col"><b>Empresa</b><span>Sua empresa aqui</span></div>
          <div class="cab-col"><b>Folha 07/2026</b><span class="badge">Aberta</span></div>
          <div class="cab-col"><b>Versão</b><span>no rodapé, sempre à vista</span></div>
        </div>
        <div class="avisos">
          <div class="aviso cert">🔑 Certificado digital A1 — válido até 12/2026</div>
          <div class="aviso lic">🔐 Licença Folha10-Simples ativa</div>
        </div>
      </section>""" % t_abertura))

    for mod in modulos:
        do_mod = [t for t in telas if t["modulo"] == mod["chave"]]
        prontas = [t for t in do_mod if t["ok"]]
        if not prontas:
            continue
        fases = (voz[mod["chave"]]["fases"] if mod["chave"] in voz
                 else [T_GAVETA, T_MOSAICO, T_TELA])
        dur = round(sum(fases), 2)
        slides.append((dur, """
      <section class="slide modulo" data-dur="%s" data-fases="%s" data-mod="%s">
        <div class="fase fase-gaveta">%s</div>
        <div class="fase fase-mosaico"><h3>%s — %d telas</h3>%s</div>
        <div class="fase fase-tela">%s</div>
      </section>""" % (dur, ",".join(str(f) for f in fases),
                       esc(mod["chave"]), bloco_gaveta(mod, do_mod),
                       esc(mod["titulo"]), len(prontas),
                       bloco_mosaico(do_mod), bloco_tela(mod["chave"], do_mod))))
        roteiro.append((mod["titulo"], len(prontas), dur))

    fora = [m for m in dados["modulos"] if m["chave"] in MODULOS_NO_FECHO]
    promessa = " · ".join(m["titulo"] for m in fora)
    t_fecho = voz["fecho"]["dur"] if "fecho" in voz else T_FECHO
    slides.append((t_fecho, """
      <section class="slide fecho" data-dur="%s">
        <h2>Processe o primeiro mês sem custo</h2>
        <p class="lede">Sem compromisso e com suporte.%s</p>
        <p class="url">folha10-simples.com.br</p>
      </section>""" % (t_fecho,
                       (" Chegando: " + promessa + ".") if promessa else "")))

    total = round(sum(d for d, _ in slides), 2)
    html = MOLDE.replace("{{SLIDES}}", "".join(s for _, s in slides)) \
                .replace("{{TOTAL}}", str(total))
    io.open(SAIDA, "w", encoding="utf-8", newline="").write(html)

    faltam = sum(1 for t in telas
                 if t["ok"] and not t["repetida"] and not os.path.exists(arquivo_do(t)))
    print("%s gerado — %d slides, %.0f s (%d min %02d s)%s"
          % (SAIDA, len(slides), total, int(total) // 60, int(total) % 60,
             "" if voz else "   [tempos fixos, sem narração]"))
    for titulo, n, dur in roteiro:
        print("   %-16s %2d telas  %.0fs" % (titulo, n, dur))
    if fora:
        print("   (no fecho, sem tela pronta: %s)" % promessa)
    if not voz:
        print("\nATENÇÃO: sem narração — os tempos acima são chutes fixos e o"
              "\nHTML vai rodar mudo. Rode:  python _demo_narracao.py")
    if faltam:
        print("\nATENÇÃO: %d print(s) ainda não capturado(s) — essas telas saem"
              "\ncomo moldura vazia. Rode:  python _demo_capturar.py" % faltam)
    else:
        print("\nTodos os prints no lugar.")


MOLDE = r"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>Folha10-Simples — Demonstração</title>
<style>
:root{
  --paper:#EFF3F8; --stage:#FFFFFF; --panel:#F5F8FC;
  --ink:#0C1726; --ink-2:#4A5D75; --ink-3:#7C8EA5;
  --rule:#D3DDE9; --brand:#1F6FD0; --brand-soft:#E2EDFB;
  --ok:#06773F; --ok-soft:#DDF2E6; --amber:#9A5B06; --amber-soft:#FBEEDA;
  --sans:"Segoe UI",system-ui,-apple-system,Arial,sans-serif;
  --mono:"Cascadia Mono",Consolas,ui-monospace,monospace;
  --shadow:0 1px 0 rgba(12,23,38,.04), 0 18px 40px -24px rgba(12,23,38,.35);
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --paper:#080F19; --stage:#101D2D; --panel:#16273A;
    --ink:#E9F1F9; --ink-2:#9FB4CB; --ink-3:#71879F;
    --rule:#23374E; --brand:#63A5F6; --brand-soft:#173049;
    --ok:#3CCB85; --ok-soft:#10331F; --amber:#E9A84A; --amber-soft:#33260F;
    --shadow:0 1px 0 rgba(0,0,0,.4), 0 22px 50px -28px rgba(0,0,0,.9);
  }
}
:root[data-theme="dark"]{
  --paper:#080F19; --stage:#101D2D; --panel:#16273A;
  --ink:#E9F1F9; --ink-2:#9FB4CB; --ink-3:#71879F;
  --rule:#23374E; --brand:#63A5F6; --brand-soft:#173049;
  --ok:#3CCB85; --ok-soft:#10331F; --amber:#E9A84A; --amber-soft:#33260F;
}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);
     -webkit-font-smoothing:antialiased}
.deck{min-height:100vh;min-height:100dvh;display:flex;flex-direction:column;
      gap:14px;padding:16px clamp(12px,3vw,32px) 14px}
.rail{display:flex;align-items:center;gap:clamp(10px,2vw,20px);flex-wrap:wrap}
.mark{font-weight:700;letter-spacing:-.02em;font-size:15px;white-space:nowrap}
.mark b{color:var(--brand)}
.track{flex:1 1 240px;height:3px;background:var(--rule);border-radius:2px;overflow:hidden}
.track i{display:block;height:100%;width:0;background:var(--brand)}
.ctrl{display:flex;gap:8px}
.ctrl button{font:inherit;font-size:12px;padding:6px 12px;border:1px solid var(--rule);
  border-radius:7px;background:var(--stage);color:var(--ink);cursor:pointer}
.ctrl button:hover{border-color:var(--brand);color:var(--brand)}
.palco{flex:1;position:relative;background:var(--stage);border:1px solid var(--rule);
       border-radius:12px;box-shadow:var(--shadow);overflow:hidden}
.slide{position:absolute;inset:0;padding:clamp(18px,3vw,40px);opacity:0;
       pointer-events:none;display:flex;flex-direction:column;gap:14px;overflow:hidden}
.slide.on{opacity:1;pointer-events:auto}
h1{font-size:clamp(30px,4.4vw,58px);margin:0;letter-spacing:-.03em}
h2{font-size:clamp(24px,3.4vw,44px);margin:0;letter-spacing:-.02em}
h3{font-size:clamp(15px,1.9vw,22px);margin:0 0 10px;color:var(--ink-2)}
h4{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--brand);
   margin:0 0 6px}
.lede{font-size:clamp(14px,1.5vw,19px);color:var(--ink-2);margin:0;max-width:62ch}
.url{font-family:var(--mono);font-size:clamp(17px,2.6vw,34px);color:var(--brand);
     margin:18px 0 0;padding:12px 20px;border:1px solid var(--rule);border-radius:8px;
     background:var(--panel);align-self:flex-start}
/* ---- abertura ---- */
.cab-demo{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:8px;
  border:1px solid var(--rule);border-radius:10px;padding:12px;background:var(--panel)}
.cab-col b{display:block;font-size:10px;letter-spacing:.1em;text-transform:uppercase;
  color:var(--ink-3)}
.cab-col span{font-size:14px}
.badge{background:var(--ok-soft);color:var(--ok);padding:1px 8px;border-radius:20px;
  font-size:12px;font-weight:600}
.avisos{display:flex;gap:10px;flex-wrap:wrap;margin-top:auto}
.aviso{font-size:13px;padding:9px 14px;border-radius:9px;border:1px solid var(--rule)}
.aviso.cert{background:var(--amber-soft);color:var(--amber)}
.aviso.lic{background:var(--ok-soft);color:var(--ok)}
/* ---- fases do módulo ---- */
.fase{position:absolute;inset:clamp(18px,3vw,40px);opacity:0;transition:opacity .5s}
.fase.on{opacity:1}
.gaveta{border:1px solid var(--rule);border-radius:10px;overflow:hidden;height:100%;
  display:flex;flex-direction:column;background:var(--panel)}
.gaveta-cab{padding:11px 16px;font-weight:700;font-size:17px;background:var(--brand-soft);
  color:var(--brand);border-bottom:1px solid var(--rule)}
.gaveta-corpo{padding:14px 16px;display:grid;gap:14px;overflow:auto;
  grid-template-columns:repeat(auto-fit,minmax(190px,1fr))}
.gaveta ul{list-style:none;margin:0;padding:0;display:grid;gap:3px}
.gaveta li{font-size:12.5px;color:var(--ink-2);line-height:1.45}
.gaveta li.nao{opacity:.42}
.mosaico{display:grid;gap:10px;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));
  align-content:start;height:100%;overflow:hidden}
.mosaico figure{margin:0;animation:sobe .5s both;animation-delay:calc(var(--i)*.05s)}
@keyframes sobe{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
figcaption{font-size:10.5px;color:var(--ink-3);margin-top:4px;line-height:1.3}
.tiro{border:1px solid var(--rule);border-radius:7px;overflow:hidden;background:#fff;
  line-height:0;box-shadow:var(--shadow)}
.tiro img{display:block;width:100%;height:auto}
.tiro.mini{aspect-ratio:16/10;display:grid;place-items:center}
.tiro.mini img{height:100%;width:100%;object-fit:cover;object-position:top center}
.tiro.falta{aspect-ratio:16/10;display:grid;place-items:center;background:var(--panel);
  border-style:dashed;line-height:1.4}
.tiro.falta span{font-size:11px;color:var(--ink-3);padding:8px;text-align:center}
.cheia{position:relative;height:100%;display:grid;place-items:center}
.cheia .tiro.grande{max-height:100%;max-width:100%}
.cheia .tiro.grande img{max-height:calc(100vh - 190px);width:auto}
.cartao{position:absolute;right:4%;bottom:8%;background:var(--stage);border:1px solid var(--rule);
  border-radius:11px;box-shadow:var(--shadow);padding:14px 16px;display:grid;gap:10px;
  min-width:min(330px,80%)}
.campo label{display:block;font-size:10px;letter-spacing:.09em;text-transform:uppercase;
  color:var(--ink-3);margin-bottom:3px}
.campo .valor{display:flex;align-items:center;gap:1px;border:1px solid var(--rule);
  border-radius:6px;padding:7px 10px;background:var(--panel);font-family:var(--mono);
  font-size:14px;min-height:34px}
.campo .valor i{width:1.5px;height:16px;background:var(--brand);opacity:0}
.campo.digitando .valor i{animation:pisca .9s steps(1) infinite}
@keyframes pisca{0%,50%{opacity:1}51%,100%{opacity:0}}
.fecho{justify-content:center}
@media (max-width:820px){
  .cab-demo{grid-template-columns:1fr}
  .cartao{right:auto;left:4%;bottom:4%;min-width:auto;width:92%}
}
</style>
</head>
<body>
<div class="deck">
  <div class="rail">
    <div class="mark">Folha10<b>-Simples</b></div>
    <div class="track"><i id="barra"></i></div>
    <div class="ctrl">
      <button id="btPlay">▶ Rodar</button>
      <button id="btAnt">‹</button>
      <button id="btProx">›</button>
    </div>
  </div>
  <div class="palco" id="palco">{{SLIDES}}</div>
</div>
<audio id="voz" src="static/demo_narracao.mp3" preload="auto"></audio>
<script>
// Motor dos slides. Cada <section> diz quanto dura em data-dur; os blocos de
// modulo tem tres fases internas (gaveta, mosaico, tela cheia) que se revezam
// dentro desse tempo. A digitacao comeca junto com a fase da tela.
//
// data-fases traz o tempo de CADA fase, medido na narracao. Sem ele as tres
// dividiam o slide em partes iguais -- e a voz, que nao e igual, entrava na
// fase errada: a frase da tela cheia comecava ainda no mosaico.
const TOTAL = {{TOTAL}};
const slides = [...document.querySelectorAll('.slide')];
const barra  = document.getElementById('barra');
const voz    = document.getElementById('voz');

const dur = s => parseFloat(s.dataset.dur || '8');

// A linha do tempo inteira, montada uma vez: o segundo em que cada slide
// entra e, dentro dele, quanto dura cada fase. Sao os mesmos numeros que
// geraram o audio, entao imagem e voz medem pela mesma regua.
const CENAS = slides.map(s => {
  const fases = [...s.querySelectorAll('.fase')];
  const medidos = (s.dataset.fases || '').split(',').filter(Boolean).map(Number);
  const passos = (fases.length && medidos.length === fases.length)
    ? medidos
    : fases.map(() => dur(s) / fases.length);
  return {dur: dur(s), passos: passos};
});
const INICIO = [];
CENAS.reduce((t, c) => { INICIO.push(t); return t + c.dur; }, 0);

let rodando = false, base = 0, t0 = 0, mostrando = -1, faseAtual = -1, laco = null;

// Um relogio so para tudo. Com o audio tocando, quem manda e ele: e o unico
// que nao acumula atraso ao longo de seis minutos -- a versao anterior
// encadeava setTimeout e, no fim da demonstracao, a voz ja falava do modulo
// seguinte. Sem audio, ou se o navegador bloquear o som, cai no cronometro.
function agora() {
  if (voz.readyState > 0 && !voz.paused) return voz.currentTime;
  return base + (rodando ? (performance.now() - t0) / 1000 : 0);
}

function mostrarFase(slide, i) {
  const fases = [...slide.querySelectorAll('.fase')];
  fases.forEach((f, k) => f.classList.toggle('on', k === i));
  if (fases[i] && fases[i].classList.contains('fase-tela')) digitar(fases[i]);
}

// Digita letra por letra. O texto vem do data-txt para o HTML continuar
// legivel e para o campo poder ser reiniciado quantas vezes for preciso.
function digitar(fase) {
  const campos = [...fase.querySelectorAll('.campo')];
  campos.forEach(c => {
    c.querySelector('.valor span').textContent = '';
    c.classList.remove('digitando');
  });
  let atrasoCampo = 600;
  campos.forEach(c => {
    setTimeout(() => {
      c.classList.add('digitando');
      const txt = c.dataset.txt || '', alvo = c.querySelector('.valor span');
      let i = 0;
      const bate = setInterval(() => {
        alvo.textContent = txt.slice(0, ++i);
        if (i >= txt.length) { clearInterval(bate); c.classList.remove('digitando'); }
      }, 70);
    }, atrasoCampo);
    atrasoCampo += 600 + (c.dataset.txt || '').length * 70 + 500;
  });
}

// Poe na tela o que corresponde ao segundo t. Nao guarda estado proprio: e
// so o relogio traduzido em slide e fase. Por isso pular para tras, pausar
// ou arrastar o audio dao todos no mesmo lugar.
function pintar(t) {
  let n = 0;
  while (n + 1 < slides.length && t >= INICIO[n + 1]) n++;
  if (n !== mostrando) {
    slides.forEach((s, i) => s.classList.toggle('on', i === n));
    mostrando = n; faseAtual = -1;
  }
  const passos = CENAS[n].passos;
  if (passos.length) {
    let f = 0, acc = INICIO[n];
    for (let i = 0; i < passos.length; i++) { if (t >= acc) f = i; acc += passos[i]; }
    if (f !== faseAtual) { faseAtual = f; mostrarFase(slides[n], f); }
  }
  barra.style.width = Math.min(100, t / TOTAL * 100) + '%';
}

function irPara(t) {
  base = Math.max(0, Math.min(t, TOTAL)); t0 = performance.now();
  if (voz.readyState > 0) { try { voz.currentTime = base; } catch (e) {} }
  pintar(base);
}

function tique() {
  const t = agora();
  if (t >= TOTAL) { parar(); return; }
  pintar(t);
}

function rodar() {
  rodando = true; t0 = performance.now();
  document.getElementById('btPlay').textContent = '❚❚ Pausar';
  voz.play().catch(() => {});   // celular so libera audio depois de um toque
  clearInterval(laco); laco = setInterval(tique, 100);
}

function parar() {
  base = agora();                // antes de pausar: depois o relogio some
  rodando = false; clearInterval(laco); laco = null; t0 = performance.now();
  document.getElementById('btPlay').textContent = '▶ Rodar';
  voz.pause();
}

document.getElementById('btPlay').onclick = () => rodando ? parar() : rodar();
document.getElementById('btProx').onclick = () => irPara(INICIO[Math.min(mostrando + 1, slides.length - 1)]);
document.getElementById('btAnt').onclick  = () => irPara(INICIO[Math.max(mostrando - 1, 0)]);
document.addEventListener('keydown', e => {
  if (e.key === 'ArrowRight') document.getElementById('btProx').click();
  if (e.key === 'ArrowLeft')  document.getElementById('btAnt').click();
  if (e.key === ' ') { e.preventDefault(); document.getElementById('btPlay').click(); }
});
pintar(0);
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
