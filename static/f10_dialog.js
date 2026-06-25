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
    return { backdrop, tipo, fechar };
  }

  // ── f10Alert ──
  window.f10Alert = function f10Alert(msg, opts) {
    opts = Object.assign({ msg }, opts || {});
    return new Promise((resolve) => {
      const { backdrop, tipo, fechar } = criarModal(opts);
      const acoes = backdrop.querySelector('.f10dlg-acoes');
      const btn = document.createElement('button');
      btn.className = 'f10dlg-btn f10dlg-btn-ok-' + tipo;
      btn.textContent = opts.okText || 'OK';
      btn.onclick = () => { fechar(); resolve(); };
      acoes.appendChild(btn);
      btn.focus();

      // ESC fecha
      backdrop.addEventListener('keydown', (e) => {
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
      const { backdrop, tipo, fechar } = criarModal(opts);
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
      const { backdrop, tipo, fechar } = criarModal(opts);
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
