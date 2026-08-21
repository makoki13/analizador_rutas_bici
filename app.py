import tempfile  # Librería para crear archivos temporales

import gpxpy
import gradio as gr
import ollama


def generar_hoja_ruta(gpx_track_file, gpx_route_file, cuesheet_file):  # noqa: C901
    # 1. Comprobamos que el usuario ha subido los archivos mínimos
    if gpx_track_file is None and gpx_route_file is None:
        return "⚠️ Por favor, sube al menos un archivo GPX (Track o Route).", None
    if cuesheet_file is None:
        return "⚠️ Por favor, sube el archivo CSV de la cuesheet.", None

    # 2. Leemos el archivo CSV (Cuesheet)
    try:
        with open(cuesheet_file, encoding='utf-8') as f:
            cuesheet_text = f.read()
    except Exception as e:
        return f"Error leyendo el archivo CSV: {e}", None

    # 3. Extraemos datos del GPX TRACK (Geometría y altimetría)
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

    # 4. Extraemos datos del GPX ROUTE (Puntos de navegación/Waypoints)
    route_info = "No se proporcionó GPX Route."
    if gpx_route_file:
        try:
            with open(gpx_route_file, encoding='utf-8') as f:
                gpx_content = f.read()
            gpx_route = gpxpy.parse(gpx_content)

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

    # 5. Preparamos el texto para la IA (El Prompt Mejorado)
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

    # 6. Hablamos con la IA LOCAL usando Ollama
    try:
        respuesta = ollama.chat(
            model='qwen2.5:3b',
            messages=[{'role': 'user', 'content': texto_para_ia}],
            options={'temperature': 0.3}
        )
        resultado = respuesta['message']['content']

        # --- NUEVO: Guardamos el resultado en un archivo temporal para descargar ---
        # Creamos un archivo temporal con extensión .txt
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as temp_file:
            temp_file.write(resultado)
            ruta_archivo = temp_file.name # Guardamos la ruta donde se ha creado

        # Devolvemos el texto para la pantalla Y la ruta del archivo para el botón de descarga
        return resultado, ruta_archivo

    except Exception as e:
        return f"Parece que Ollama no está corriendo o el modelo no se ha descargado aún. Error: {e}", None

# 7. Construimos la interfaz visual (Ahora con 2 salidas: Texto y Archivo)
interfaz = gr.Interface(
    fn=generar_hoja_ruta,
    inputs=[
        gr.File(label="1. Sube tu GPX Track (Geometría)", file_types=[".gpx"]),
        gr.File(label="2. Sube tu GPX Route (Navegación)", file_types=[".gpx"]),
        gr.File(label="3. Sube tu Cuesheet (CSV)", file_types=[".csv", ".txt"])
    ],
    outputs=[
        gr.Textbox(lines=25, label="4. Rutómetro y Análisis (Pantalla)"),
        gr.File(label="5. Descargar Rutómetro (.txt)") # <-- Nuevo botón de descarga
    ],
    title="🚴‍♂️ Analizador de Rutas en Bicicleta IA (100% Local)",
    description="Sube el Track, el Route y el CSV para generar el documento para el manillar."
)

# 8. Lanzamos la app
if __name__ == "__main__":
    interfaz.launch()
