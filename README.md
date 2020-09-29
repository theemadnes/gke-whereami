# whereami

`whereami` is a simple Kubernetes-oriented python app for describing the location of the pod serving a request via its attributes (cluster name, cluster region, pod name, namespace, service account, etc). This is useful for a variety of demos where you just need to understand how traffic is getting to and returning from your app.

### Simple deployment 

`whereami` is a single-container app, designed and packaged to run on Kubernetes. In it's simplest form it can be deployed in a single line with only a few parameters.

```bash
$ kubectl run --image=gcr.io/google-samples/whereami:v1.0.1 --expose --port 8080 whereami
```

The `whereami`  pod listens on port `8080` and returns a very simple JSON response that indicates who is responding and where they live.

```bash
$ curl 10.12.0.4:8080
{"cluster_name":"gke-us-east","host_header":"10.12.0.4:8080","node_name":"gke-gke-us-east-default-pool-96ad63bd-5bhj.c.church-243723.internal","pod_name":"whereami-8559dc65f9-cckpc","pod_name_emoji":"👸🏽","project_id":"church-243723","timestamp":"2020-08-02T22:24:04","zone":"us-east4-a"}
```

Some of the returned metadata includes:

- `pod_name_emoji` - an emoji character hashed from Pod name. This makes it a little easier for a human to visually identify the pod you're dealing with.
- `zone` - the GCP zone in which the Pod is running
- `host_header` - the HTTP host header field, as seen by the Pod

### Full deployment walk through

`whereami` can return even more information about your application and its environment, if you provide access to that information. This walkthrough will demonstrate the deployment of a GKE cluster and the metadata `whereami` is capable of exposing. Clone this repo to have local access to the deployment files used in step 2.

```bash
$ git clone https://github.com/GoogleCloudPlatform/kubernetes-engine-samples
$ cd kubernetes-engine-samples/whereami
```

#### Step 1 - Create a GKE cluster 

First define your environment variables (substituting where #needed#):

```bash
$ export PROJECT_ID=#YOUR_PROJECT_ID#
$ export COMPUTE_REGION=#YOUR_COMPUTE_REGION# # this expects a region, not a zone
$ export CLUSTER_NAME=whereami
```

Now create your cluster:

```bash
$ gcloud beta container clusters create $CLUSTER_NAME \
  --enable-ip-alias \
  --enable-stackdriver-kubernetes \
  --region=$COMPUTE_REGION \
  --num-nodes=1 \
  --release-channel=regular

$ gcloud container clusters get-credentials $CLUSTER_NAME --region $COMPUTE_REGION
```

This will create a regional cluster with a single node per zone (3 nodes in total). 

#### Step 2 - Deploy whereami

This [Deployment manifest](k8s/deployment.yaml) shows the configurable parameters of `whereami` as environment variables passed from a configmap to the Pods. Each of the following environment variables are optional. If the environment variable is passed to the Pod then the application will enable that field in its response.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: whereami
spec:
  replicas: 3 #whereami can be deployed as multiple identical replicas
  selector:
    matchLabels:
      app: whereami
  template:
    metadata:
      labels:
        app: whereami
    spec:
      serviceAccountName: whereami-ksa
      containers:
      - name: whereami
        image: gcr.io/google-samples/whereami:v1.0.1
        ports:
          - name: http
            containerPort: 8080 #The application is listening on port 8080
        livenessProbe: #There is a health probe listening on port 8080/healthz that will respond with 200 if the application is running
          httpGet:
              path: /healthz
              port: 8080
              scheme: HTTP
          initialDelaySeconds: 5
          periodSeconds: 15
          timeoutSeconds: 5
        readinessProbe:
          httpGet:
            path: /healthz
            port: 8080
            scheme: HTTP
          initialDelaySeconds: 5
          timeoutSeconds: 1
        env:
          - name: POD_NAMESPACE #The kubernetes Namespace where the Pod is running
            valueFrom:
              fieldRef:
                fieldPath: metadata.namespace
          - name: POD_IP #The IP address of the pod
            valueFrom:
              fieldRef:
                fieldPath: status.podIP
          - name: POD_SERVICE_ACCOUNT #The name of the Service Account that the pod is using
            valueFrom:
              fieldRef:
                fieldPath: spec.serviceAccountName
          - name: BACKEND_ENABLED #If true, enables queries from whereami to a specified Service name or IP. Requires BACKEND_SERVICE to be set. 
            valueFrom:
              configMapKeyRef:
                name: whereami-configmap
                key: BACKEND_ENABLED
          - name: BACKEND_SERVICE #Configures the name or IP of the endpoint that whereami will query.
            valueFrom:
              configMapKeyRef:
                name: whereami-configmap
                key: BACKEND_SERVICE
          - name: METADATA #An arbitrary metadata field that can be used to label JSON responses
            valueFrom:
              configMapKeyRef:
                name: whereami-configmap
                key: METADATA
```

The k8s deployment repo uses Kustomize to organize its deployment files. The following command will deploy the all of the required resources for the full `whereami` deployment.

```bash
$ cat k8s/kustomization.yaml
resources:
- ksa.yaml
- deployment.yaml
- service.yaml
- configmap.yaml

$ kubectl apply -k k8s
serviceaccount/whereami-ksa created
configmap/whereami-configmap created
service/whereami created
deployment.apps/whereami created
```

#### Step 3 - Query whereami

Get the external Service endpoint. The `k8s` repo deploys an external `LoadBalancer Service` on port TCP/80 to make the application reachable on the internet.

```
ENDPOINT=$(kubectl get svc whereami | grep -v EXTERNAL-IP | awk '{ print $4}')
```

> Note: this may be `pending` for a few minutes while the service provisions

Wrap things up by `curl`ing the `EXTERNAL-IP` of the service. 

```bash
$ curl $ENDPOINT

{"cluster_name":"cluster-1","host_header":"34.72.90.134","metadata":"frontend","node_name":"gke-cluster-1-default-pool-c91b5644-v8kg.c.alexmattson-scratch.internal","pod_ip":"10.4.2.34","pod_name":"whereami-7b79956dd6-vmm9z","pod_name_emoji":"🧚🏼‍♀️","pod_namespace":"default","pod_service_account":"whereami-ksa","project_id":"alexmattson-scratch","timestamp":"2020-07-30T05:44:14","zone":"us-central1-c"}
```



### Setup a backend service call

`whereami` has an optional flag within its configmap that will cause it to call another backend service within your Kubernetes cluster (for example, a different, non-public instance of itself). This is helpful for demonstrating a public microservice call to a non-public microservice, and then including the responses of both microservices in the payload delivered back to the user.

#### Step 1 - Deploy the whereami backend

Deploy `whereami` again using the manifests from [k8s-backend-overlay-example](k8s-backend-overlay-example)

```bash
$ kubectl apply -k k8s-backend-overlay-example
serviceaccount/whereami-ksa-backend created
configmap/whereami-configmap-backend created
service/whereami-backend created
deployment.apps/whereami-backend created
```

`configmap/whereami-configmap-backend` has the following fields configured:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: whereami-configmap
data:
  BACKEND_ENABLED: "False" # assuming you don't want a chain of backend calls
  METADATA:        "backend"
```

It overlays the base manifest with the following Kustomization file:

```yaml
nameSuffix: "-backend"
commonLabels:
  app: whereami-backend
bases:
- ../k8s
patches:
- cm-flag.yaml
- service-type.yaml
```

#### Step 2 - Deploy the whereami frontend

Now we're going to deploy the `whereami` frontend from the `k8s-frontend-overlay-example` folder. The configmap in this folder shows how the frontend is configured differently from the backend:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: whereami-configmap
data:
  BACKEND_ENABLED: "True" #This enables requests to be send to the backend
  BACKEND_SERVICE: "whereami-backend" #This is the name of the backend Service that was created in the previous step
  METADATA:        "frontend" #This is the metadata string returned in the output
```

Deploy the frontend:

```bash
$ kubectl apply -k k8s-frontend-overlay-example
serviceaccount/whereami-ksa-frontend created
configmap/whereami-configmap-frontend created
service/whereami-frontend created
deployment.apps/whereami-frontend created
```

#### Step 3 - Query whereami

Get the external Service endpoint again:

```bash
$ ENDPOINT=$(kubectl get svc whereami-frontend | grep -v EXTERNAL-IP | awk '{ print $4}')
```

Curl the endpoint to get the response. In this example we use [jq]() to provide a little more structure to the response:

```bash
$ curl $ENDPOINT -s | jq .
{
  "backend_result": {
    "cluster_name": "gke-us-east",
    "host_header": "whereami-backend",
    "metadata": "backend",
    "node_name": "gke-gke-us-east-default-pool-96ad63bd-5bhj.c.church-243723.internal",
    "pod_ip": "10.12.0.9",
    "pod_name": "whereami-backend-769bdff967-6plr6",
    "pod_name_emoji": "🤦🏾‍♀️",
    "pod_namespace": "multi-cluster-demo",
    "pod_service_account": "whereami-ksa-backend",
    "project_id": "church-243723",
    "timestamp": "2020-08-02T23:38:56",
    "zone": "us-east4-a"
  },
  "cluster_name": "gke-us-east",
  "host_header": "35.245.36.194",
  "metadata": "frontend",
  "node_name": "gke-gke-us-east-default-pool-96ad63bd-5bhj.c.church-243723.internal",
  "pod_ip": "10.12.0.10",
  "pod_name": "whereami-frontend-5ddd6bc84c-nkrds",
  "pod_name_emoji": "🏃🏻‍♀️",
  "pod_namespace": "multi-cluster-demo",
  "pod_service_account": "whereami-ksa-frontend",
  "project_id": "church-243723",
  "timestamp": "2020-08-02T23:38:56",
  "zone": "us-east4-a"
}
```

This response shows the chain of communications with the response from the frontend and the response from the backend. A little bit of jq-magic can actually make it easy too see the chains of communications over successive requests:

```bash
$ for i in {1..3}; do curl $ENDPOINT -s | jq '{frontend: .pod_name, backend: .backend_result.pod_name}' -c; done
{"frontend":"🏃🏻‍♀️","backend":"5️⃣"}
{"frontend":"🤦🏾","backend":"🤦🏾‍♀️"}
{"frontend":"🏃🏻‍♀️","backend":"🏀"}
```

### Include all received headers in the response  

`whereami` has an additional feature flag that, when enabled, will include all received headers in its reply. If, in `k8s/configmap.yaml`, `ECHO_HEADERS` is set to `True`, the response payload will include a `headers` field, populated with the headers included in the client's request. 

#### Step 1 - Deploy whereami with header echoing enabled 

```bash
$ kubectl apply -k k8s-echo-headers-overlay-example
serviceaccount/whereami-ksa-frontend created
configmap/whereami-configmap-frontend created
service/whereami-frontend created
deployment.apps/whereami-frontend created
```

#### Step 2 - Query whereami

Get the external Service endpoint again:

```bash
$ ENDPOINT=$(kubectl get svc whereami-echo-headers | grep -v EXTERNAL-IP | awk '{ print $4}')
```

Curl the endpoint to get the response. Yet again, we use [jq]() to provide a little more structure to the response:

```bash
$ curl $ENDPOINT -s | jq .
{
  "cluster_name": "cluster-1",
  "headers": {
    "Accept": "*/*",
    "Host": "35.202.174.251",
    "User-Agent": "curl/7.64.1"
  },
  "host_header": "35.202.174.251",
  "metadata": "echo_headers_enabled",
  "node_name": "gke-cluster-1-default-pool-c91b5644-1z7l.c.alexmattson-scratch.internal",
  "pod_ip": "10.4.1.44",
  "pod_name": "whereami-echo-headers-78766fb94f-ggmcb",
  "pod_name_emoji": "🧑🏿",
  "pod_namespace": "default",
  "pod_service_account": "whereami-ksa-echo-headers",
  "project_id": "alexmattson-scratch",
  "timestamp": "2020-08-11T18:21:58",
  "zone": "us-central1-c"
}
```


### Notes

If you'd like to build & publish via Google's [buildpacks](https://github.com/GoogleCloudPlatform/buildpacks), something like this should do the trick (leveraging the local `Procfile`):

```pack build --builder gcr.io/buildpacks/builder:v1 --publish gcr.io/${PROJECT_ID}/whereami```


