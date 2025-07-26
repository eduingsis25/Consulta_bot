import os
import telegram
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import constants
import requests
import re  # Necesario para expresiones regulares

# --- CONFIGURACIÓN ---
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    raise ValueError(
        "TELEGRAM_BOT_TOKEN no está configurada como variable de entorno.")

API_VOTACION_URL = os.environ.get('API_VOTACION_URL')
if not API_VOTACION_URL:
    raise ValueError(
        "API_VOTACION_URL no está configurada como variable de entorno.")

API_MARCAR_VOTADO_URL = os.environ.get('API_MARCAR_VOTADO_URL')
if not API_MARCAR_VOTADO_URL:
    print("ADVERTENCIA: API_MARCAR_VOTADO_URL no configurada. La funcionalidad de marcar votado no estará activa.")

# NUEVA VARIABLE DE ENTORNO PARA EL TOKEN DE AUTENTICACIÓN
API_MARCAR_VOTADO_AUTH_TOKEN = os.environ.get('API_MARCAR_VOTADO_AUTH_TOKEN')
if not API_MARCAR_VOTADO_AUTH_TOKEN:
    print("ADVERTENCIA: API_MARCAR_VOTADO_AUTH_TOKEN no configurada. Las peticiones a la API de marcado de votado podrían fallar por autenticación (Error 401).")


# Expresión regular para validar cédulas (V, E, P, G, J + 1 a 9 dígitos, O solo 7 a 9 dígitos)
CEDULA_REGEX = r"^(?:[VEPGJ])?\d{7,9}$"

# --- FUNCIONES DEL BOT ---


async def start(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja el comando /start."""
    await update.message.reply_text(
        '¡Hola! Soy Progreso, tu bot de consulta de cédulas.\n\n'
        'Puedes enviarme directamente el número de cédula (ej. `V12345678` o `12345678`) '
        'o usar el comando `/consulta [número de cédula]`.\n\n'
        '**Ejemplo:** `V12345678` o `/consulta 12345678`',
        parse_mode=constants.ParseMode.MARKDOWN
    )


async def _post_elector_voted(cedula_solo_numeros: str) -> dict:
    """
    Intenta enviar una petición POST a la API para marcar al elector como votado.
    Devuelve un diccionario con 'success' (bool) y 'message' (str).
    """
    if not API_MARCAR_VOTADO_URL:
        return {'success': False, 'message': 'API_MARCAR_VOTADO_URL no configurada. No se pudo registrar el voto.'}

    # PREPARAR ENCABEZADOS DE AUTENTICACIÓN
    headers = {}
    if API_MARCAR_VOTADO_AUTH_TOKEN:
        # Asumimos que es un Token "Token". Si tu API usa otro formato (ej. una clave X-API-Key),
        # DEBES AJUSTAR esta línea. Por ejemplo: headers['X-API-Key'] = API_MARCAR_VOTADO_AUTH_TOKEN
        headers['Authorization'] = f'Token {API_MARCAR_VOTADO_AUTH_TOKEN}'

    try:
        data_to_send = {'cedula': cedula_solo_numeros}

        # Enviamos la petición POST incluyendo los headers
        response = requests.post(
            API_MARCAR_VOTADO_URL, json=data_to_send, headers=headers)
        response.raise_for_status()

        return {'success': True, 'message': 'Voto registrado exitosamente.'}

    except requests.exceptions.HTTPError as http_err:
        if http_err.response.status_code == 401:
            # Mensaje específico para el error 401
            return {'success': False, 'message': 'Error de autenticación (401). Verifica que el token/clave API sea correcto y esté configurado en Railway.'}
        elif http_err.response.status_code == 409:
            return {'success': False, 'message': 'El elector ya había votado y está registrado.'}
        elif http_err.response.status_code == 400:
            try:
                error_details = http_err.response.json()
                msg = error_details.get('message', str(http_err.response.text))
            except requests.exceptions.JSONDecodeError:
                msg = str(http_err.response.text)
            return {'success': False, 'message': f'Error de petición al registrar voto: {msg}.'}
        return {'success': False, 'message': f'Error HTTP {http_err.response.status_code} al registrar voto: {http_err.response.text}.'}
    except requests.exceptions.RequestException as req_err:
        return {'success': False, 'message': f'Error de conexión al registrar voto: {req_err}.'}
    except Exception as e:
        return {'success': False, 'message': f'Error inesperado al registrar voto: {e}.'}


async def _process_elector_request(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE, cedula_input_raw: str) -> None:
    """
    Función interna para procesar la petición de cédula, validar, consultar API
    y marcar como votado.
    """
    cedula_completa_con_prefijo = cedula_input_raw.strip().upper()

    match = re.match(CEDULA_REGEX, cedula_completa_con_prefijo)

    if not match:
        await update.message.reply_text(
            'Formato de cédula incorrecto. Debe empezar con V, E, P, G o J seguido de 7 a 9 números, '
            'o solo los números (7 a 9 dígitos). Ejemplo: `V12345678` o `12345678`',
            parse_mode=constants.ParseMode.MARKDOWN
        )
        return

    if cedula_completa_con_prefijo and cedula_completa_con_prefijo[0] in ('V', 'E', 'P', 'G', 'J'):
        cedula_solo_numeros = cedula_completa_con_prefijo[1:]
    else:
        cedula_solo_numeros = cedula_completa_con_prefijo

    print(
        f"DEBUG: Enviando a API_VOTACION_URL: {API_VOTACION_URL}/{cedula_solo_numeros}")
    print(
        f"DEBUG: Enviando a API_MARCAR_VOTADO_URL (POST): {API_MARCAR_VOTADO_URL} con cedula: {cedula_solo_numeros}")

    await update.message.reply_text(f'Consultando tu API para la cédula {cedula_completa_con_prefijo}...')

    try:
        api_url_completa = f"{API_VOTACION_URL}/{cedula_solo_numeros}"
        response = requests.get(api_url_completa)
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
                f"   👤 **Cédula:** {nacionalidad}{data.get('cedula', cedula_completa_con_prefijo)}\n"
                f"   **Nombre:** {nombre_completo if nombre_completo else 'N/A'}\n"
                f"   **Apellido:** {apellido_completo if apellido_completo else 'N/A'}\n"
                f"   🗳️ **Centro de Votación:** {cv}\n"
            )

            # --- INTENTAR MARCAR COMO VOTADO ---
            voto_result = await _post_elector_voted(cedula_solo_numeros)
            if voto_result['success']:
                mensaje_respuesta += "\n\n✔️ Voto registrado exitosamente."
            else:
                mensaje_respuesta += f"\n\n⚠️ No se pudo registrar el voto: {voto_result['message']}"

        else:
            mensaje_respuesta = (
                f"❌ No se encontró información electoral para la cédula {cedula_completa_con_prefijo}. "
                f"Por favor, verifica el número."
            )

        await update.message.reply_text(mensaje_respuesta, parse_mode=constants.ParseMode.MARKDOWN)

    except requests.exceptions.HTTPError as http_err:
        if http_err.response.status_code == 404:
            await update.message.reply_text(f'❌ No se encontró información en la API para la cédula {cedula_completa_con_prefijo}.')
        else:
            await update.message.reply_text(
                f'❌ Error HTTP {http_err.response.status_code} al consultar tu API: {http_err.response.text}. '
                f'Por favor, verifica la URL de la API o inténtalo más tarde.')
    except requests.exceptions.ConnectionError as conn_err:
        await update.message.reply_text(
            f'❌ Error de conexión al intentar comunicarse con tu API: {conn_err}. '
            'Asegúrate de que la URL de la API es accesible y correcta.')
    except ValueError:
        await update.message.reply_text(
            '❌ Error al procesar la respuesta de tu API. El formato de la respuesta no es válido.')
    except Exception as e:
        await update.message.reply_text(f'❌ Ocurrió un error inesperado: {e}.')


async def handle_consulta_command(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja el comando /consulta."""
    if not context.args:
        await update.message.reply_text(
            'Por favor, ingresa el número de cédula después del comando. Ejemplo: `/consulta V12345678` o `/consulta 12345678`',
            parse_mode=constants.ParseMode.MARKDOWN
        )
        return
    cedula_input_raw = context.args[0]
    await _process_elector_request(update, context, cedula_input_raw)


async def handle_text_message(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja mensajes de texto que podrían ser cédulas."""
    text = update.message.text
    if re.match(CEDULA_REGEX, text.strip().upper()):
        await _process_elector_request(update, context, text)
    else:
        pass


def main() -> None:
    """Función principal para iniciar el bot."""
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler(
        "consulta", handle_consulta_command))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, handle_text_message))

    application.run_polling(allowed_updates=telegram.Update.ALL_TYPES)


if __name__ == '__main__':
    main()
