import os
import telegram
# Importa las clases de la nueva forma para Application
from telegram.ext import Application, CommandHandler, MessageHandler
from telegram.ext import filters  # Sigue siendo correcto
import requests

# --- CONFIGURACIÓN ---
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    raise ValueError(
        "TELEGRAM_BOT_TOKEN no está configurada como variable de entorno.")

API_VOTACION_URL = os.environ.get('API_VOTACION_URL')
if not API_VOTACION_URL:
    raise ValueError(
        "API_VOTACION_URL no está configurada como variable de entorno.")

# --- FUNCIONES DEL BOT ---


async def start(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja el comando /start."""
    await update.message.reply_text(
        '¡Hola! Soy Progreso, tu bot de consulta de cédulas.\n\n'
        'Actualmente, solo puedo consultar el centro de votación.\n'
        '➡️ `/consulta [número de cédula]`: Consulta tu centro de votación.\n\n'
        '**Ejemplo:** `/consulta V12345678`',
        parse_mode=telegram.ParseMode.MARKDOWN
    )


async def consultar_elector(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja el comando /consulta para obtener datos electorales."""
    # En la nueva API, context.args ya no es una tupla, es una lista.
    args = context.args
    if not args:
        await update.message.reply_text(
            'Por favor, ingresa el número de cédula después del comando. Ejemplo: `/consulta V12345678`',
            parse_mode=telegram.ParseMode.MARKDOWN
        )
        return

    cedula_input = args[0].strip().upper()

    if not (len(cedula_input) > 1 and cedula_input[0] in ('V', 'E', 'P') and cedula_input[1:].isdigit()):
        await update.message.reply_text(
            'Formato de cédula incorrecto. Debe empezar con V, E o P seguido de números. Ejemplo: V12345678')
        return

    await update.message.reply_text(f'Consultando tu API para la cédula {cedula_input}...')

    try:
        params = {'cedula': cedula_input}
        response = requests.get(API_VOTACION_URL, params=params)
        response.raise_for_status()

        data = response.json()

        mensaje_respuesta = ""
        if data and data.get('cedula'):
            nacionalidad = data.get('nacionalidad', 'N/A')
            # ¡Revisa estas claves con tu API!
            primer_nombre = data.get('pnombre', 'N/A')
            segundo_nombre = data.get('snombre', 'N/A')
            primer_apellido = data.get('papellido', 'N/A')
            segundo_apellido = data.get('sapellido', 'N/A')
            centro_votacion = data.get('cv', 'No especificado')

            nombre_completo = f"{primer_nombre} {segundo_nombre}".strip()
            apellido_completo = f"{primer_apellido} {segundo_apellido}".strip()

            mensaje_respuesta = (
                f"✅ **Datos del Elector:**\n"
                f"   👤 **Cédula:** {nacionalidad}{data.get('cedula', 'N/A')}\n"
                f"   **Nombre:** {nombre_completo if nombre_completo else 'N/A'}\n"
                f"   **Apellido:** {apellido_completo if apellido_completo else 'N/A'}\n"
                f"   🗳️ **Centro de Votación:** {centro_votacion}\n"
            )
        else:
            mensaje_respuesta = (
                f"❌ No se encontró información electoral para la cédula {cedula_input}. "
                f"Por favor, verifica el número."
            )

        await update.message.reply_text(mensaje_respuesta, parse_mode=telegram.ParseMode.MARKDOWN)

    except requests.exceptions.RequestException as e:
        await update.message.reply_text(
            f'❌ Error al conectar con tu API: {e}. Por favor, verifica la URL de la API o inténtalo más tarde.')
    except ValueError:
        await update.message.reply_text(
            '❌ Error al procesar la respuesta de tu API. El formato de la respuesta no es válido.')
    except Exception as e:
        await update.message.reply_text(f'❌ Ocurrió un error inesperado: {e}.')


def main() -> None:
    """Función principal para iniciar el bot."""
    # Crea la instancia de la aplicación
    application = Application.builder().token(TOKEN).build()

    # Añadir manejadores de comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("consulta", consultar_elector))

    # Iniciar el bot (polling)
    application.run_polling(allowed_updates=telegram.Update.ALL_TYPES)


if __name__ == '__main__':
    main()
