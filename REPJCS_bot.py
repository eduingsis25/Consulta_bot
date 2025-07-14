import os
import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler
# Correcto para versiones modernas de python-telegram-bot
from telegram.ext import filters
import requests

# --- CONFIGURACIÓN ---
# Leer el token de Telegram desde las variables de entorno
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    raise ValueError(
        "TELEGRAM_BOT_TOKEN no está configurada como variable de entorno.")

# URL de tu endpoint de API para consulta electoral (votación)
API_VOTACION_URL = os.environ.get('API_VOTACION_URL')
if not API_VOTACION_URL:
    raise ValueError(
        "API_VOTACION_URL no está configurada como variable de entorno.")

# La API_CENSADO_URL y su manejo se eliminan por ahora, según tu indicación.
# Se considerará para una futura versión.


# --- FUNCIONES DEL BOT ---

def start(update, context):
    """Maneja el comando /start."""
    update.message.reply_text(
        '¡Hola! Soy Progreso, tu bot de consulta de cédulas.\n\n'
        'Actualmente, solo puedo consultar el centro de votación.\n'
        '➡️ `/consulta [número de cédula]`: Consulta tu centro de votación.\n\n'
        '**Ejemplo:** `/consulta V12345678`',
        # Asegura que el formato Markdown se aplique
        parse_mode=telegram.ParseMode.MARKDOWN
    )


def consultar_elector(update, context):
    """Maneja el comando /consulta para obtener datos electorales."""
    args = context.args
    if not args:
        update.message.reply_text(
            'Por favor, ingresa el número de cédula después del comando. Ejemplo: `/consulta V12345678`',
            parse_mode=telegram.ParseMode.MARKDOWN
        )
        return

    # Obtener la cédula, limpiar espacios, y convertir a mayúsculas
    cedula_input = args[0].strip().upper()

    # Validación de cédula venezolana (V, E, P + números)
    # Asumimos que la API puede manejar el prefijo (V, E, P) como parte de la cédula string
    if not (len(cedula_input) > 1 and cedula_input[0] in ('V', 'E', 'P') and cedula_input[1:].isdigit()):
        update.message.reply_text(
            'Formato de cédula incorrecto. Debe empezar con V, E o P seguido de números. Ejemplo: V12345678')
        return

    update.message.reply_text(
        f'Consultando tu API para la cédula {cedula_input}...')

    try:
        # Prepara los parámetros para la petición GET. Se envía la cédula como string.
        params = {'cedula': cedula_input}

        # Realiza la petición a tu API de votación
        response = requests.get(API_VOTACION_URL, params=params)
        # Lanza una excepción para códigos de error HTTP (4xx o 5xx)
        response.raise_for_status()

        data = response.json()  # Asume que tu API devuelve JSON

        mensaje_respuesta = ""
        # Verifica si tu API devolvió datos válidos para la cédula
        # Asumo que la presencia de 'cedula' en la respuesta JSON indica éxito.
        # Ajusta 'data.get('cedula')' a la clave que tu API usa para indicar que encontró el registro.
        if data and data.get('cedula'):
            # --- PERSONALIZA AQUÍ LA EXTRACCIÓN DE CAMPOS SEGÚN LA RESPUESTA DE TU API ---
            # ¡IMPORTANTE! Reemplaza 'pnombre', 'snombre', etc. con los nombres EXACTOS de las claves JSON de tu API.
            nacionalidad = data.get('nacionalidad', 'N/A')
            # Revisa: ¿tu API devuelve 'pnombre' o 'primerNombre'?
            primer_nombre = data.get('pnombre', 'N/A')
            # Revisa: ¿tu API devuelve 'snombre' o 'segundoNombre'?
            segundo_nombre = data.get('snombre', 'N/A')
            # Revisa: ¿tu API devuelve 'papellido' o 'primerApellido'?
            primer_apellido = data.get('papellido', 'N/A')
            # Revisa: ¿tu API devuelve 'sapellido' o 'segundoApellido'?
            segundo_apellido = data.get('sapellido', 'N/A')
            # Revisa: ¿tu API devuelve 'cv' o 'centro_votacion'?
            centro_votacion = data.get('cv', 'No especificado')
            # Añade otros campos si tu API los devuelve, por ejemplo:
            # direccion_centro = data.get('direccion_centro', 'N/A')
            # mesa_votacion = data.get('mesa', 'N/A')

            # Construir el nombre completo para la presentación
            nombre_completo = f"{primer_nombre} {segundo_nombre}".strip()
            apellido_completo = f"{primer_apellido} {segundo_apellido}".strip()

            mensaje_respuesta = (
                f"✅ **Datos del Elector:**\n"
                f"   👤 **Cédula:** {nacionalidad}{data.get('cedula', 'N/A')}\n"
                f"   **Nombre:** {nombre_completo if nombre_completo else 'N/A'}\n"
                f"   **Apellido:** {apellido_completo if apellido_completo else 'N/A'}\n"
                f"   🗳️ **Centro de Votación:** {centro_votacion}\n"
                # f"   📍 **Dirección:** {direccion_centro}\n" # Descomentar si usas
                # f"   🪑 **Mesa:** {mesa_votacion}" # Descomentar si usas
            )
        else:
            # Mensaje si no se encuentran datos para la cédula
            mensaje_respuesta = (
                f"❌ No se encontró información electoral para la cédula {cedula_input}. "
                f"Por favor, verifica el número."
            )

        update.message.reply_text(
            mensaje_respuesta, parse_mode=telegram.ParseMode.MARKDOWN)

    except requests.exceptions.RequestException as e:
        # Manejo de errores de red o HTTP (ej. API no disponible, 404, 500)
        update.message.reply_text(
            f'❌ Error al conectar con tu API: {e}. Por favor, verifica la URL de la API o inténtalo más tarde.')
    except ValueError:
        # Manejo de errores si la respuesta de la API no es un JSON válido
        update.message.reply_text(
            '❌ Error al procesar la respuesta de tu API. El formato de la respuesta no es válido.')
    except Exception as e:
        # Otros errores inesperados
        update.message.reply_text(f'❌ Ocurrió un error inesperado: {e}.')


def main():
    """Función principal para iniciar el bot."""
    updater = Updater(TOKEN)  # CORREGIDO: Eliminado use_context=True
    dp = updater.dispatcher

    # Añadir manejadores de comandos
    dp.add_handler(CommandHandler("start", start))
    # El comando /censo y su handler se eliminan por ahora.
    dp.add_handler(CommandHandler("consulta", consultar_elector))

    # Iniciar el bot
    updater.start_polling()
    updater.idle()  # Mantener el bot en ejecución hasta que se presione Ctrl+C


if __name__ == '__main__':
    main()
