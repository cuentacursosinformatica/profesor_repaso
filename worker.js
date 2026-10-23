const SYSTEM_PROMPT = `Eres un profesor particular paciente y motivador que habla español. Tu objetivo es ayudar al alumno a repasar y aprender.
- Si aún no conoces el curso o nivel y la asignatura, pregúntalos de forma breve.
- Adapta el vocabulario y la dificultad al nivel del alumno.
- Alterna preguntas tipo test y preguntas abiertas cuando sea apropiado.
- Haz una pregunta cada vez y espera la respuesta antes de continuar.
- Cuando el alumno responda, indica si es correcto. Explica el razonamiento de forma clara y breve, y corrige los errores con amabilidad.
- Aumenta la dificultad gradualmente cuando el alumno progrese.
- Si pide ayuda o una pista, ofrece una pista sin revelar automáticamente toda la solución.
- Si pide otra pregunta, propón una nueva relacionada con la materia.
- Si quiere terminar, despídete cordialmente.
- Mantén el foco en la conversación y evita inventar datos.
Devuelve exclusivamente un objeto JSON válido con dos campos: "intencion" y "respuesta".
"intencion" debe ser una de estas etiquetas: "responder", "ayuda", "otra", "continuar", "despedirse".
"respuesta" debe contener el texto que verá el alumno. No uses bloques Markdown alrededor del JSON.`;

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/api/chat") {
      if (request.method !== "POST") {
        return json({ error: "Usa POST para enviar un mensaje al chat." }, 405, {
          Allow: "POST, OPTIONS"
        });
      }
      return handleChat(request, env);
    }

    if (url.pathname.startsWith("/api/")) {
      return json({ error: "Ruta de API no encontrada." }, 404);
    }

    return env.ASSETS.fetch(request);
  }
};

async function handleChat(request, env) {
  try {
    if (!env.OLLAMA_API_KEY) {
      return json({ error: "Falta configurar el secreto OLLAMA_API_KEY en Cloudflare Workers." }, 500);
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return json({ error: "El cuerpo de la petición debe ser JSON válido." }, 400);
    }

    const incoming = Array.isArray(body.messages) ? body.messages : [];
    const messages = incoming
      .filter(m => m && (m.role === "user" || m.role === "assistant") && typeof m.content === "string")
      .slice(-30)
      .map(m => ({ role: m.role, content: m.content.slice(0, 6000) }));

    if (!messages.length || messages[messages.length - 1].role !== "user") {
      return json({ error: "Envía un mensaje para empezar." }, 400);
    }

    const upstream = await fetch("https://ollama.com/api/chat", {
      method: "POST",
      headers: {
        "Authorization": "Bearer " + env.OLLAMA_API_KEY,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        model: "gpt-oss:120b",
        stream: false,
        format: "json",
        messages: [{ role: "system", content: SYSTEM_PROMPT }, ...messages]
      })
    });

    if (!upstream.ok) {
      const detail = (await upstream.text()).slice(0, 500);
      console.error("Ollama API error", upstream.status, detail);
      return json({
        error: "Ollama ha devuelto un error (" + upstream.status + "). Comprueba el secreto y el acceso al modelo."
      }, 502);
    }

    const result = await upstream.json();
    const content = result && result.message && result.message.content;
    if (typeof content !== "string") {
      return json({ error: "Ollama no devolvió una respuesta válida." }, 502);
    }

    let parsed;
    try {
      parsed = JSON.parse(content);
    } catch {
      parsed = { respuesta: content };
    }

    return json({
      intencion: typeof parsed.intencion === "string" ? parsed.intencion : "responder",
      respuesta: typeof parsed.respuesta === "string" ? parsed.respuesta
        : typeof parsed.content === "string" ? parsed.content
        : content
    });
  } catch (error) {
    console.error("Worker chat error", error);
    return json({ error: "No se ha podido procesar el mensaje. Revisa los registros del Worker." }, 500);
  }
}

function json(data, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      ...extraHeaders
    }
  });
}
