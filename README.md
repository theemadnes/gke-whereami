# gke-whereami

A simple Kubernetes-oriented app for describing the location of the pod serving a request via its attributes (cluster name, cluster region, pod name, namespace, service account, etc). The response payload includes an emoji that is hashed from the pod name, which makes it a little easier for a human to visually identify the pod you're dealing with.

This was originally written for testing & debugging multi-cluster ingress use cases on GKE (now Ingress for Anthos). The app's response payload will omit fields that it's unable to provide, meaning you can run this app on non-GKE K8s clusters, but the payload's fields will reflect that gap.

### Setup

#### Step 1 - Create a GKE cluster 

First define your environment variables (substituting where #needed#):

```
export PROJECT_ID=#YOUR_PROJECT_ID#

export COMPUTE_REGION=#YOUR_COMPUTE_REGION# # this expects a region, not a zone

export CLUSTER_NAME=whereami
```

Now create your cluster:

```
gcloud beta container clusters create $CLUSTER_NAME \
  --enable-ip-alias \
  --enable-stackdriver-kubernetes \
  --region=$COMPUTE_REGION \
  --num-nodes=1 \
  --release-channel=regular

gcloud container clusters get-credentials $CLUSTER_NAME --region $COMPUTE_REGION
```

This will create a regional cluster with a single node per zone (3 nodes in total). 

#### Step 2 - Deploy the service/pods:

```
kubectl apply -k k8s
```

*or via [kustomize](https://kustomize.io/)*

```
kustomize build k8s | kubectl apply -f -
```

Get the service endpoint:
> Note: this may be `pending` for a few minutes while the service provisions
```
WHEREAMI_ENDPOINT=$(kubectl get svc whereami | grep -v EXTERNAL-IP | awk '{ print $4}')
```

Wrap things up by `curl`ing the `EXTERNAL-IP` of the service. 

```
curl $WHEREAMI_ENDPOINT
```

Result:

```{"cluster_name":"cluster-1","host_header":"34.72.90.134","metadata":"frontend","node_name":"gke-cluster-1-default-pool-c91b5644-v8kg.c.alexmattson-scratch.internal","pod_ip":"10.4.2.34","pod_name":"whereami-7b79956dd6-vmm9z","pod_name_emoji":"🧚🏼‍♀️","pod_namespace":"default","pod_service_account":"whereami-ksa","project_id":"alexmattson-scratch","timestamp":"2020-07-30T05:44:14","zone":"us-central1-c"}```

### [Optional] Setup backend service call

`gke-whereami` has an optional flag within its configmap that will cause it to call another backend service within your GKE cluster (for example, a different, non-public instance of itself). This is helpful for demonstrating a public microservice call to a non-public microservice, and then including the responses of both microservices in the payload delivered back to the user.

#### [Optional] Step 1 - Remove existing deployment 

First, remove the default deployment, as the default deployment won't attempt to call the downstream service, since updating a configmap referenced by a pod will not automatically redeploy that pod:

```
kubectl delete -k k8s
```

#### [Optional] Step 2 - Deploy the backend instance

```
kubectl apply -k k8s-backend-overlay-example
```

*or via [kustomize](https://kustomize.io/)*

```
kustomize build k8s-backend-overlay-example | kubectl apply -f -
```

#### [Optional] Step 3 - Configure & deploy the frontend

Modify `k8s/configmap.yaml`'s `BACKEND_ENABLED` field to `"True"`.

Next, redeploy the "frontend" instance of `gke-whereami`:

```
kubectl apply -k k8s
```

*or via [kustomize](https://kustomize.io/)*

```
kustomize build k8s | kubectl apply -f -
```

Get the service endpoint:
> Note: this may be `pending` for a few minutes while the service provisions
```
WHEREAMI_ENDPOINT=$(kubectl get svc whereami | grep -v EXTERNAL-IP | awk '{ print $4}')
```

Wrap things up by `curl`ing the `EXTERNAL-IP` of the service. 

```
curl $WHEREAMI_ENDPOINT
```

The (*slightly* busy-looking) result should look like this:

```{"backend_result":{"cluster_name":"cluster-1","host_header":"whereami-backend","metadata":"backend","node_name":"gke-cluster-1-default-pool-c91b5644-v8kg.c.alexmattson-scratch.internal","pod_ip":"10.4.2.37","pod_name":"whereami-backend-86bdc7b596-z4dqk","pod_name_emoji":"💪🏾","pod_namespace":"default","pod_service_account":"whereami-ksa-backend","project_id":"alexmattson-scratch","timestamp":"2020-07-30T05:56:15","zone":"us-central1-c"},"cluster_name":"cluster-1","host_header":"34.72.90.134","metadata":"frontend","node_name":"gke-cluster-1-default-pool-c91b5644-1z7l.c.alexmattson-scratch.internal","pod_ip":"10.4.1.29","pod_name":"whereami-7888579d9d-qdmbg","pod_name_emoji":"🧜","pod_namespace":"default","pod_service_account":"whereami-ksa","project_id":"alexmattson-scratch","timestamp":"2020-07-30T05:56:15","zone":"us-central1-c"}```

Look at the `backend_result` field from the response. That portion of the JSON is from the backend service.

If you wish to call a different backend service, modify `k8s/configmap.yaml`'s `BACKEND_SERVICE` to some other service name. 


### Notes

If you'd like to build & publish via Google's [buildpacks](https://github.com/GoogleCloudPlatform/buildpacks), something like this should do the trick (leveraging the local `Procfile`):

```pack build --builder gcr.io/buildpacks/builder:v1 --publish gcr.io/${PROJECT_ID}/whereami```

