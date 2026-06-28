# SaltStack state: logging agent
# Installs Vector to ship Envoy access logs to centralised logging.

vector_pkg:
  pkgrepo.managed:
    - name: deb [arch=amd64] https://packages.timber.io/vector/0.X/deb stable vector
    - file: /etc/apt/sources.list.d/vector.list

vector:
  pkg.installed:
    - require:
      - pkgrepo: vector_pkg
  service.running:
    - enable: True

/etc/vector/vector.toml:
  file.managed:
    - makedirs: True
    - contents: |
        [sources.envoy_access]
        type = "file"
        include = ["/var/log/envoy/*.log"]

        [transforms.parse_json]
        type = "remap"
        inputs = ["envoy_access"]
        source = '. = parse_json!(.message)'

        [sinks.stdout]
        type = "console"
        inputs = ["parse_json"]
        encoding.codec = "json"
    - require:
      - pkg: vector
