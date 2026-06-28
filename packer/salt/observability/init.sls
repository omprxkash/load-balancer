# SaltStack state: observability agent
# Installs Prometheus node_exporter for metrics, and a log shipper.
# Installs Prometheus node_exporter for metrics and a distributed tracing agent.

node_exporter:
  pkg.installed:
    - name: prometheus-node-exporter

node_exporter_service:
  service.running:
    - name: prometheus-node-exporter
    - enable: True
    - require:
      - pkg: node_exporter

# Log shipper (Vector is a modern Rust-based alternative to Fluentd)
/etc/apt/sources.list.d/vector.list:
  file.managed:
    - contents: |
        deb [arch=amd64] https://packages.timber.io/vector/0.X/deb stable vector

vector:
  pkg.installed: []
  service.running:
    - enable: True

/etc/vector/vector.toml:
  file.managed:
    - contents: |
        [sources.envoy_access_logs]
        type = "file"
        include = ["/var/log/envoy/access.log"]

        [sinks.stdout]
        type = "console"
        inputs = ["envoy_access_logs"]
        encoding.codec = "json"
