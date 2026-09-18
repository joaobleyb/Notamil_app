/* Contadores +/- da tela de geracao de prova. */
document.addEventListener("click", function (evento) {
  const botao = evento.target.closest("[data-passo]");
  if (!botao) return;

  const campo = document.getElementById(botao.dataset.alvo);
  if (!campo) return;

  const atual = parseInt(campo.value, 10) || 0;
  campo.value = Math.max(0, atual + parseInt(botao.dataset.passo, 10));
});

document.addEventListener("change", function (evento) {
  if (!evento.target.matches(".contador input")) return;

  const valor = parseInt(evento.target.value, 10);
  evento.target.value = Number.isNaN(valor) || valor < 0 ? 0 : valor;
});
