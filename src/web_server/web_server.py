from datetime import datetime
from pysimplesoap.server import SoapDispatcher
from wsgiref.simple_server import make_server

dispatcher = SoapDispatcher(
    name="FechaHoraService",
    location="http://127.0.0.1:8000/",
    action="http://127.0.0.1:8000/",
    namespace="http://example.org/fecha_hora",
    prefix="tns",
    trace=True,
    ns=True,
)

# El argumento dummy es un string vacío que no se utiliza en la función
# pero es necesario para cumplir con la firma del servicio SOAP. En caso
# contrario, no funcionaría desde el cliente.
def get_datetime(dummy):
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

dispatcher.register_function(
    'get_datetime',
    get_datetime,
    returns={'return': str},
    args={'dummy': str}
)

def application(environ, start_response):
    path = environ.get("PATH_INFO", "")
    qs   = environ.get("QUERY_STRING", "")

    if path == "/" and qs.lower() == "wsdl":
        wsdl_xml = dispatcher.wsdl()
        start_response("200 OK", [
            ("Content-Type", "application/wsdl+xml; charset=utf-8"),
            ("Content-Length", str(len(wsdl_xml)))
        ])
        return [wsdl_xml]

    if environ.get("REQUEST_METHOD", "") == "POST":
        length = int(environ.get('CONTENT_LENGTH', 0) or 0)
        raw    = environ['wsgi.input'].read(length)
        try:
            soap_request = raw.decode('utf-8')
        except UnicodeDecodeError:
            soap_request = raw.decode('latin-1', 'ignore')

        soap_action   = environ.get('HTTP_SOAPACTION', "")
        response_str  = dispatcher.dispatch(soap_request, soap_action)

        response_bytes = response_str if isinstance(response_str, bytes) else response_str.encode('utf-8')
        start_response("200 OK", [
            ("Content-Type", "text/xml; charset=utf-8"),
            ("Content-Length", str(len(response_bytes)))
        ])
        return [response_bytes]

    wsdl_xml = dispatcher.wsdl()
    start_response("200 OK", [
        ("Content-Type", "application/wsdl+xml; charset=utf-8"),
        ("Content-Length", str(len(wsdl_xml)))
    ])
    return [wsdl_xml]

if __name__ == '__main__':
    print("Servidor SOAP escuchando en http://127.0.0.1:8000/")
    print("WSDL disponible en http://127.0.0.1:8000/?wsdl")
    make_server('127.0.0.1', 8000, application).serve_forever()
