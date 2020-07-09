# gke-whereami
A simple Flask app for showing what node / zone / project / cluster a given K8s pod is in. It includes an emoji that is hashed from the pod name, which makes it a little easier to visually track the pod you're dealing with.

This has been recently modified to make use of `kustomize` for some advanced use cases. 


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
  --cluster-version=1.15 \
  --enable-ip-alias \
  --enable-stackdriver-kubernetes \
  --region=$COMPUTE_REGION \
  --num-nodes=1

gcloud container clusters get-credentials $CLUSTER_NAME --region $COMPUTE_REGION

```

Deploy the service/pods:

```
kubectl apply -k k8s
```

*or*

```
kustomize build k8s | kubectl apply -f -
```

Get the service endpoint:
```
WHEREAMI_ENDPOINT=$(kubectl get svc | grep -v EXTERNAL-IP | awk '{ print $4}')
```

Wrap things up by `curl`ing the `EXTERNAL-IP` of the service. 

```curl $WHEREAMI_ENDPOINT```

Result:

```{"cluster_name":"acn-ips-01","node_name":"gke-acn-ips-01-default-pool-949017b6-chsz.c.alexmattson-scratch.internal","pod_ip":"10.56.1.10","pod_name":"whereami-764cb9d75c-7tccm","pod_name_emoji":"🌤","pod_namespace":"default","pod_service_account":"whereami-ksa","project_id":"alexmattson-scratch","timestamp":"2019-10-26T06:10:28","zone":"us-central1-f"}```


#### using `gke-whereami` to call other instances of itself 

`gke-whereami` has an optional flag that will cause it to attempt to call another backend service within your GKE cluster (for example, a different, non-public instance of itself). 

First, build the non-public instance of `gke-whereami`:

```
kustomize build k8s-backend-overlay-example | kubectl apply -f -
```

*or*

```
kubectl apply -k k8s-backend-overlay-example
```

Once that service is up and running, modify `k8s/configmap.yaml`'s `BACKEND_ENABLED` to `"True"`. You will have to redeploy the pods in the whereami service as they will not automatically be created when you updated the configmap.

If you wish to call a different backend service, modify `k8s/configmap.yaml`'s `BACKEND_SERVICE` to some other service name. 


#### Note

The operating port of this service has been switched from `5000` to `8080` to work easily with the managed version of Cloud Run.


