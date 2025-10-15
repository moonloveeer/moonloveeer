# Kubernetes Deployment

These manifests deploy the QRL wallet container from GHCR onto a Kubernetes cluster.

## Prerequisites
- Cluster with Kubernetes 1.24+
- `kubectl` configured for the target cluster
- Pull access to `ghcr.io/moonloveeer/moonloveeer` (set package visibility to public or create a secret)
- Kubernetes secret containing Flask `SECRET_KEY`

## Manifests
- Deployment: `k8s/deployment.yaml`
- Service: `k8s/service.yaml`

Apply with:

```bash
kubectl apply -f k8s/ -n <namespace>
```

## Secrets
Create two secrets:

```bash
kubectl create secret generic qrl-wallet-secrets \
  --from-literal=secret-key=$(openssl rand -hex 32) \
  -n <namespace>

kubectl create secret docker-registry ghcr-credentials \
  --docker-server=ghcr.io \
  --docker-username=<github-username> \
  --docker-password=<github-token> \
  --docker-email=<email> \
  -n <namespace>
```

If the GHCR package is public, you can omit `imagePullSecrets` in the deployment.

## Probes and resources
- Readiness/liveness probes target `/healthz` on port `5001`.
- Resource requests: 250m CPU / 256Mi memory. Limits: 500m CPU / 512Mi memory.
- Environment variables disable auto-mining and inject the secret key securely.
- GitHub Actions workflow `.github/workflows/k8s-lint.yml` runs kubeconform against the manifests on every push/PR touching `k8s/`.

## Ingress / Exposure
`k8s/service.yaml` defines a `ClusterIP` service. Add an Ingress or LoadBalancer service depending on cluster requirements.

## GitHub Actions deployment (optional)
A manual workflow (`.github/workflows/k8s-deploy.yml`) demonstrates applying these manifests using a `KUBE_CONFIG_BASE64` secret.
