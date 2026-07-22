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
