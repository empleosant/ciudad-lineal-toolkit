"""
Cuánto se espera a una llamada que no vuelve. Python puro, sin Streamlit.

    con_plazo(hacer, segundos, respaldo=, al_respaldar=)

Es lo único que decide cuánto espera la persona cuando una petición al modelo
se queda colgada, así que va aparte de `comun/ia.py`: aquí no hay Streamlit y
`pruebas/estres.py` lo puede probar con funciones de mentira, sin gastar cuota.

Los plazos de fábrica están calibrados contra el codificador SISPE, que hace
llamadas cortas. Las herramientas que redactan (informes, formación) tardan
mucho más y no pasan por aquí: piden su respuesta sin plazo.
"""

import threading
import time

PLAZO_INTENTO = 6    # segundos de reloj para UN intento contra el modelo.
                     #
                     # No lo corta el plazo del cliente HTTP: ese mide el
                     # tiempo SIN RECIBIR DATOS, no lo que dura la respuesta, y
                     # una llamada que tarda veinte segundos no lo dispara
                     # jamás mientras mantenga viva la conexión. El corte de
                     # verdad es este, con reloj propio.
                     #
                     # Seis porque dentro caben DOS peticiones: la primera y su
                     # respaldo, que sale a los 2,5 s y tiene 3,5 para volver,
                     # de sobra para el 1,0-1,4 s de una respuesta sana.

PLAZO_RESPALDO = 2.5  # segundos sin respuesta antes de lanzar una SEGUNDA
                      # petición igual, sin tirar la primera; se queda la que
                      # vuelva antes.
                      #
                      # A 2,5 s casi ninguna respuesta sana ha disparado el
                      # respaldo todavía, y la que se ha quedado colgada lleva
                      # ya el doble de lo normal sin volver. Bajarlo dispara
                      # respaldos a respuestas que iban a llegar y gasta cupo;
                      # subirlo es volver a esperar por una petición muerta.

ESPERA_TOTAL = 30    # segundos para la consulta ENTERA, relevos incluidos. Es
                     # un tope distinto del de arriba y no se puede unificar:
                     # con un solo número, el tiempo gastado en el intento que
                     # se atascó contaba contra el intento bueno y mataba una
                     # respuesta que ya venía en camino.


def con_plazo(hacer, segundos, respaldo=None, al_respaldar=None):
    """Ejecuta `hacer()` y se rinde a los `segundos`, conteste o no. Si a los
    `respaldo` segundos no ha contestado, lanza un SEGUNDO `hacer()` igual, sin
    tirar el primero, y se queda con el que vuelva antes.

    EL RESPALDO. Cuando el modelo contesta, contesta en 1,0-1,4 s. Pero una de
    cada cinco peticiones no vuelve: no es que tarde, es que se queda colgada
    en algún servidor, y el reintento que va detrás vuelve en el segundo de
    siempre. Esperar el plazo entero para descubrirlo cuesta el plazo más el
    relevo; con dos modelos colgados seguidos, diez segundos largos de espera.

    El respaldo es ese reintento lanzado ANTES de rendirse. La primera no se
    cancela porque no se puede; si vuelve antes que el respaldo, se usa ella.

    Un error que llega ANTES del respaldo -un 429, un 400- se relanza al
    momento y no se lanza nada más: eso no es un atasco, es una respuesta, y
    reintentar sería gastar cupo en lo mismo. Si el primero falla DESPUÉS de
    salir el respaldo, se espera al respaldo; si falla el respaldo y el primero
    sigue vivo, se le sigue esperando hasta el plazo. Solo cuando no queda
    ninguno vivo se relanza el último error, con su tipo intacto: de eso
    dependen `ia.sin_cuota` y `ia.por_minuto` para decidir si se espera, se
    releva o se aparta al proveedor.

    `al_respaldar(segundos)` se llama en el hilo PRINCIPAL en el momento de
    lanzar el respaldo, para poder dejarlo anotado: es lo que hace visible
    cuántas veces hace falta y lo que cuesta.

    Un hilo es la única forma de rendirse: una llamada HTTP bloqueada no se
    puede cancelar desde fuera. El hilo abandonado termina por su cuenta y su
    respuesta se tira; va como demonio para que no retenga al servidor.

    Dentro del hilo NO se toca nada de Streamlit: aquí solo se hace la llamada.
    `al_respaldar` corre fuera, en el principal.
    """
    listo = threading.Condition()
    llegadas = []   # ("valor", x) o ("error", e), por orden de llegada

    def envuelve():
        try:
            resultado = ("valor", hacer())
        except BaseException as e:  # noqa: BLE001
            # Se guarda y se relanza fuera, para que llegue al mismo `except`
            # de siempre con su tipo intacto.
            resultado = ("error", e)
        with listo:
            llegadas.append(resultado)
            listo.notify_all()

    def lanza():
        threading.Thread(target=envuelve, daemon=True).start()

    arranque = time.perf_counter()
    lanza()
    vivos = 1
    respaldado = respaldo is None   # sin respaldo pedido, no hay nada que lanzar
    ultimo = None
    while True:
        pasado = time.perf_counter() - arranque
        if pasado >= segundos:
            # Ni «quota» ni «429» en el texto: `sin_cuota` mira la cadena y
            # esto no es un problema de cupo, es una llamada que no vuelve.
            raise TimeoutError(f"Sin respuesta del modelo en {segundos} s.")
        # Se duerme hasta el siguiente hito: el respaldo, si aún no ha salido,
        # o el plazo. Cualquier llegada despierta antes.
        hito = segundos if respaldado else min(respaldo, segundos)
        with listo:
            if not llegadas:
                listo.wait(max(hito - pasado, 0))
            recibidas, llegadas[:] = list(llegadas), []
        for tipo, x in recibidas:
            if tipo == "valor":
                return x
            ultimo = x
            vivos -= 1
        if vivos == 0:
            raise ultimo
        if not respaldado and time.perf_counter() - arranque >= respaldo:
            respaldado = True
            lanza()
            vivos += 1
            if al_respaldar:
                al_respaldar(time.perf_counter() - arranque)
