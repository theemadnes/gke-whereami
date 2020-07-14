# gke-whereami
A simple Flask app for showing what node / ip / service_account / zone / project / cluster a given K8s pod is in, plus stuff like the `Host` header. It includes an emoji that is hashed from the pod name, which makes it a little easier to visually track the pod you're dealing with.

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
  --cluster-version=1.16 \
  --enable-ip-alias \
  --enable-stackdriver-kubernetes \
  --region=$COMPUTE_REGION \
  --num-nodes=1

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

```{"cluster_name":"cluster-1","host_header":"34.66.118.115","node_name":"gke-cluster-1-default-pool-c91b5644-q7w5.c.alexmattson-scratch.internal","pod_ip":"10.4.0.7","pod_name":"whereami-596cb9b99-x2vz2","pod_name_emoji":"🏃🏾‍♀️","pod_namespace":"default","pod_service_account":"whereami-ksa","project_id":"alexmattson-scratch","timestamp":"2020-07-14T15:33:07","version":"1.0","zone":"us-central1-c"}```


#### using gke-whereami to call downstream services 

`gke-whereami` has an optional flag that will cause it to attempt to call another backend service within your GKE cluster (for example, a different, non-public instance of itself). 

*NOTE:* this backend call assumes the downstream service is returning JSON.

First, build the non-public instance of `gke-whereami`:

```kustomize build k8s-backend-overlay-example | kubectl apply -f -```

*or*

```kubectl apply -k k8s-backend-overlay-example```

Once that service is up and running, modify `k8s/configmap.yaml`'s `BACKEND_ENABLED` to `"True"`. You will have to redeploy the pods in the whereami service as they will not automatically be recreated when you update the configmap.

The (slightly busy-looking) result should look like this:

```{"backend_result":{"cluster_name":"cluster-1","host_header":"whereami-backend","node_name":"gke-cluster-1-default-pool-c91b5644-v8kg.c.alexmattson-scratch.internal","pod_ip":"10.4.2.5","pod_name":"whereami-backend-5d5f79bdf9-kknxd","pod_name_emoji":"🇺🇳","pod_namespace":"default","pod_service_account":"whereami-ksa-backend","project_id":"alexmattson-scratch","timestamp":"2020-07-14T15:33:08","version":"1.0","zone":"us-central1-c"},"cluster_name":"cluster-1","host_header":"34.66.118.115","node_name":"gke-cluster-1-default-pool-c91b5644-q7w5.c.alexmattson-scratch.internal","pod_ip":"10.4.0.7","pod_name":"whereami-596cb9b99-x2vz2","pod_name_emoji":"🏃🏾‍♀️","pod_namespace":"default","pod_service_account":"whereami-ksa","project_id":"alexmattson-scratch","timestamp":"2020-07-14T15:33:07","version":"1.0","zone":"us-central1-c"}```

If you wish to call a different backend service, modify `k8s/configmap.yaml`'s `BACKEND_SERVICE` to some other service name. 


#### Note

The operating port of this service has been switched from `5000` to `8080` to work easily with the managed version of Cloud Run.

If you'd like to build & publish via Google's buildpacks, something like this should do the trick (leveraging the `Procfile`:

```pack build --builder gcr.io/buildpacks/builder:v1 --publish gcr.io/#target_project#/whereami```
