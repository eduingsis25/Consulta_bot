import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import requests  # ¡Ahora sí la usamos para tu API!

# --- CONFIGURACIÓN ---
# Reemplaza 'TU_TOKEN_DE_BOT' con el token que te dio BotFather
TOKEN = '7963130345:AAHaCoLCVPrjJXqXlZnXAacaMJ0MTuGBuT0'

# URLs de tus endpoints de API
# AJUSTA ESTAS URLs según cómo tengas configurada tu API
API_VOTACION_URL = 'http://repjcs.onrender.com/api/elector'
API_CENSADO_URL = 'http://repjcs.onrender.com/api/censo'

# Puedes agregar una clave API si tu API lo requiere para autenticación
# API_KEY = 'TU_API_KEY_SI_ES_NECESARIA'
# HEADERS = {'Authorization': f'Bearer {API_KEY}'} # Ejemplo de header para API Key

# --- FUNCIONES DEL BOT ---


def start(update, context):
    """Maneja el comando /start."""
    update.message.reply_text(
        '¡Hola! Soy Progreso, tu bot de consulta de cédulas. Por favor, usa los siguientes comandos:\n\n'
        '➡️ /consulta [número de cédula]: Consulta el centro de votación.\n'
        '➡️ /censo [número de cédula]: Consulta si la persona está censada y otros datos.\n\n'
        '**Ejemplo:** /consulta 12345678'
    )


def _consultar_api(update, context, api_url, tipo_consulta):
    """Función auxiliar para realizar la petición a tu API."""
    args = context.args
    if not args:
        update.message.reply_text(
            f'Por favor, ingresa el número de cédula después del comando. Ejemplo: /{tipo_consulta} 12345678')
        return

    # Convertir a mayúsculas por si tu API espera el prefijo (V, E, P)
    cedula = int(args)

    update.message.reply_text(
        f'Consultando tu API para la cédula {cedula} ({tipo_consulta})...')

    try:
        # Prepara los parámetros para la petición GET o POST
        params = {'cedula': cedula}
        # headers = HEADERS # Descomenta si usas una API Key

        # Realiza la petición a tu API
        # Si tu API usa POST, usa requests.post(api_url, json=params)
        response = requests.get(api_url, params=params)
        # Lanza una excepción para códigos de error HTTP (4xx o 5xx)
        response.raise_for_status()

        data = response.json()  # Asume que tu API devuelve JSON

        # --- AQUÍ ES DONDE PERSONALIZAS LA RESPUESTA ---
        # El formato de 'data' depende de lo que tu API devuelva.
        # Ajusta esta lógica para extraer los campos correctos.

        mensaje_respuesta = ""
        if tipo_consulta == "votacion":
            # Asumiendo que tu API tiene un campo 'encontrado'
            if data and data.get('cedula', False):
                nacionalidad = data.get('nacionalidad', 'N/A')
                pnombre = data.get('nombre', 'N/A')
                snombre = data.get('nombre', 'N/A')
                papellido = data.get('nombre', 'N/A')
                sapellido = data.get('nombre', 'N/A')
                cv = data.get('centro_votacion', 'No especificado')

                mensaje_respuesta = (
                    f"✅ **Centro de Votación para (C.I. {nacionalidad}{cedula}):**\n"
                    f"   🗳️ **Primer Nombre:** {pnombre}\n"
                    f"   🗳️ **Segundo Nombre:** {snombre}\n"
                    f"   🗳️ **Primer Apellido:** {papellido}\n"
                    f"   🗳️ **Segundo Apellido:** {sapellido}\n"
                    f"   🗳️ **Centro de Votación:** {cv}\n"
                )
            else:
                mensaje_respuesta = f"❌ No se encontró centro de votación para la cédula {cedula} o la cédula no está registrada para votar en el municipio."

        # elif tipo_consulta == "censado":
        #     if data and data.get('encontrado', False):
        #         nombre_completo = data.get('nombre_completo', 'N/A')
        #         fecha_nacimiento = data.get('fecha_nacimiento', 'N/A')
        #         estado = data.get('estado', 'N/A')
        #         municipio = data.get('municipio', 'N/A')

        #         mensaje_respuesta = (
        #             f"✅ **Datos Censados para {nombre_completo} (C.I. {cedula}):**\n"
        #             f"   🎂 **Fecha Nacimiento:** {fecha_nacimiento}\n"
        #             f"   🗺️ **Ubicación Censal:** {municipio}, {estado}"
        #             # Agrega más campos si tu API los devuelve (ej. dirección, etc.)
        #         )
        #     else:
        #         mensaje_respuesta = f"❌ No se encontraron datos censales para la cédula {cedula}."

        # else:
        #     mensaje_respuesta = "Tipo de consulta desconocido en el procesamiento interno."

        update.message.reply_text(
            mensaje_respuesta, parse_mode=telegram.ParseMode.MARKDOWN)

    except requests.exceptions.RequestException as e:
        # Manejo de errores de red o HTTP (ej. API no disponible, 404, 500)
        update.message.reply_text(
            f'❌ Error al conectar con tu API: {e}. Por favor, verifica la URL de la API o inténtalo más tarde.')
    except ValueError:
        # Manejo de errores si la respuesta de la API no es un JSON válido
        update.message.reply_text(
            '❌ Error al procesar la respuesta de tu API. El formato no es válido.')
    except Exception as e:
        # Otros errores inesperados
        update.message.reply_text(f'❌ Ocurrió un error inesperado: {e}.')


def consultar_votacion(update, context):
    """Maneja el comando /consulta."""
    _consultar_api(update, context, API_VOTACION_URL, "elector")


def consultar_censado(update, context):
    """Maneja el comando /censo."""
    _consultar_api(update, context, API_CENSADO_URL, "censo")


def main():
    """Función principal para iniciar el bot."""
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Añadir manejadores de comandos
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("consulta", consultar_votacion))
    dp.add_handler(CommandHandler("censo", consultar_censado))

    # Iniciar el bot
    updater.start_polling()
    updater.idle()  # Mantener el bot en ejecución hasta que se presione Ctrl+C


if __name__ == '__main__':
    main()
