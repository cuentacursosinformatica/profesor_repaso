
import json
import os
import urllib.request
import urllib.error
import subprocess
import tempfile
import os
import re


# ==========================================
# CONFIGURACIÓN
# ==========================================

# 9431062a78b6468ea6786752cb99375

API_KEY = "9431062a78b6468ea6786752cb99375c.DkPUx"
MODELO = "gpt-oss:120b"
URL_API = "https://ollama.com/api/chat"


SYSTEM_PROMPT = """

En cada mensaje debes:
1. Detectar la intención del usuario.
2. Responder de forma natural y adecuada a esa intención.

Las intenciones posibles son:
- "despedirse": quiere terminar la conversación o marcharse.
- "continuar": quiere seguir aprendiendo.
- "responder": contesta a una pregunta del test.
- "ayuda": pide una explicación o ayuda.
- "otra": cualquier otra intención.

Interpreta el significado, no solo las palabras.
Ejemplos:
"Me voy" -> despedirse.
"Quiero irme" -> despedirse.
"Hasta luego" -> despedirse.
"No me quiero ir todavía" -> continuar.
"Quiero otra pregunta" -> continuar.
"La respuesta es la b" -> responder.
"No entiendo" -> ayuda.

Devuelve SIEMPRE un objeto JSON válido con esta estructura:
{
  "intencion": "despedirse",
  "respuesta": "¡Hasta luego! Espero que hayas aprendido mucho."
}

El campo "intencion" debe contener una de las cinco etiquetas
indicadas anteriormente.
El campo "respuesta" debe contener el mensaje para el usuario.
No incluyas texto fuera del JSON.

No incluyas asteriscos en las respuestas ni formato MarkDown en respuestas.
En las preguntas y conversación se breve y raṕido.
Eres un profesor virtual de instituto para alumnos y les ayudas a preparar el examen.
Tu objetivo es enseñarles y repasarles los conceptos básicos de la asignatura que ellos te dirán.
Primero tienes que preguntar el curso y la asignatura y después hacer preguntas tipo test y abierta para comprobar que han aprendido.
Si se equivocan en alguna pregunta, vuelve a preguntar sobre la materia hasta que responde correctamente.
 

Reglas:
- Habla siempre en español o en el idioma que te pida el usuario.
- Explica de forma clara y breve adaptada al usuario y que sea didáctica y con ejemplos reales.
- Haz una pregunta cada vez y corrige educadamente y de forma amable.
- No reveles la solución antes de que el alumno responda.
- Corrige los errores y explica el motivo.
- Aumenta la dificultad progresivamente.
- Mantén la conversación centrada en la asigntura que el alumno elija.
- No respondas a preguntas que no tengan que ver con la materia.
- Anima al alumno a seguir aprendiendo para que no pierda la motivación.
- No uses asteriscos para negritas ni cursivas.
- No utilices almohadillas para títulos.
- Escribe texto sencillo, limpio y legible en la terminal.
- Para enumerar opciones, utiliza letras o números.
- Separa las explicaciones en párrafos.

"""

# Historial de la conversación
mensajes = [
    {
        "role": "system",
        "content": (
            SYSTEM_PROMPT
        )
    }
]


# ==========================================
# FUNCIONES
# ==========================================

def hablar(texto):
    """Lee un texto en español usando la voz de Google Translate."""

    # Dividir respuestas largas en fragmentos pequeños
    palabras = texto.split()
    fragmentos = []
    actual = ""

    for palabra in palabras:
        if len(actual) + len(palabra) + 1 > 180:
            fragmentos.append(actual)
            actual = palabra
        else:
            actual = (actual + " " + palabra).strip()

    if actual:
        fragmentos.append(actual)

    for fragmento in fragmentos:
        archivo = None

        try:
            with tempfile.NamedTemporaryFile(
                suffix=".mp3", delete=False
            ) as temporal:
                archivo = temporal.name

            descarga = subprocess.run(
                [
                    "curl", "-fsSL",
                    "-A", "Mozilla/5.0",
                    "--get",
                    "--data-urlencode", "ie=UTF-8",
                    "--data-urlencode", "client=tw-ob",
                    "--data-urlencode", "tl=es",
                    "--data-urlencode", "q=" + fragmento,
                    "https://translate.google.com/translate_tts",
                    "-o", archivo
                ],
                capture_output=True,
                text=True
            )

            if descarga.returncode != 0:
                print("No se pudo descargar el audio.")
                continue

            reproduccion = subprocess.run(
                [
                    "ffplay", "-nodisp", "-autoexit",
                    "-loglevel", "error",
                    "-af", "atempo=1.5", archivo
                ],
                capture_output=True,
                text=True
            )

            if reproduccion.returncode != 0:
                print("No se pudo reproducir el audio.")

        except Exception as error:
            print(f"Error de voz: {error}")

        finally:
            if archivo and os.path.exists(archivo):
                os.remove(archivo)


def consultar_ollama(mensajes):
    """Envía el historial a Ollama Cloud y devuelve la respuesta."""

    datos = {
        "model": MODELO,
        "messages": mensajes,
        "format": "json",
        "stream": False
    }

    cuerpo = json.dumps(datos).encode("utf-8")

    solicitud = urllib.request.Request(
        URL_API,
        data=cuerpo,
        headers={
            "Authorization": "Bearer " + API_KEY,
            "Content-Type": "application/json"
        },
        method="POST"
    )

    with urllib.request.urlopen(solicitud, timeout=180) as respuesta:
        resultado = json.loads(
            respuesta.read().decode("utf-8")
        )

    return resultado["message"]["content"]



def filtrar_texto_voz(texto):
    # Busca el inicio de la primera opción: a)
    coincidencia = re.search(r"(?m)^\s*a\)\s*", texto, re.IGNORECASE)

    if coincidencia:
        texto = texto[:coincidencia.start()]

    # Elimina formato Markdown, como **Pregunta 1**
    texto = re.sub(r"\*\*(.*?)\*\*", r"\1", texto)

    return texto.strip()



def mostrar_ayuda():
    print("""
COMANDOS DISPONIBLES
--------------------
/salir      Terminar el chat
/limpiar    Borrar el historial
/ayuda      Mostrar estos comandos
""")


# ==========================================
# PROGRAMA PRINCIPAL
# ==========================================

def main():
    if not API_KEY:
        print("ERROR: No has configurado tu clave API.")
        print("Configura la variable OLLAMA_API_KEY.")
        print("Consulta las instrucciones debajo del código.")
        return

    print("=" * 45)
    print("       CHAT PYTHON + OLLAMA CLOUD")
    print("=" * 45)
    print("Modelo:", MODELO)
    print("Escribe /ayuda para ver los comandos.")

    while True:
        try:
            pregunta = input("\nTú: ").strip()

            if not pregunta:
                continue

            comando = pregunta.lower()

            if comando == "/salir":
                print("¡Hasta pronto!")
                break

            if comando == "/ayuda":
                mostrar_ayuda()
                continue

            if comando == "/limpiar":
                mensajes[:] = mensajes[:1]
                print("Historial borrado.")
                continue

            # Añadir la pregunta al historial
            mensajes.append({
                "role": "user",
                "content": pregunta
            })

            try:
                print("\n...pensando...\n")

                respuesta = consultar_ollama(mensajes)

                try:
                    resultado = json.loads(respuesta)
                    #print("Resultado1:",resultado)
                    intencion = resultado.get("intencion", "otra")
                    print("Intención:",intencion)
                    respuesta = resultado.get("respuesta", "")
                    #print("Respuesta:",respuesta)

                    if intencion not in {"despedirse", "continuar", "responder", "ayuda", "otra"}:intencion = "otra"

                except (json.JSONDecodeError, TypeError):
                    intencion = "otra"
                    respuesta = contenido

                print("IA:", respuesta)
                texto_voz = filtrar_texto_voz(respuesta)
                if texto_voz: hablar(texto_voz)

                if intencion == "despedirse":
                    print("Sesión finalizada.")
                    break


                # Guardar la respuesta para mantener el contexto
                mensajes.append({
                    "role": "assistant",
                    "content": respuesta
                })

            except urllib.error.HTTPError as error:
                print("ERROR HTTP:", error.code)

                detalle = error.read().decode(
                    "utf-8", errors="replace"
                )
                print("Detalle:", detalle)

                mensajes.pop()

            except urllib.error.URLError as error:
                print("ERROR DE CONEXIÓN:", error.reason)
                mensajes.pop()

            except (KeyError, ValueError, TypeError) as error:
                print("ERROR EN LA RESPUESTA:", error)
                mensajes.pop()

            except TimeoutError:
                print("La conexión ha tardado demasiado.")
                mensajes.pop()

        except (KeyboardInterrupt, EOFError):
            print("\nChat finalizado.")
            break


if __name__ == "__main__":
    main()
