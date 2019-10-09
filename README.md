# gke-whereami
A simple Flask app for showing what node / zone / project / cluster a given K8s pod is in


### Setup

Create a regional GKE cluster with workload identity enabled 

First define your environment variables (substituting where #needed#):

```
export PROJECT_ID=#YOUR_PROJECT_ID#

export COMPUTE_REGION=#YOUR_COMPUTE_REGION#

export CLUSTER_NAME=whereami

export GSA_NAME=whereami-gsa

export K8S_NAMESPACE=whereami

export KSA_NAME=whereami-ksa

```

Now create your resources:

```
gcloud beta container clusters create $CLUSTER_NAME \
  --cluster-version=1.14 \
  --identity-namespace=$PROJECT_ID.svc.id.goog \
  --enable-ip-alias \
  --enable-stackdriver-kubernetes \
  --region=$COMPUTE_REGION \
  --num-nodes=1

gcloud container clusters get-credentials $CLUSTER_NAME --region $COMPUTE_REGION

gcloud iam service-accounts create $GSA_NAME

kubectl create namespace $K8S_NAMESPACE

kubectl create serviceaccount \
 --namespace $K8S_NAMESPACE \
 $KSA_NAME

gcloud iam service-accounts add-iam-policy-binding \
  --role roles/iam.workloadIdentityUser \
  --member "serviceAccount:$PROJECT_ID.svc.id.goog[$K8S_NAMESPACE/$KSA_NAME]" \
  $GSA_NAME@$PROJECT_ID.iam.gserviceaccount.com

kubectl annotate serviceaccount \
  --namespace $K8S_NAMESPACE \
  $KSA_NAME \
  iam.gke.io/gcp-service-account=$GSA_NAME@$PROJECT_ID.iam.gserviceaccount.com
```

Verify that things are correct:
```
kubectl run -it \
  --generator=run-pod/v1 \
  --image google/cloud-sdk \
  --serviceaccount $KSA_NAME \
  --namespace $K8S_NAMESPACE \
  workload-identity-test

curl -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/zone
```