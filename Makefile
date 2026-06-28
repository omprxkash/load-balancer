.PHONY: up down demo test clean k8s k8s-down logs help

help:
	@echo ""
	@echo "  make up       - Start the full local stack (Docker Compose)"
	@echo "  make down     - Stop all containers"
	@echo "  make demo     - Run the end-to-end demo (provision + route)"
	@echo "  make test     - Run all unit tests"
	@echo "  make clean    - Remove containers, volumes, and build cache"
	@echo "  make k8s      - Deploy to local kind cluster"
	@echo "  make k8s-down - Tear down the kind cluster"
	@echo "  make logs     - Tail logs for all services"
	@echo ""

up:
	@echo "Starting stack..."
	cp -n .env.example .env 2>/dev/null || true
	docker compose up --build -d
	@echo ""
	@echo "Stack is up:"
	@echo "  OSB:       http://localhost:8080/v2/catalog"
	@echo "  Sovereign: http://localhost:8001/health"
	@echo "  Envoy:     http://localhost:10000"
	@echo "  Envoy admin: http://localhost:9901"

down:
	docker compose down

demo:
	@echo ""
	@echo "=== Provisioning jira-mock load balancer ==="
	./demo/provision-jira.sh
	@echo ""
	@echo "=== Waiting for provisioning to complete ==="
	@sleep 5
	@echo ""
	@echo "=== Testing routing through Envoy proxy ==="
	curl -s -H "Host: jira.local" -H "Authorization: Bearer dev-token-for-testing" \
		http://localhost:10000/ | python3 -m json.tool
	@echo ""
	@echo "=== Testing auth rejection (no token) ==="
	curl -s -o /dev/null -w "HTTP status: %{http_code}\n" \
		-H "Host: jira.local" http://localhost:10000/secure
	@echo ""
	@echo "=== Envoy cluster status ==="
	curl -s http://localhost:9901/clusters | grep -E "^jira|confluence|bitbucket"

test:
	cd osb && python3 -m pytest tests/ -v
	cd sovereign && python3 -m pytest tests/ -v
	cd sidecars/auth && python3 -m pytest tests/ -v

clean:
	docker compose down -v --remove-orphans
	docker system prune -f --filter label=project=load-balancer

logs:
	docker compose logs -f

k8s:
	@echo "Creating kind cluster..."
	kind create cluster --config infra/k8s/kind-config.yaml --name load-balancer
	@echo "Applying manifests..."
	kubectl apply -k infra/k8s/
	@echo ""
	@echo "Waiting for pods..."
	kubectl -n load-balancer wait --for=condition=ready pod --all --timeout=120s
	@echo ""
	@echo "Port-forwarding Envoy to localhost:10000..."
	kubectl -n load-balancer port-forward svc/envoy 10000:10000 &
	@echo "k8s stack is up. Run 'make demo' to test."

k8s-down:
	kind delete cluster --name load-balancer
