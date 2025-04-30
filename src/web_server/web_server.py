# server.py
from datetime import datetime
from pysimplesoap.server import SoapDispatcher
from wsgiref.simple_server import make_server

# 1) Creamos el despachador SOAP
dispatcher = SoapDispatcher(
    name="FechaHoraService",
    location="http://127.0.0.1:8000/",
    action="http://127.0.0.1:8000/",
    namespace="http://example.org/fecha_hora",
    prefix="tns",
    trace=True,
    ns=True,
)

# 2) Definimos la operación que devuelve la fecha y hora formateada
def get_datetime():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

# 3) Registramos la operación como que retorna un string
dispatcher.register_function(
    'get_datetime',
    get_datetime,
    returns={'return': str}
)

# 4) Aplicación WSGI principal: sirve el WSDL en GET /?wsdl y procesa POSTs SOAP
def application(environ, start_response):
    path = environ.get("PATH_INFO", "")
    qs   = environ.get("QUERY_STRING", "")

    # Si piden el WSDL explícitamente
    if path == "/" and qs.lower() == "wsdl":
        wsdl_xml = dispatcher.wsdl()
        start_response("200 OK", [
            ("Content-Type", "application/wsdl+xml; charset=utf-8"),
            ("Content-Length", str(len(wsdl_xml)))
        ])
        return [wsdl_xml]

    # Si reciben una invocación SOAP via POST
    if environ.get("REQUEST_METHOD", "") == "POST":
        length = int(environ.get('CONTENT_LENGTH', 0) or 0)
        raw    = environ['wsgi.input'].read(length)  # bytes
        # Decodificamos a str para que PySimpleSOAP pueda hacer sus regex/xml
        try:
            soap_request = raw.decode('utf-8')
        except UnicodeDecodeError:
            soap_request = raw.decode('latin-1', 'ignore')

        # Procesamos la llamada
        soap_action   = environ.get('HTTP_SOAPACTION', "")
        response_str  = dispatcher.dispatch(soap_request, soap_action)

        # Devolvemos siempre bytes
        response_bytes = response_str.encode('utf-8')
        start_response("200 OK", [
            ("Content-Type", "text/xml; charset=utf-8"),
            ("Content-Length", str(len(response_bytes)))
        ])
        return [response_bytes]

    # Cualquier otra cosa, devolvemos el WSDL igualmente
    wsdl_xml = dispatcher.wsdl()
    start_response("200 OK", [
        ("Content-Type", "application/wsdl+xml; charset=utf-8"),
        ("Content-Length", str(len(wsdl_xml)))
    ])
    return [wsdl_xml.encode("utf-8")]

if __name__ == '__main__':
    print("Servidor SOAP escuchando en http://127.0.0.1:8000/")
    print("WSDL disponible en http://127.0.0.1:8000/?wsdl")
    make_server('127.0.0.1', 8000, application).serve_forever()
