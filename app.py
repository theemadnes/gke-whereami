import requests
from flask import Flask, request, Response
import logging
import json
import sys
import socket
import os
from datetime import datetime
import emoji
import random

METADATA_URL = 'http://metadata.google.internal/computeMetadata/v1/'
METADATA_HEADERS = {'Metadata-Flavor': 'Google'}

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False # otherwise our emojis get hosed 

# set up emoji list
emoji_list = list(emoji.UNICODE_EMOJI)

@app.route('/')
def home():

    # get project ID
    try:
        r = requests.get(METADATA_URL + 'project/project-id', headers=METADATA_HEADERS)
        if r.ok:
            project_id = r.text
        else:
            project_id = None
    except:

        project_id = None

    # get zone 
    try:
        r = requests.get(METADATA_URL + 'instance/zone', headers=METADATA_HEADERS)
        if r.ok:
            zone = str(r.text.split("/")[3])
        else:
            zone = None
    except:

        zone = None 

    # get gke node_name 
    try:
        r = requests.get(METADATA_URL + 'instance/hostname', headers=METADATA_HEADERS)
        if r.ok:
            node_name = str(r.text)
        else:
            node_name = None
    except:

        node_name = None

    # get cluster 
    try:
        r = requests.get(METADATA_URL + 'instance/attributes/cluster-name', headers=METADATA_HEADERS)
        if r.ok:
            cluster_name = str(r.text)
        else:
            cluster_name = None
    except:

        cluster_name = None

    # get pod name
    pod_name = socket.gethostname()

    # get datetime
    timestamp=datetime.now().replace(microsecond=0).isoformat()

    # get k8s namespace, pod ip, and pod service account 
    pod_namespace = os.getenv('POD_NAMESPACE')
    pod_ip = os.getenv('POD_IP')
    pod_service_account = os.getenv('POD_SERVICE_ACCOUNT')

    payload = {}
    payload['cluster_name'] = cluster_name
    payload['emoji'] = random.choice(emoji_list)[0]
    payload['node_name'] = node_name
    payload['pod_ip'] = pod_ip
    payload['pod_name'] = pod_name
    payload['pod_namespace'] = pod_namespace
    payload['pod_service_account'] = pod_service_account
    payload['project_id'] = project_id
    payload['timestamp'] = timestamp
    payload['zone'] = zone 

    return json.dumps(payload)

@app.route('/healthz')
def i_am_healthy():
    return ('OK')


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


