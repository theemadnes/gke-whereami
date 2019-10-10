import requests
from flask import Flask, request, Response
import logging
import json
import sys
import socket
from datetime import datetime

METADATA_URL = 'http://metadata.google.internal/computeMetadata/v1/'
METADATA_HEADERS = {'Metadata-Flavor': 'Google'}

app = Flask(__name__)

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

    payload = {}
    payload['project_id'] = project_id
    payload['pod_name'] = pod_name
    payload['timestamp'] = timestamp
    payload['node_name'] = node_name
    payload['zone'] = zone
    payload['cluster_name'] = cluster_name

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
    app.run(host='0.0.0.0', port=5000)


