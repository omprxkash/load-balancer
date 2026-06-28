# SaltStack state: security hardening
# Disables root SSH, sets auditd, removes unnecessary packages.

disable_root_ssh:
  file.replace:
    - name: /etc/ssh/sshd_config
    - pattern: "^PermitRootLogin.*"
    - repl: "PermitRootLogin no"

auditd:
  pkg.installed: []
  service.running:
    - enable: True
    - require:
      - pkg: auditd

remove_unnecessary:
  pkg.removed:
    - pkgs:
      - telnet
      - rsh-client
