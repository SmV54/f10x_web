/* ==========================================================================
   f10_autoselect.js — quando sobra UM funcionário, ele já vem escolhido.

   Vale nos dois casos:
     - a empresa só tem um funcionário;
     - a busca/filtro da tela reduziu a lista a um.

   Marcar o único item visível não é uma escolha, é burocracia. O script marca
   e dispara o 'change', para a própria tela rodar o handler dela
   (atualizarSelecao / atualizarTodos / o que for) sem que este arquivo precise
   conhecer o nome da função.

   Não age quando:
     - há 0 ou 2+ funcionários VISÍVEIS (aí existe escolha de verdade);
     - a tela já marcou alguém (ex.: Visualizar Cálculo com ?matricula=, ou as
       telas de férias/rescisão que já vêm com tudo marcado);
     - o usuário já desmarcou aquele item — cada caixa só é marcada uma vez,
       senão o filtro ficaria brigando com quem desmarcou de propósito.

   Listas montadas por JS podem chamar window.f10MarcarUnicoFuncionario()
   depois de renderizar; o MutationObserver abaixo também cobre esse caso.
   ========================================================================== */
(function () {
    'use strict';

    // Convenções de marcação de funcionário no sistema. O S-3000 também usa
    // .func-chk, mas para REMESSAS — por isso ele não inclui este script.
    var SELETORES = [
        '.func-item input[type="checkbox"]',
        '#funcLista input[type="checkbox"]',
        'input.func-chk[type="checkbox"]'
    ];

    // Cada caixa é marcada no máximo uma vez. Sem isso, quem desmarcasse e
    // continuasse digitando na busca veria o item marcar sozinho de novo.
    var jaMarcadas = (typeof WeakSet === 'function') ? new WeakSet() : null;

    function visivel(el) {
        return !!(el.offsetParent || (el.getClientRects && el.getClientRects().length));
    }

    function caixasVisiveis() {
        var achadas = [];
        SELETORES.forEach(function (sel) {
            var nos;
            try { nos = document.querySelectorAll(sel); } catch (e) { return; }
            Array.prototype.forEach.call(nos, function (c) {
                if (c.disabled) return;
                if (achadas.indexOf(c) !== -1) return;
                if (!visivel(c)) return;
                achadas.push(c);
            });
        });
        return achadas;
    }

    function marcar() {
        var chks = caixasVisiveis();
        if (chks.length !== 1) return false;      // 0 ou 2+: existe escolha
        var c = chks[0];
        if (c.checked) return false;              // já marcado
        if (jaMarcadas && jaMarcadas.has(c)) return false;   // usuário desmarcou
        if (jaMarcadas) jaMarcadas.add(c);
        c.checked = true;
        c.dispatchEvent(new Event('change', { bubbles: true }));
        return true;
    }

    // Reavalia com folga: a tela pode filtrar, re-renderizar a lista ou rodar
    // o próprio init logo depois. 120 ms junta a rajada num disparo só.
    var timer = null;
    function reavaliar() {
        if (timer) clearTimeout(timer);
        timer = setTimeout(function () {
            timer = null;
            marcar();
            atualizarBotaoVisiveis();
        }, 120);
    }

    /* ── "Selecionar visíveis" ─────────────────────────────────────────
       Marcar enquanto se digita não dá: no caminho até "Adri" você passa por
       "A", que casa com quase todo mundo. Para corrigir isso seria preciso
       DESMARCAR quem sai do filtro — e aí a seleção deixaria de ser cumulativa
       e apagaria o que foi marcado na mão. Então é um clique explícito: filtra,
       vê quem sobrou, marca os que estão à vista. Mesmo padrão da tela Select
       Funcionário, que já fazia assim.
       Botões com [data-f10-visiveis] aparecem sozinhos quando há filtro. */
    function selecionarVisiveis() {
        var n = 0;
        caixasVisiveis().forEach(function (c) {
            if (c.checked) return;
            if (jaMarcadas) jaMarcadas.add(c);
            c.checked = true;
            c.dispatchEvent(new Event('change', { bubbles: true }));
            n++;
        });
        return n;
    }

    function totalCaixas() {
        var t = 0;
        SELETORES.forEach(function (sel) {
            try { t += document.querySelectorAll(sel).length; } catch (e) {}
        });
        return t;
    }

    // Só faz sentido oferecer o botão quando o filtro escondeu alguém e ainda
    // sobra mais de um visível (com um só, o auto-select já resolveu).
    function atualizarBotaoVisiveis() {
        var btns = document.querySelectorAll('[data-f10-visiveis]');
        if (!btns.length) return;
        var vis = caixasVisiveis();
        var mostrar = vis.length > 1 && vis.length < totalCaixas();
        Array.prototype.forEach.call(btns, function (b) {
            b.style.display = mostrar ? '' : 'none';
            b.textContent = '✓ Selecionar os ' + vis.length + ' visíveis';
        });
    }

    window.f10SelecionarVisiveis     = selecionarVisiveis;
    window.f10MarcarUnicoFuncionario = marcar;

    function ligar() {
        // 1) abertura da tela — setTimeout deixa o init dela terminar antes
        setTimeout(function () { marcar(); atualizarBotaoVisiveis(); }, 0);

        // 2) busca/filtro: qualquer digitação pode reduzir a lista a um
        document.addEventListener('input', reavaliar, true);

        // 3) listas que somem/aparecem (display:none) ou são re-renderizadas
        if (typeof MutationObserver === 'function' && document.body) {
            new MutationObserver(reavaliar).observe(document.body, {
                childList: true,
                subtree:   true,
                attributes: true,
                attributeFilter: ['style', 'class', 'hidden']
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', ligar);
    } else {
        ligar();
    }
})();
