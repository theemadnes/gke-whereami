from flask import Flask, request, Response, jsonify
import logging
import sys
import os
from flask_cors import CORS
import whereami_payload

from concurrent import futures
import multiprocessing

import grpc

from grpc_reflection.v1alpha import reflection
from grpc_health.v1 import health
from grpc_health.v1 import health_pb2
from grpc_health.v1 import health_pb2_grpc

import whereami_pb2
import whereami_pb2_grpc

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # otherwise our emojis get hosed
CORS(app)  # enable CORS

# define Whereami object
whereami_payload = whereami_payload.WhereamiPayload()


# create gRPC class
class WhereamigRPC(whereami_pb2_grpc.WhereamiServicer):

    def GetPayload(self, request, context):
        payload = whereami_payload.build_payload(None)
        return whereami_pb2.WhereamiReply(**payload)


# if selected will serve gRPC endpoint on port 9090
# see https://github.com/grpc/grpc/blob/master/examples/python/xds/server.py
# for reference on code below
def grpc_serve():
    # the +5 you see below re: max_workers is a hack to avoid thread starvation
    # working on a proper workaround
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=multiprocessing.cpu_count()+5))

    # Add the application servicer to the server.
    whereami_pb2_grpc.add_WhereamiServicer_to_server(WhereamigRPC(), server)

    # Create a health check servicer. We use the non-blocking implementation
    # to avoid thread starvation.
    health_servicer = health.HealthServicer(
        experimental_non_blocking=True,
        experimental_thread_pool=futures.ThreadPoolExecutor(max_workers=1))
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)

    # Create a tuple of all of the services we want to export via reflection.
    services = tuple(
        service.full_name
        for service in whereami_pb2.DESCRIPTOR.services_by_name.values()) + (
            reflection.SERVICE_NAME, health.SERVICE_NAME)

    # Add the reflection service to the server.
    reflection.enable_server_reflection(services, server)
    server.add_insecure_port('[::]:9090')
    server.start()

    # Mark all services as healthy.
    overall_server_health = ""
    for service in services + (overall_server_health,):
        health_servicer.set(service, health_pb2.HealthCheckResponse.SERVING)

    # Park the main application thread.
    server.wait_for_termination()


# HTTP heathcheck
@app.route('/healthz')  # healthcheck endpoint
def i_am_healthy():
    return ('OK')


# default HTTP service
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def home(path):

    payload = whereami_payload.build_payload(request.headers)

    # split the path to see if user wants to read a specific field
    requested_value = path.split('/')[-1]
    if requested_value in payload.keys():

        return payload[requested_value]

    return jsonify(payload)

if __name__ == '__main__':
    out_hdlr = logging.StreamHandler(sys.stdout)
    fmt = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    out_hdlr.setFormatter(fmt)
    out_hdlr.setLevel(logging.INFO)
    logging.getLogger().addHandler(out_hdlr)
    logging.getLogger().setLevel(logging.INFO)
    app.logger.handlers = []
    app.logger.propagate = True
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

    # decision point - HTTP or gRPC?
    if os.getenv('GRPC_ENABLED') == "True":
        logging.info("gRPC server listening on port 9090")
        grpc_serve()

    else:
        app.run(
            host='0.0.0.0', port=int(os.environ.get('PORT', 8080)),
            threaded=True)
