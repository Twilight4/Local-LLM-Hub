# local-llm-hub — kind + Helm lifecycle.
# Usage: make create && make install && make verify
CHART  := helm/local-llm-hub
BASE   := $(CHART)/values.yaml
LOCAL  := $(CHART)/values.local.yaml
NS     := local-llm-hub
REL    := llh

.PHONY: create install upgrade verify logs destroy

create:
	kind create cluster --config kind-config.yaml

install:
	helm install $(REL) $(CHART) -f $(BASE) -f $(LOCAL) -n $(NS) --create-namespace --wait

upgrade:
	helm upgrade $(REL) $(CHART) -f $(BASE) -f $(LOCAL) -n $(NS) --wait

verify:
	@echo "==> waiting for all pods Ready"
	kubectl -n $(NS) wait --for=condition=Ready pod --all --timeout=600s
	@echo "==> liveliness"
	curl -sf localhost:4000/health/liveliness && echo "  litellm OK"
	kubectl -n $(NS) exec deploy/ollama -- ollama list | grep -q llama3.2 && echo "  ollama models OK"
	curl -sf localhost:6333 >/dev/null && echo "  qdrant OK"
	curl -sf localhost:6006 >/dev/null && echo "  phoenix OK"
	curl -sf localhost:8080/health && echo "  open-webui OK"
	@echo "==> one-token chat"
	KEY=$$(grep masterKey $(LOCAL) | sed 's/.*"\(.*\)".*/\1/'); \
	RESP=$$(curl -s localhost:4000/v1/chat/completions \
	  -H "Authorization: Bearer $$KEY" \
	  -H "Content-Type: application/json" \
	  -d '{"model":"llama3.2","messages":[{"role":"user","content":"Say OK"}],"max_tokens":3}'); \
	echo "$$RESP" | grep -q choices && echo "  chat OK" || (echo "  chat FAIL: $$RESP" && exit 1)

logs:
	kubectl -n $(NS) logs -l app.kubernetes.io/part-of=local-llm-hub --tail=80 --all-containers

destroy:
	-helm uninstall $(REL) -n $(NS)
	-kind delete cluster --name local-llm-hub

# --- GitOps (ArgoCD) ---
# Usage: make gitops-bootstrap && make gitops-secret && make gitops-verify
ARGOCD_VERSION  := v3.4.5
ARGOCD_MANIFEST := https://raw.githubusercontent.com/argoproj/argo-cd/$(ARGOCD_VERSION)/manifests/install.yaml
ARGOCD_NS       := argocd

.PHONY: gitops-install gitops-apply gitops-secret gitops-verify gitops-bootstrap argocd-ui

gitops-install:
	@echo "==> installing ArgoCD $(ARGOCD_VERSION)"
	kubectl create namespace $(ARGOCD_NS) --dry-run=client -o yaml | kubectl apply -f -
	kubectl apply --server-side --force-conflicts -n $(ARGOCD_NS) -f $(ARGOCD_MANIFEST)
	kubectl -n $(ARGOCD_NS) wait deploy/argocd-server --for=condition=Available --timeout=300s

gitops-apply:
	@echo "==> applying ArgoCD Application"
	kubectl apply -f gitops/application.yaml

gitops-secret:
	@echo "==> injecting master key (out-of-band; ArgoCD-ignored)"
	@n=0; until kubectl get namespace $(NS) >/dev/null 2>&1; do n=$$((n+1)); [ $$n -ge 60 ] && { echo "  ns $(NS) not ready after ~180s - did ArgoCD sync?"; exit 1; }; echo "  waiting for ns $(NS)"; sleep 3; done
	KEY=$$(grep masterKey $(LOCAL) | sed 's/.*"\(.*\)".*/\1/'); \
	kubectl -n $(NS) create secret generic local-llm-hub-secrets \
	  --from-literal=LITELLM_MASTER_KEY="$$KEY" -o yaml --dry-run=client | \
	  kubectl -n $(NS) apply -f -

gitops-verify:
	@echo "==> ArgoCD Application sync/health"
	kubectl -n $(ARGOCD_NS) wait application/local-llm-hub --for=jsonpath='{.status.sync.status}'=Synced --timeout=600s
	kubectl -n $(ARGOCD_NS) get application local-llm-hub -o jsonpath='sync={.status.sync.status} health={.status.health.status}{"\n"}'
	@echo "==> waiting for all pods Ready"
	kubectl -n $(NS) wait --for=condition=Ready pod --all --timeout=600s
	@echo "==> app checks"
	curl -sf localhost:4000/health/liveliness && echo "  litellm OK"
	@echo "==> waiting for ollama models (post-install hook is async)"
	@n=0; until kubectl -n $(NS) exec deploy/ollama -- ollama list 2>/dev/null | grep -q llama3.2; do n=$$((n+1)); [ $$n -ge 60 ] && { echo "  ollama models MISSING (llama3.2)"; exit 1; }; sleep 5; done; echo "  ollama models OK"
	curl -sf localhost:6333 >/dev/null && echo "  qdrant OK"
	curl -sf localhost:6006 >/dev/null && echo "  phoenix OK"
	curl -sf localhost:8080/health && echo "  open-webui OK"
	@echo "==> one-token chat"
	KEY=$$(grep masterKey $(LOCAL) | sed 's/.*"\(.*\)".*/\1/'); \
	RESP=$$(curl -s localhost:4000/v1/chat/completions \
	  -H "Authorization: Bearer $$KEY" \
	  -H "Content-Type: application/json" \
	  -d '{"model":"llama3.2","messages":[{"role":"user","content":"Say OK"}],"max_tokens":3}'); \
	echo "$$RESP" | grep -q choices && echo "  chat OK" || (echo "  chat FAIL: $$RESP" && exit 1)

gitops-bootstrap: gitops-install gitops-apply

argocd-ui:
	@echo "==> ArgoCD UI: https://localhost:8081  (CTRL-C to stop)"
	@echo "    admin password: kubectl -n $(ARGOCD_NS) get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d"
	kubectl -n $(ARGOCD_NS) port-forward svc/argocd-server 8081:443
