/* ==========================================================================
   f10_autoselect.js — empresa com UM funcionário só já vem escolhido.

   Quando a lista de funcionários da tela tem exatamente um item, marcar esse
   item é a única saída possível: o clique não é uma escolha, é burocracia.
   Este script marca sozinho e dispara o 'change', para a própria tela rodar o
   handler dela (atualizarSelecao / atualizarTodos / o que for) sem que este
   arquivo precise conhecer o nome da função.

   Não age quando:
     - há 0 ou 2+ funcionários (aí existe escolha de verdade);
     - a tela já marcou alguém (ex.: Visualizar Cálculo vindo com ?matricula=,
       ou as telas de férias/rescisão que já vêm com tudo marcado).

   Listas montadas por JS (fetch) devem chamar window.f10MarcarUnicoFuncionario()
   no fim da renderização — o DOMContentLoaded já passou nessa hora.
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

    function caixas() {
        var achadas = [];
        SELETORES.forEach(function (sel) {
            var nós;
            try { nós = document.querySelectorAll(sel); } catch (e) { return; }
            Array.prototype.forEach.call(nós, function (c) {
                if (!c.disabled && achadas.indexOf(c) === -1) achadas.push(c);
            });
        });
        return achadas;
    }

    function marcar() {
        var chks = caixas();
        if (chks.length !== 1) return false;   // 0 ou 2+: existe escolha
        var c = chks[0];
        if (c.checked) return false;           // a tela já marcou
        c.checked = true;
        c.dispatchEvent(new Event('change', { bubbles: true }));
        return true;
    }

    // setTimeout 0: deixa o DOMContentLoaded da própria tela terminar antes,
    // senão o init dela pode desmarcar o que acabamos de marcar.
    function agendar() { setTimeout(marcar, 0); }

    window.f10MarcarUnicoFuncionario = marcar;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', agendar);
    } else {
        agendar();
    }
})();
