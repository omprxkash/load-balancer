# SaltStack state: container runtime for sidecars
# Installs Docker so auth/ratelimit/authz sidecars can run as containers.

docker_apt_repo:
  pkgrepo.managed:
    - humanname: Docker CE
    - name: deb [arch=amd64] https://download.docker.com/linux/ubuntu jammy stable
    - file: /etc/apt/sources.list.d/docker.list
    - key_url: https://download.docker.com/linux/ubuntu/gpg

docker-ce:
  pkg.installed:
    - require:
      - pkgrepo: docker_apt_repo

docker:
  service.running:
    - enable: True
    - require:
      - pkg: docker-ce

# Add ubuntu user to docker group (avoid sudo)
docker_group:
  group.present:
    - name: docker
    - addusers:
      - ubuntu
