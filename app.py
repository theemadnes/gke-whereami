import requests
from flask import Flask, request, Response, jsonify
import logging
import json
import sys
import socket
import os
from datetime import datetime
import emoji
import random
from flask_cors import CORS

METADATA_URL = 'http://metadata.google.internal/computeMetadata/v1/'
METADATA_HEADERS = {'Metadata-Flavor': 'Google'}

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # otherwise our emojis get hosed
CORS(app)  # enable CORS

# set up emoji list
emoji_list = list(emoji.unicode_codes.UNICODE_EMOJI.keys())


@app.route('/healthz')  # healthcheck endpoint
def i_am_healthy():
    return ('OK')


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def home(path):

    # define the response payload
    payload = {}

    # get GCP project ID
    try:
        r = requests.get(METADATA_URL +
                         'project/project-id',
                         headers=METADATA_HEADERS)
        if r.ok:
            payload['project_id'] = r.text
    except:

        logging.warning("Unable to capture project ID.")

    # get GCP zone
    try:
        r = requests.get(METADATA_URL +
                         'instance/zone',
                         headers=METADATA_HEADERS)
        if r.ok:
            payload['zone'] = str(r.text.split("/")[3])
    except:

        logging.warning("Unable to capture zone.")

    # get GKE node name
    try:
        r = requests.get(METADATA_URL +
                         'instance/hostname',
                         headers=METADATA_HEADERS)
        if r.ok:
            payload['node_name'] = str(r.text)
    except:

        logging.warning("Unable to capture node name.")

    # get GKE cluster name
    try:
        r = requests.get(METADATA_URL +
                         'instance/attributes/cluster-name',
                         headers=METADATA_HEADERS)
        if r.ok:
            payload['cluster_name'] = str(r.text)
    except:

        logging.warning("Unable to capture GKE cluster name.")

    # get host header
    try:
        payload['host_header'] = request.headers.get('host')
    except:
        logging.warning("Unable to capture host header.")

    # get pod name, emoji & datetime
    payload['pod_name'] = socket.gethostname()
    payload['pod_name_emoji'] = emoji_list[hash(socket.gethostname()) %
                                           len(emoji_list)]
    payload['timestamp'] = datetime.now().replace(microsecond=0).isoformat()

    # get namespace, pod ip, and pod service account via downstream API
    if os.getenv('POD_NAMESPACE'):
        payload['pod_namespace'] = os.getenv('POD_NAMESPACE')
    else:
        logging.warning("Unable to capture pod namespace.")

    if os.getenv('POD_IP'):
        payload['pod_ip'] = os.getenv('POD_IP')
    else:
        logging.warning("Unable to capture pod IP address.")

    if os.getenv('POD_SERVICE_ACCOUNT'):
        payload['pod_service_account'] = os.getenv('POD_SERVICE_ACCOUNT')
    else:
        logging.warning("Unable to capture pod KSA.")

    # get the whereami METADATA envvar
    metadata = os.getenv('METADATA')
    if os.getenv('METADATA'):
        payload['metadata'] = os.getenv('METADATA')
    else:
        logging.warning("Unable to capture metadata.")

    # should we call a backend service?
    call_backend = os.getenv('BACKEND_ENABLED')

    if call_backend == 'True':

        backend_service = os.getenv('BACKEND_SERVICE')

        try:
            r = requests.get('http://' + backend_service)
            if r.ok:
                backend_result = r.json()
            else:
                backend_result = None
        except:

            print(sys.exc_info()[0])
            backend_result = None

        payload['backend_result'] = backend_result

    echo_headers = os.getenv('ECHO_HEADERS')

    if echo_headers == 'True':

        try: 

            payload['headers'] = {k:v for k, v in request.headers.items()}

        except:

            logging.warning("Unable to capture inbound headers.")

    return jsonify(payload)


if __name__ == '__main__':
    out_hdlr = logging.StreamHandler(sys.stdout)
    fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    out_hdlr.setFormatter(fmt)
    out_hdlr.setLevel(logging.INFO)
    logging.getLogger().addHandler(out_hdlr)
    logging.getLogger().setLevel(logging.INFO)
    app.logger.handlers = []
    app.logger.propagate = True
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
