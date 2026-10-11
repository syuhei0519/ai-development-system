#!/usr/bin/env bash
# Local synthetic validation only. Never calls real kubectl/kind or dispatches CI.
# Usage: bash reproduce.sh HEAD_CHECKOUT BASE_CHECKOUT OUTPUT_DIR
set -euo pipefail
head=$(realpath "$1"); base=$(realpath "$2"); output=$(realpath -m "$3")
script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
test "$(git -C "$head" rev-parse HEAD)" = e01882d8a2c4ac4eadad5b081c1b5c69e5599776
test "$(git -C "$base" rev-parse HEAD)" = b989e29b8addbd6396c5c2b4833b969bc15fc8fa
git -C "$head" diff --exit-code
git -C "$base" diff --exit-code
mkdir -p "$output"
cd "$head"
go version
helm version --short
bash ci/github/test.sh
for module in tools/bootstrap tools/scan-gate; do
 (cd "$module"; go test -race -count=1 ./...; go vet ./...; go build -o "$output/${module##*/}" .)
done
sh ci/validate.sh
PE_OBSERVABILITY_RENDER_DIR=.rendered .build/bootstrap-test -test.run 'TestObservabilityContract|TestCollectorContract|TestGrafanaProvisioningBoundary|TestOrderWorkloadsContract' -test.v
.security/scan-gate -check-render-only .rendered -out "$output/render-boundary.json"
python3 "$script_dir/independent.py" "$head" "$base" "$output/bootstrap" "$output/independent.json"
image=ghcr.io/yannh/kubeconform:v0.7.0-alpine@sha256:8f0eeaaa96ba27ba1500b0e4b1c215acc358d159c62a7ecae58d7a03403287b0
# Existing infrastructure CA only; no TLS bypass or host trust configuration writes.
mounts=(--rm -v /etc/ssl/certs:/etc/ssl/certs:ro -v "$head:/work:ro" -w /work)
docker run "${mounts[@]}" "$image" -strict -summary -kubernetes-version 1.36.0 .rendered/runner-foundation.yaml .rendered/gitlab-runner.yaml .rendered/observability-foundation.yaml .rendered/prometheus.yaml .rendered/argocd-pods.yaml .rendered/collector-disabled.yaml .rendered/collector-enabled.yaml .rendered/grafana.yaml
for pair in application:applications appproject:projects; do
 kind=${pair%:*}; file=${pair#*:}
 docker run "${mounts[@]}" "$image" -strict -summary -schema-location "https://raw.githubusercontent.com/datreeio/CRDs-catalog/ad3b08c5045129d7bb1eeffd8e61719b2c8dd1e2/argoproj.io/${kind}_v1alpha1.json" ".rendered/$file.yaml"
done
# A standalone clone is necessary: /work-only mounts cannot resolve external worktree .git files.
git clone --no-hardlinks "$head" "$output/scan-checkout"
cp -a .rendered "$output/scan-checkout/"
mkdir -p "$output/scan-checkout/.security"
cp .security/scan-gate "$output/scan-checkout/.security/"
docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -v /etc/ssl/certs:/etc/ssl/certs:ro -v "$output/scan-checkout:/work" -w /work -e SECURITY_RENDER_REQUIRED=true --entrypoint sh aquasec/trivy:0.75.0@sha256:9db099105405c648166e6b94155eb32f8da12673cf1f455207f7385cc9a77283 -ec 'git config --global --add safe.directory /work; sh ci/source-scan.sh'
