# gke-whereami

A simple Kubernetes-oriented app for describing the location of the pod serving a request via its attributes (cluster name, cluster region, pod name, namespace, service account, etc). The response payload includes an emoji that is hashed from the pod name, which makes it a little easier for a human to visually identify the pod you're dealing with.

This was originally written for testing & debugging multi-cluster ingress use cases on GKE (now Ingress for Anthos).

### Setup

Create a GKE cluster 

First define your environment variables (substituting where #needed#):

```
export PROJECT_ID=#YOUR_PROJECT_ID#

export COMPUTE_REGION=#YOUR_COMPUTE_REGION#

export CLUSTER_NAME=whereami
```

Now create your resources:

```
gcloud beta container clusters create $CLUSTER_NAME \
  --enable-ip-alias \
  --enable-stackdriver-kubernetes \
  --region=$COMPUTE_REGION \
  --num-nodes=1 \
  --release-channel=regular

gcloud container clusters get-credentials $CLUSTER_NAME --region $COMPUTE_REGION
```

Deploy the service/pods:

```kubectl apply -k k8s```

*or*

```kustomize build k8s | kubectl apply -f -```

Get the service endpoint:
```
WHEREAMI_ENDPOINT=$(kubectl get svc | grep -v EXTERNAL-IP | awk '{ print $4}')
```

Wrap things up by `curl`ing the `EXTERNAL-IP` of the service. 

```curl $WHEREAMI_ENDPOINT -H "Host: hello"```

Result:

```{"cluster_name":"cluster-1","host_header":"34.66.118.115","id_string":"frontend","node_name":"gke-cluster-1-default-pool-c91b5644-v8kg.c.alexmattson-scratch.internal","pod_ip":"10.4.2.15","pod_name":"whereami-c657c68f5-9jtkw","pod_name_emoji":"👇","pod_namespace":"default","pod_service_account":"whereami-ksa","project_id":"alexmattson-scratch","timestamp":"2020-07-29T19:08:31","zone":"us-central1-c"}```


#### using gke-whereami to call downstream services 

`gke-whereami` has an optional flag within its configmap that will cause it to attempt to call another backend service within your GKE cluster (for example, a different, non-public instance of itself). This is helpful for demonstrating a public microservice call to a non-public microservice, and then including the responses of both microservices in the payload delivered back to the user.  

*NOTE:* this backend call assumes the downstream service is returning JSON.

First, build the "backend" instance of `gke-whereami`:

```kustomize build k8s-backend-overlay-example | kubectl apply -f -```

*or*

```kubectl apply -k k8s-backend-overlay-example```

Once that service is up and running, modify `k8s/configmap.yaml`'s `BACKEND_ENABLED` to `"True"`. You will have to redeploy the pods in the whereami service as they will not automatically be recreated when you update the configmap.

The (*slightly* busy-looking) result should look like this:

```{"backend_result":{"cluster_name":"cluster-1","host_header":"whereami-backend","id_string":"backend","node_name":"gke-cluster-1-default-pool-c91b5644-q7w5.c.alexmattson-scratch.internal","pod_ip":"10.4.0.10","pod_name":"whereami-backend-966547575-nk9df","pod_name_emoji":"📔","pod_namespace":"default","pod_service_account":"whereami-ksa-backend","project_id":"alexmattson-scratch","timestamp":"2020-07-29T19:32:15","zone":"us-central1-c"},"cluster_name":"cluster-1","host_header":"34.72.90.134","id_string":"frontend","node_name":"gke-cluster-1-default-pool-c91b5644-v8kg.c.alexmattson-scratch.internal","pod_ip":"10.4.2.16","pod_name":"whereami-c657c68f5-r65s5","pod_name_emoji":"🌋","pod_namespace":"default","pod_service_account":"whereami-ksa","project_id":"alexmattson-scratch","timestamp":"2020-07-29T19:32:15","zone":"us-central1-c"}```

If you wish to call a different backend service, modify `k8s/configmap.yaml`'s `BACKEND_SERVICE` to some other service name. 


#### Notes

The operating port of the pod has been switched from `5000` to `8080` to work easily with the managed version of Cloud Run.

If you'd like to build & publish via Google's buildpacks, something like this should do the trick (leveraging the local `Procfile`:

```pack build --builder gcr.io/buildpacks/builder:v1 --publish gcr.io/${PROJECT_ID}/whereami```
