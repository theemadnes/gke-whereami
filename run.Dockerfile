FROM gcr.io/buildpacks/gcp/run:v1
USER root
RUN apt-get update && apt-get install -y --no-install-recommends   wget &&   apt-get clean &&   rm -rf /var/lib/apt/lists/* &&   wget -O /bin/grpc_health_probe https://github.com/grpc-ecosystem/grpc-health-probe/releases/download/v0.3.6/grpc_health_probe-linux-amd64 &&   chmod +x /bin/grpc_health_probe
USER cnb
