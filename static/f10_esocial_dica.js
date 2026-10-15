/* =========================================================
 * Folha10 Simples — "Entenda o erro" do eSocial
 *
 * A mensagem do governo fica na tela como veio; o botao abre, embaixo dela,
 * a explicacao simples e o caminho da solucao. O texto vem do servidor
 * (_ESOCIAL_DICAS no app.py, rota /api/esocial_explicar_erro), montado na
 * hora a partir da remessa gravada em tab_esocial.
 *
 * Usado na Fila e na tela do S-3000. Precisa do f10_dialog.js (f10Alert).
 * ======================================================= */

/* Botao para uma remessa recem-recusada (resposta do Enviar/Consultar).
   So' aparece quando a mensagem traz um codigo [NNN]; se o codigo nao estiver
   no dicionario, o clique avisa que ainda nao ha explicacao. */
function _btnDica(id, msg) {
  // Codigo [NNN] ou erro que chega sem codigo (ver _ESOCIAL_DICAS_TEXTO no app.py)
  if (!id || !/\[\d{1,5}\]|assinante inv[aá]lido/i.test(String(msg || ''))) return '';
  return `<button type="button" class="btn-dica" onclick="_explicarErro(${id})"
          title="Explicação simples do erro e como resolver">&#128161; Entenda o erro</button>`;
}

async function _explicarErro(id) {
  let d;
  try {
    const r = await fetch(`/api/esocial_explicar_erro?id=${id}`);
    d = await r.json();
  } catch (e) {
    f10Alert('Não foi possível buscar a explicação agora.', { tipo: 'erro' });
    return;
  }
  if (!d.ok) {
    f10Alert(d.msg || 'Sem explicação para este erro.', { tipo: 'info', titulo: 'Entenda o erro' });
    return;
  }
  const passos = (d.solucao || []).map((p, i) => `${i + 1}. ${p}`).join('\n');
  const texto  = 'MENSAGEM DO eSOCIAL\n' + (d.msg_gov || '') +
                 '\n\nEM PALAVRAS SIMPLES\n' + d.simples +
                 (d.contexto ? '\n\n' + d.contexto : '') +
                 '\n\nCOMO RESOLVER\n' + passos;
  const _cod = /^\d+$/.test(String(d.codigo || '')) ? ` [${d.codigo}]` : '';
  f10Alert(texto, { tipo: 'info', titulo: `Entenda o erro${_cod}` });
}
