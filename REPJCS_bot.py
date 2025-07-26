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


async def _post_elector_voted(elector_data_to_post: dict) -> dict:
    """
    Intenta enviar una petición POST a la API para marcar al elector como votado.
    Recibe el diccionario completo de datos del elector para enviar.
    Devuelve un diccionario con 'success' (bool) y 'message' (str).
    """
    if not API_MARCAR_VOTADO_URL:
        return {'success': False, 'message': 'API_MARCAR_VOTADO_URL no configurada. No se pudo registrar el voto.'}

    try:
        response = requests.post(
            API_MARCAR_VOTADO_URL, json=elector_data_to_post)
        # Esto lanzará una excepción requests.exceptions.HTTPError para códigos de estado 4xx/5xx
        response.raise_for_status()

        # Si llegamos aquí, el código de estado HTTP fue 2xx (éxito).
        return {'success': True, 'message': 'Voto registrado exitosamente.'}

    except requests.exceptions.HTTPError as http_err:
        # --- INICIO DE LA SECCIÓN MODIFICADA PARA MANEJO DE ERRORES HTTP ---
        # Por defecto, usamos el texto de la respuesta como mensaje de error
        error_response_msg = str(http_err.response.text)

        try:
            # Intentar parsear el JSON de la respuesta de error
            error_details = http_err.response.json()
            if isinstance(error_details, dict):
                # Si es un diccionario y tiene un campo 'message', lo usamos
                error_response_msg = error_details.get(
                    'message', error_response_msg)
            elif isinstance(error_details, list) and error_details:
                # Si es una lista, y no sabemos la estructura exacta, podemos tomar el primer elemento
                # o representarla como string. Aquí, tomamos una representación simple.
                error_response_msg = f"API respondió con un error de lista: {error_details}"
            # Si es un diccionario sin 'message', o cualquier otro JSON,
            # error_response_msg ya está en su valor por defecto (el texto original de la respuesta).
        except requests.exceptions.JSONDecodeError:
            # Si la respuesta no es JSON válido, error_response_msg ya contiene el texto crudo
            pass

        # Conflict (estándar para duplicados)
        if http_err.response.status_code == 409:
            return {'success': False, 'message': 'El elector ya había votado y está registrado (por la API de registro).'}
        elif http_err.response.status_code == 400:  # Bad Request
            return {'success': False, 'message': f'Error de petición al registrar voto: {error_response_msg}.'}
        else:
            # Para todos los demás errores HTTP (ej. 500 Internal Server Error, 401 Unauthorized, etc.)
            return {'success': False, 'message': f'Error HTTP {http_err.response.status_code} al registrar voto: {error_response_msg}.'}
        # --- FIN DE LA SECCIÓN MODIFICADA PARA MANEJO DE ERRORES HTTP ---

    except requests.exceptions.RequestException as req_err:
        return {'success': False, 'message': f'Error de conexión al registrar voto: {req_err}.'}
    except Exception as e:
        # Este bloque ahora solo debería capturar errores que no sean de red o HTTP.
        # El error 'list' object has no attribute 'get' debería ser manejado arriba.
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
        f"DEBUG: Enviando GET a API_VOTACION_URL: {API_VOTACION_URL}/{cedula_solo_numeros}")

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

            voto_status_from_consulta = str(data.get('voto', 'FALSE')).upper()

            nombre_completo = f"{primer_nombre} {segundo_nombre}".strip()
            apellido_completo = f"{primer_apellido} {segundo_apellido}".strip()

            mensaje_respuesta = (
                f"✅ **Datos del Elector:**\n"
                f"   👤 **Cédula:** {nacionalidad}{data.get('cedula', cedula_completa_con_prefijo)}\n"
                f"   **Nombre:** {nombre_completo if nombre_completo else 'N/A'}\n"
                f"   **Apellido:** {apellido_completo if apellido_completo else 'N/A'}\n"
                f"   🗳️ **Centro de Votación:** {cv}\n"
            )

            if voto_status_from_consulta == "TRUE":
                mensaje_respuesta += "\n\n✔️ **Estado de Voto:** El elector ya ha votado (según los datos del CNE)."
            else:
                elector_data_for_post = data.copy()  # Make a copy to modify
                elector_data_for_post['voto'] = "TRUE"

                print(
                    f"DEBUG: Intentando POST a API_MARCAR_VOTADO_URL: {API_MARCAR_VOTADO_URL}")
                print(f"DEBUG: Payload para POST: {elector_data_for_post}")

                # Pass the full dict
                voto_result = await _post_elector_voted(elector_data_for_post)
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
