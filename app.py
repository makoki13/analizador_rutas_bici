import gpxpy
import gradio as gr
import ollama


def generar_hoja_ruta(gpx_track_file, gpx_route_file, cuesheet_text):
    # 1. Comprobamos que el usuario ha subido los archivos mínimos
    if gpx_track_file is None and gpx_route_file is None:
        return "⚠️ Por favor, sube al menos un archivo GPX (Track o Route)."
    if not cuesheet_text:
        return "⚠️ Por favor, pega el contenido de tu cuesheet CSV."

    # 2. Extraemos datos del GPX TRACK (Geometría y altimetría)
    track_info = "No se proporcionó GPX Track."
    if gpx_track_file:
        try:
            with open(gpx_track_file, encoding='utf-8') as f:
                gpx_content = f.read()
            gpx_track = gpxpy.parse(gpx_content)

            segment = gpx_track.tracks[0].segments[0]
            distancias = segment.length_3d()
            desniveles = segment.get_uphill_downhill()
            desnivel_pos = desniveles.uphill
            desnivel_neg = desniveles.downhill

            track_info = f"""
- Distancia total: {distancias/1000:.2f} km
- Desnivel positivo (+): {desnivel_pos:.1f} metros
- Desnivel negativo (-): {desnivel_neg:.1f} metros"""
        except Exception as e:
            track_info = f"Error leyendo el GPX Track: {e}"

    # 3. Extraemos datos del GPX ROUTE (Puntos de navegación/Waypoints)
    route_info = "No se proporcionó GPX Route."
    if gpx_route_file:
        try:
            with open(gpx_route_file, encoding='utf-8') as f:
                gpx_content = f.read()
            gpx_route = gpxpy.parse(gpx_content)

            # Extraemos los puntos de la ruta
            puntos_ruta = []
            if len(gpx_route.routes) > 0:
                for point in gpx_route.routes[0].points:
                    nombre = point.name if point.name else "Punto sin nombre"
                    puntos_ruta.append(f"Lat: {point.latitude}, Lon: {point.longitude} - {nombre}")
                route_info = "\n".join(puntos_ruta)
            else:
                route_info = "El archivo GPX Route no contiene nodos de ruta (<rte>)."
        except Exception as e:
            route_info = f"Error leyendo el GPX Route: {e}"

    # 4. Preparamos el texto para la IA (El Prompt Mejorado)
    texto_para_ia = f"""Eres un director deportivo de ciclismo experto en crear hojas de ruta (rutómetros) y analizar recorridos.
Tienes tres fuentes de información para cruzar:

1. RESUMEN DEL GPX TRACK (Geometría y altimetría real):
{track_info}

2. GPX ROUTE (Nodos de navegación con sus nombres):
{route_info}

3. CUESHEET (Indicaciones de giro en formato CSV de RideWithGPS):
{cuesheet_text}

Tu tarea es crear el RUTÓMETRO DEFINITIVO PARA EL CICLISTA. Sigue ESTRICTAMENTE estas reglas:

1. ANÁLISIS DEL RECORRIDO:
Escribe un párrafo resumiendo la ruta basándote en la distancia y desniveles reales del GPX Track. SÉ REALISTA con la dificultad.

2. HOJA DE GIRA PARA EL MANILLAR (Rutómetro):
Crea una lista que el ciclista pueda imprimir. Debes INCLUIR TODOS LOS GIROS REALES donde cambie el nombre de la calle o carretera, cruzando la información de la Cuesheet con los nombres del GPX Route.
REGLAS DE EXCLUSIÓN: Omite SOLO las líneas que digan "Keep right" o "Keep left" y las rotondas donde se diga "Straight" o "Continue" si no hay cambio de carretera.
Formato estricto: "Km [Distancia] - [Dirección] - [Nombre de la calle]".
"""

    # 5. Hablamos con la IA LOCAL usando Ollama
    try:
        respuesta = ollama.chat(
            model='qwen2.5:3b',
            messages=[{'role': 'user', 'content': texto_para_ia}],
            options={'temperature': 0.3}
        )
        return respuesta['message']['content']
    except Exception as e:
        return f"Parece que Ollama no está corriendo o el modelo no se ha descargado aún. Error: {e}"

# 6. Construimos la interfaz visual (Ahora con 3 entradas)
interfaz = gr.Interface(
    fn=generar_hoja_ruta,
    inputs=[
        gr.File(label="1. Sube tu GPX Track (Geometría)", file_types=[".gpx"]),
        gr.File(label="2. Sube tu GPX Route (Navegación)", file_types=[".gpx"]),
        gr.Textbox(lines=15, label="3. Pega aquí tu Cuesheet (CSV)", placeholder="Pega aquí el contenido de tu archivo CSV...")
    ],
    outputs=gr.Textbox(lines=25, label="4. Rutómetro y Análisis"),
    title="🚴‍♂️ Analizador de Rutas en Bicicleta IA (100% Local)",
    description="Sube el Track, el Route y pega la cuesheet para generar el documento para el manillar."
)

# 7. Lanzamos la app
if __name__ == "__main__":
    interfaz.launch()
