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

export async function onRequestPost(context) {
  try {
    if (!context.env.OLLAMA_API_KEY) {
      return json({ error: "Falta configurar el secreto OLLAMA_API_KEY en Cloudflare Pages." }, 500);
    }

    const body = await context.request.json();
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
        "Authorization": "Bearer " + context.env.OLLAMA_API_KEY,
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
      return json({ error: "El servicio de IA ha devuelto un error (" + upstream.status + "). Revisa la clave y el acceso al modelo en Cloudflare." }, 502);
    }

    const result = await upstream.json();
    const content = result && result.message && result.message.content;
    if (typeof content !== "string") {
      return json({ error: "El servicio de IA no devolvió una respuesta válida." }, 502);
    }

    let parsed;
    try {
      parsed = JSON.parse(content);
    } catch {
      parsed = { respuesta: content };
    }
    const answer = typeof parsed.respuesta === "string" ? parsed.respuesta
      : typeof parsed.content === "string" ? parsed.content
      : content;

    return json({
      intencion: typeof parsed.intencion === "string" ? parsed.intencion : "responder",
      respuesta: answer
    });
  } catch (error) {
    console.error("Chat function error", error);
    return json({ error: "No se ha podido procesar el mensaje. Comprueba la configuración e inténtalo de nuevo." }, 500);
  }
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store"
    }
  });
}
