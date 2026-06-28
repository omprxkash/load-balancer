# SaltStack state: install and configure Envoy proxy
# This is the equivalent of the Dockerfile RUN commands in the modern k8s version.

envoy_apt_repo:
  pkgrepo.managed:
    - humanname: Envoy Proxy
    - name: deb [arch=amd64] https://apt.envoyproxy.io jammy main
    - dist: jammy
    - file: /etc/apt/sources.list.d/envoy.list
    - key_url: https://apt.envoyproxy.io/signing.key

envoy:
  pkg.installed:
    - require:
      - pkgrepo: envoy_apt_repo

/etc/envoy:
  file.directory:
    - makedirs: True
    - mode: 755

/etc/envoy/envoy.yaml:
  file.managed:
    - source: salt://envoy/files/bootstrap.yaml
    - makedirs: True

envoy_service:
  service.running:
    - name: envoy
    - enable: True
    - require:
      - pkg: envoy
      - file: /etc/envoy/envoy.yaml
