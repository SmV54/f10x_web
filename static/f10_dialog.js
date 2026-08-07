/* =========================================================
 * Folha10 Simples — Diálogos profissionais
 * Substituem os alert/confirm/prompt nativos do browser
 * (que mostram "localhost:5000 diz").
 *
 * API:
 *   f10Alert(msg, opts?)   → Promise<void>
 *   f10Confirm(msg, opts?) → Promise<boolean>
 *   f10Prompt(msg, opts?)  → Promise<string|null>
 *
 * opts: {
 *   titulo: string,
 *   tipo: 'info' | 'sucesso' | 'aviso' | 'erro' | 'perigo',
 *   okText: string,
 *   cancelText: string,
 *   valor: string         // só para f10Prompt — valor default do input
 * }
 *
 * Auto-override: window.alert = f10Alert.
 * ======================================================= */
(function () {
  if (window.__f10DialogInstalled) return;
  window.__f10DialogInstalled = true;

  // ── CSS (injetado uma vez) ──
  const css = `
.f10dlg-backdrop {
    position: fixed; inset: 0;
    background: rgba(15, 23, 42, 0.55);
    backdrop-filter: blur(2px);
    display: flex; align-items: center; justify-content: center;
    z-index: 99999;
    opacity: 0;
    transition: opacity 0.18s ease;
    font-family: 'IBM Plex Sans', system-ui, sans-serif;
}
.f10dlg-backdrop.show { opacity: 1; }
.f10dlg-modal {
    background: #fff;
    border-radius: 14px;
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.35), 0 0 0 1px rgba(0, 0, 0, 0.05);
    min-width: 360px;
    max-width: 520px;
    overflow: hidden;
    transform: translateY(-12px) scale(0.98);
    transition: transform 0.18s ease;
}
.f10dlg-backdrop.show .f10dlg-modal { transform: translateY(0) scale(1); }
.f10dlg-header {
    padding: 16px 22px 12px;
    display: flex; align-items: center; gap: 12px;
    border-bottom: 1px solid #e5e7eb;
}
.f10dlg-icone {
    width: 36px; height: 36px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 20px; font-weight: 700;
    flex-shrink: 0;
}
.f10dlg-icone.info    { background: #dbeafe; color: #1d4ed8; }
.f10dlg-icone.sucesso { background: #dcfce7; color: #166534; }
.f10dlg-icone.aviso   { background: #fef3c7; color: #92400e; }
.f10dlg-icone.erro    { background: #fee2e2; color: #b91c1c; }
.f10dlg-icone.perigo  { background: #fee2e2; color: #b91c1c; }
.f10dlg-titulo {
    font-size: 15px; font-weight: 600; color: #0f172a;
    flex: 1;
}
.f10dlg-corpo {
    padding: 18px 22px;
    font-size: 14px; color: #334155; line-height: 1.55;
    white-space: pre-wrap; word-wrap: break-word;
    max-height: 60vh; overflow-y: auto;
}
.f10dlg-input {
    width: 100%; margin-top: 14px;
    padding: 9px 12px; border-radius: 8px;
    border: 1px solid #cbd5e1;
    font-size: 14px; font-family: inherit;
    outline: none; transition: 0.15s;
    background: #fff; color: #0f172a;
}
.f10dlg-input:focus {
    border-color: #2a7de1;
    box-shadow: 0 0 0 3px rgba(42, 125, 225, 0.15);
}
.f10dlg-acoes {
    padding: 12px 22px 18px;
    display: flex; justify-content: flex-end; gap: 10px;
    background: #f8fafc;
    border-top: 1px solid #e5e7eb;
}
.f10dlg-btn {
    padding: 8px 18px; border-radius: 8px; border: 1px solid transparent;
    font-size: 13px; font-weight: 600; cursor: pointer;
    font-family: inherit; transition: 0.13s;
    min-width: 90px;
}
.f10dlg-btn-cancel {
    background: #fff; color: #374151; border-color: #cbd5e1;
}
.f10dlg-btn-cancel:hover { background: #f1f5f9; border-color: #94a3b8; }
.f10dlg-btn-ok-info,
.f10dlg-btn-ok-sucesso { background: #2a7de1; color: #fff; }
.f10dlg-btn-ok-info:hover,
.f10dlg-btn-ok-sucesso:hover { background: #1e63c4; }
.f10dlg-btn-ok-aviso { background: #d97706; color: #fff; }
.f10dlg-btn-ok-aviso:hover { background: #b45309; }
.f10dlg-btn-ok-erro,
.f10dlg-btn-ok-perigo { background: #dc2626; color: #fff; }
.f10dlg-btn-ok-erro:hover,
.f10dlg-btn-ok-perigo:hover { background: #b91c1c; }
.f10dlg-btn:focus { outline: 2px solid #93c5fd; outline-offset: 1px; }

/* =========================================================
 * Padronização do botão "Voltar/Menu" do cabeçalho (.topo)
 * Mesmo modelo do "Sair": fundo branco + fonte vermelha, inverte no hover.
 * Também garante que o botão fique SEMPRE ao lado (nunca embaixo da versão).
 * ========================================================= */
.topo .btn-voltar-topo,
.topo .btn-voltar,
.topo .btn-menu,
.topo .btn-voltar-menu {
    background: #fff !important;
    border: 1.5px solid #e11d48 !important;
    color: #e11d48 !important;
    font-weight: 700 !important;
    font-size: 13.5px !important;
    padding: 9px 22px !important;
    border-radius: 8px !important;
    box-shadow: 0 2px 8px rgba(190,18,60,0.18) !important;
    text-decoration: none !important;
    cursor: pointer !important;
    transition: 0.15s !important;
    white-space: nowrap !important;
    line-height: 1.1 !important;
    display: inline-flex !important;
    align-items: center !important;
}
.topo .btn-voltar-topo:hover,
.topo .btn-voltar:hover,
.topo .btn-menu:hover,
.topo .btn-voltar-menu:hover {
    background: #e11d48 !important;
    border-color: #be123c !important;
    color: #fff !important;
    box-shadow: 0 3px 12px rgba(190,18,60,0.32) !important;
}
/* Corrige telas onde o Voltar caía embaixo da versão (topo-dir empilhado)
   e mantém o bloco alinhado à DIREITA da célula (não colar no título). */
.topo .topo-dir { flex-direction: row !important; align-items: center !important; justify-content: flex-end !important; gap: 14px !important; }

/* Versão: largura igualada à da logomarca — o tamanho da fonte é calculado
   dinamicamente em JS (ver ajustarVersaoLargura), aqui só travamos espaçamento. */
.topo .topo-versao {
    letter-spacing: 0 !important;
    white-space: nowrap !important;
    line-height: 1.05 !important;
}
`;
  const style = document.createElement('style');
  style.id = 'f10-dialog-styles';
  style.textContent = css;
  (document.head || document.documentElement).appendChild(style);

  // ── Ícones / títulos padrão por tipo ──
  const ICONES = {
    info:    { sym: 'i', titulo: 'Informação' },
    sucesso: { sym: '✓', titulo: 'Sucesso'    },
    aviso:   { sym: '!', titulo: 'Atenção'    },
    erro:    { sym: '✕', titulo: 'Erro'       },
    perigo:  { sym: '!', titulo: 'Atenção'    },
  };

  // ── Detecta o tipo a partir da mensagem ──
  function detectarTipo(msg) {
    const m = String(msg || '').toLowerCase();
    if (/excluir|exclus[ãa]o|remover|remo[çc][ãa]o|apagar/.test(m)) return 'perigo';
    if (/desativar|desabilitar|cancelar/.test(m)) return 'aviso';
    if (/erro|falha|inv[áa]lido|n[ãa]o foi poss[íi]vel/.test(m)) return 'erro';
    if (/sucesso|gravad[oa]|salvo|conclu[íi]d[oa]|enviad[oa]/.test(m)) return 'sucesso';
    if (/aten[çc][ãa]o|aviso|cuidado|incomum|redu[çc][ãa]o/.test(m)) return 'aviso';
    return 'info';
  }

  // ── Núcleo: cria modal e retorna {root, fechar} ──
  function criarModal(opts) {
    const tipo = opts.tipo || detectarTipo(opts.msg);
    const ic   = ICONES[tipo] || ICONES.info;
    const titulo = opts.titulo || ic.titulo;

    const backdrop = document.createElement('div');
    backdrop.className = 'f10dlg-backdrop';
    backdrop.innerHTML = `
      <div class="f10dlg-modal" role="dialog" aria-modal="true">
        <div class="f10dlg-header">
          <div class="f10dlg-icone ${tipo}">${ic.sym}</div>
          <div class="f10dlg-titulo"></div>
        </div>
        <div class="f10dlg-corpo"></div>
        <div class="f10dlg-acoes"></div>
      </div>
    `;
    backdrop.querySelector('.f10dlg-titulo').textContent = titulo;
    backdrop.querySelector('.f10dlg-corpo').textContent  = String(opts.msg || '');

    document.body.appendChild(backdrop);
    // Anima entrada
    requestAnimationFrame(() => backdrop.classList.add('show'));

    function fechar() {
      backdrop.classList.remove('show');
      setTimeout(() => backdrop.remove(), 180);
    }

    // Enter/Esc pressionado para fechar UM dialogo chegava a vazar para o
    // seguinte, quando dois sao abertos em sequencia: o segundo ja nasce com o
    // botao focado e se resolvia sozinho. Ignora tecla nos primeiros 250ms.
    const nascidoEm = performance.now();
    function tecladoLiberado() { return performance.now() - nascidoEm > 250; }

    return { backdrop, tipo, fechar, tecladoLiberado };
  }

  // ── f10Alert ──
  window.f10Alert = function f10Alert(msg, opts) {
    opts = Object.assign({ msg }, opts || {});
    return new Promise((resolve) => {
      const { backdrop, tipo, fechar, tecladoLiberado } = criarModal(opts);
      const acoes = backdrop.querySelector('.f10dlg-acoes');
      const btn = document.createElement('button');
      btn.className = 'f10dlg-btn f10dlg-btn-ok-' + tipo;
      btn.textContent = opts.okText || 'OK';
      btn.onclick = () => { fechar(); resolve(); };
      acoes.appendChild(btn);
      btn.focus();

      // ESC fecha
      backdrop.addEventListener('keydown', (e) => {
        if (!tecladoLiberado()) return;
        if (e.key === 'Escape') { fechar(); resolve(); }
      });
      backdrop.tabIndex = -1;
      backdrop.focus();
    });
  };

  // ── f10Confirm ──
  window.f10Confirm = function f10Confirm(msg, opts) {
    opts = Object.assign({ msg }, opts || {});
    return new Promise((resolve) => {
      const { backdrop, tipo, fechar, tecladoLiberado } = criarModal(opts);
      const acoes = backdrop.querySelector('.f10dlg-acoes');

      const btnCancel = document.createElement('button');
      btnCancel.className = 'f10dlg-btn f10dlg-btn-cancel';
      btnCancel.textContent = opts.cancelText || 'Cancelar';
      btnCancel.onclick = () => { fechar(); resolve(false); };

      const btnOk = document.createElement('button');
      btnOk.className = 'f10dlg-btn f10dlg-btn-ok-' + tipo;
      // Texto contextual por tipo se okText não foi passado
      const padrao = {
        perigo:  'Excluir',
        aviso:   'Confirmar',
        sucesso: 'Confirmar',
        erro:    'Confirmar',
        info:    'Confirmar',
      };
      btnOk.textContent = opts.okText || padrao[tipo] || 'Confirmar';
      btnOk.onclick = () => { fechar(); resolve(true); };

      acoes.appendChild(btnCancel);
      acoes.appendChild(btnOk);
      btnOk.focus();

      backdrop.addEventListener('keydown', (e) => {
        if (!tecladoLiberado()) return;
        if (e.key === 'Escape') { fechar(); resolve(false); }
        if (e.key === 'Enter')  { fechar(); resolve(true);  }
      });
      backdrop.tabIndex = -1;
      backdrop.focus();
    });
  };

  // ── f10Prompt ──
  window.f10Prompt = function f10Prompt(msg, opts) {
    opts = Object.assign({ msg }, opts || {});
    return new Promise((resolve) => {
      const { backdrop, tipo, fechar, tecladoLiberado } = criarModal(opts);
      const corpo = backdrop.querySelector('.f10dlg-corpo');
      const input = document.createElement('input');
      input.type = 'text';
      input.className = 'f10dlg-input';
      input.value = opts.valor || '';
      corpo.appendChild(input);

      const acoes = backdrop.querySelector('.f10dlg-acoes');
      const btnCancel = document.createElement('button');
      btnCancel.className = 'f10dlg-btn f10dlg-btn-cancel';
      btnCancel.textContent = opts.cancelText || 'Cancelar';
      btnCancel.onclick = () => { fechar(); resolve(null); };

      const btnOk = document.createElement('button');
      btnOk.className = 'f10dlg-btn f10dlg-btn-ok-' + tipo;
      btnOk.textContent = opts.okText || 'OK';
      btnOk.onclick = () => { fechar(); resolve(input.value); };

      acoes.appendChild(btnCancel);
      acoes.appendChild(btnOk);
      setTimeout(() => input.focus(), 50);

      input.addEventListener('keydown', (e) => {
        if (!tecladoLiberado()) return;
        if (e.key === 'Enter')  { fechar(); resolve(input.value); }
        if (e.key === 'Escape') { fechar(); resolve(null); }
      });
    });
  };

  // ── Override transparente do window.alert ──
  // (alert nativo é fire-and-forget — código existente não usa retorno)
  window.alert = function (msg) {
    return window.f10Alert(msg);
  };
})();

/* =========================================================
 * Modo Admin — banner amarelo global de impersonation
 * Injeta um banner fixo no topo + tint amarelo suave no fundo
 * em toda tela que carrega este script, quando /api/impersonando_state
 * retornar ativo=true.
 * ======================================================= */
(function () {
  if (window.__f10ImpInstalled) return;
  window.__f10ImpInstalled = true;

  function escapeHtml(s) {
    return String(s || '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function injetar(nome) {
    if (!document.getElementById('f10-imp-style')) {
      const s = document.createElement('style');
      s.id = 'f10-imp-style';
      s.textContent = `
.f10-imp-banner {
    position: fixed; top: 0; left: 0; right: 0; z-index: 9999;
    background: repeating-linear-gradient(45deg, #fde68a 0 12px, #fcd34d 12px 24px);
    color: #78350f; padding: 6px 20px;
    display: flex; align-items: center; gap: 14px; flex-wrap: wrap;
    font-size: 13px; font-weight: 600;
    font-family: 'IBM Plex Sans', Arial, sans-serif;
    box-shadow: 0 2px 8px rgba(0,0,0,0.10);
}
.f10-imp-banner .f10-imp-icone { font-size: 18px; line-height: 1; }
.f10-imp-banner a {
    background: #fff; color: #78350f; padding: 3px 12px;
    border: 1px solid #d97706; border-radius: 6px;
    font-weight: 700; font-size: 12px; text-decoration: none;
    margin-left: auto; white-space: nowrap;
}
.f10-imp-banner a:hover { background: #fef3c7; }
body.f10-imp-tint {
    background:
      linear-gradient(180deg, rgba(251,191,36,0.10) 0%, rgba(251,191,36,0.04) 220px, rgba(251,191,36,0) 500px),
      #fffbeb !important;
}
      `;
      document.head.appendChild(s);
    }
    if (!document.querySelector('.f10-imp-banner')) {
      const div = document.createElement('div');
      div.className = 'f10-imp-banner';
      div.innerHTML =
        '<span class="f10-imp-icone">🎭</span>' +
        '<span>MODO ADMIN — Você está processando como <strong>' + escapeHtml(nome) + '</strong>. Alterações são gravadas no cliente.</span>' +
        '<a href="/parar_impersonar">Voltar ao Admin</a>';
      document.body.insertBefore(div, document.body.firstChild);
    }
    document.body.classList.add('f10-imp-tint');
    if (!document.body.style.paddingTop) {
      document.body.style.paddingTop = '34px';
    }
  }

  function checar() {
    fetch('/api/impersonando_state', { credentials: 'same-origin' })
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d && d.ativo) injetar(d.nome || ''); })
      .catch(() => {});
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', checar);
  } else {
    checar();
  }
})();

/* =========================================================
 * Ajuste dinâmico: fonte da "Versão" = largura da logomarca
 * Mede a largura do logo (.topo-logo-img) e escala a fonte da
 * .topo-versao para a linha da versão ficar com a MESMA largura
 * horizontal — em qualquer tela e qualquer formato de versão.
 * ======================================================= */
(function () {
  if (window.__f10VersaoFitInstalled) return;
  window.__f10VersaoFitInstalled = true;

  function ajustar() {
    document.querySelectorAll('.topo').forEach(function (topo) {
      var img = topo.querySelector('.topo-logo-img');
      var ver = topo.querySelector('.topo-versao');
      if (!img || !ver) return;
      var larguraLogo = img.getBoundingClientRect().width;
      if (!larguraLogo) return;                       // imagem ainda não carregou
      // mede a versão a 10px e escala proporcionalmente (largura ∝ font-size)
      ver.style.setProperty('font-size', '10px', 'important');
      var atual = ver.scrollWidth || ver.getBoundingClientRect().width;
      if (atual > 0) {
        var alvo = 10 * (larguraLogo / atual);
        alvo = Math.max(6, Math.min(alvo, 22));       // limites de segurança
        ver.style.setProperty('font-size', alvo.toFixed(2) + 'px', 'important');
      }
    });
  }

  function agendar() {
    ajustar();
    document.querySelectorAll('.topo .topo-logo-img').forEach(function (img) {
      if (!img.complete) img.addEventListener('load', ajustar);
    });
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(ajustar);
    window.addEventListener('load', ajustar);
    window.addEventListener('resize', ajustar);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', agendar);
  } else {
    agendar();
  }
})();
