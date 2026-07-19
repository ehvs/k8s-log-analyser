// Frontend vanilla — consome a API JSON da rag-api via proxy /api (mesma origem).
const form = document.getElementById("chat-form");
const input = document.getElementById("question");
const messages = document.getElementById("messages");
const spinner = document.getElementById("spinner");
const button = form.querySelector("button");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = input.value.trim();
  if (!question) return;

  appendMessage("user", question);
  input.value = "";
  setLoading(true);

  try {
    const resp = await fetch("/api/ask", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ question }),
    });

    if (!resp.ok) {
      const detail =
        resp.status === 503
          ? "Serviço indisponível — a base pode não estar indexada ou o modelo ainda está carregando."
          : `Erro ${resp.status}`;
      appendMessage("error", detail);
      return;
    }

    const data = await resp.json();
    appendMessage("assistant", data.answer, data.sources);
  } catch (err) {
    appendMessage("error", `Falha de rede: ${err.message}`);
  } finally {
    setLoading(false);
  }
});

function setLoading(on) {
  spinner.hidden = !on;
  button.disabled = on;
}

// textContent evita XSS ao inserir o conteúdo do modelo/base no DOM.
function appendMessage(role, text, sources) {
  const msg = document.createElement("div");
  msg.className = `msg msg--${role}`;

  const body = document.createElement("p");
  body.className = "msg__text";
  body.textContent = text;
  msg.appendChild(body);

  if (Array.isArray(sources) && sources.length) {
    const src = document.createElement("p");
    src.className = "msg__sources";
    src.textContent = "Fontes: " + [...new Set(sources)].join(", ");
    msg.appendChild(src);
  }

  messages.appendChild(msg);
  msg.scrollIntoView({ behavior: "smooth", block: "end" });
}
