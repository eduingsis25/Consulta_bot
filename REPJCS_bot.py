import os
import telegram
from telegram.ext import Application, CommandHandler, MessageHandler
from telegram.ext import filters
from telegram import constants
import requests

# --- CONFIGURACIÓN ---
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    raise ValueError(
        "TELEGRAM_BOT_TOKEN no está configurada como variable de entorno.")

# Ahora será 'https://consultaelecciones.onrender.com/api/elector'
API_VOTACION_URL = os.environ.get('API_VOTACION_URL')
if not API_VOTACION_URL:
    raise ValueError(
        "API_VOTACION_URL no está configurada como variable de entorno.")

# --- Funciones del bot (sin cambios en start) ---


async def start(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja el comando /start."""
    await update.message.reply_text(
        '¡Hola! Soy Progreso, tu bot de consulta de cédulas.\n\n'
        'Actualmente, solo puedo consultar el centro de votación.\n'
        '➡️ `/consulta [número de cédula]`: Consulta tu centro de votación.\n\n'
        '**Ejemplo:** `/consulta V12345678`',
        parse_mode=constants.ParseMode.MARKDOWN
    )


async def consultar_elector(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja el comando /consulta para obtener datos electorales."""
    args = context.args
    if not args:
        await update.message.reply_text(
            'Por favor, ingresa el número de cédula después del comando. Ejemplo: `/consulta V12345678`',
            parse_mode=constants.ParseMode.MARKDOWN
        )
        return

    cedula_completa_con_prefijo = args[0].strip().upper()

    if (len(cedula_completa_con_prefijo) > 1 and
            cedula_completa_con_prefijo[0] in ('V', 'E', 'P') and
            cedula_completa_con_prefijo[1:].isdigit()):
        cedula_solo_numeros = cedula_completa_con_prefijo[1:]
    else:
        await update.message.reply_text(
            'Formato de cédula incorrecto. Debe empezar con V, E o P seguido de números. Ejemplo: V12345678')
        return

    await update.message.reply_text(f'Consultando tu API para la cédula {cedula_completa_con_prefijo}...')

    try:
        # ¡¡¡CAMBIO CRÍTICO AQUÍ!!!
        # Construimos la URL completa concatenando la base y la cédula
        api_url_completa = f"{API_VOTACION_URL}/{cedula_solo_numeros}"
        response = requests.get(api_url_completa)
        # Ya no necesitamos 'params=params' porque la cédula ya está en la URL
        response.raise_for_status()

        data = response.json()

        mensaje_respuesta = ""
        if data and data.get('cedula'):
            nacionalidad = data.get('nacionalidad', 'N/A')
            primer_nombre = data.get('pnombre', 'N/A')
            segundo_nombre = data.get('snombre', 'N/A')
            primer_apellido = data.get('papellido', 'N/A')
            segundo_apellido = data.get('sapellido', 'N/A')
            cv = data.get('cv', 'No especificado')

            nombre_completo = f"{primer_nombre} {segundo_nombre}".strip()
            apellido_completo = f"{primer_apellido} {segundo_apellido}".strip()

            mensaje_respuesta = (
                f"✅ **Datos del Elector:**\n"
                f"   👤 **Cédula:** {nacionalidad}{data.get('cedula', 'N/A')}\n"
                f"   **Nombre:** {nombre_completo if nombre_completo else 'N/A'}\n"
                f"   **Apellido:** {apellido_completo if apellido_completo else 'N/A'}\n"
                f"   🗳️ **Centro de Votación:** {cv}\n"
            )
        else:
            mensaje_respuesta = (
                f"❌ No se encontró información electoral para la cédula {cedula_completa_con_prefijo}. "
                f"Por favor, verifica el número."
            )

        await update.message.reply_text(mensaje_respuesta, parse_mode=constants.ParseMode.MARKDOWN)

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
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("consulta", consultar_elector))
    application.run_polling(allowed_updates=telegram.Update.ALL_TYPES)


if __name__ == '__main__':
    main()
