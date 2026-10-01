// Leitura das respostas das telas do eSocial.
// Quando o servidor devolve HTML (502/503/504 do Render, eSocial fora do ar) em
// vez de JSON, troca o "SyntaxError: Unexpected token '<'" por uma mensagem clara.

async function lerRespostaJson(r) {
  const txt = await r.text();
  try {
    return JSON.parse(txt);
  } catch (_) {
    if ([502, 503, 504].includes(r.status) || /timeout|gateway/i.test(txt))
      throw new Error('O eSocial demorou para responder ou está fora do ar no momento. ' +
                      'Aguarde alguns minutos e confira a situação antes de enviar de novo.');
    throw new Error('O servidor não respondeu corretamente (código ' + r.status + '). ' +
                    'Aguarde alguns minutos e tente de novo.');
  }
}

// Texto da falha para o cliente (sem o nome tecnico do erro).
function msgFalha(e) {
  if (e instanceof TypeError && /fetch|network|load failed/i.test(e.message || ''))
    return 'Sem conexão com o servidor. Verifique a internet e tente de novo.';
  return (e && e.message) ? e.message : String(e);
}
