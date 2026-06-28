# SaltStack state: kernel network tuning for high-throughput proxy workloads.
# These sysctl parameters are critical for a proxy handling millions of connections.

/etc/sysctl.d/99-envoy-proxy.conf:
  file.managed:
    - contents: |
        # Increase socket buffer sizes for high-throughput proxy
        net.core.rmem_max = 134217728
        net.core.wmem_max = 134217728
        net.ipv4.tcp_rmem = 4096 87380 134217728
        net.ipv4.tcp_wmem = 4096 65536 134217728

        # Increase file descriptor limits
        fs.file-max = 1000000

        # Enable TCP fast open
        net.ipv4.tcp_fastopen = 3

        # Reduce TIME_WAIT connections
        net.ipv4.tcp_tw_reuse = 1
        net.ipv4.ip_local_port_range = 1024 65535

        # Increase connection backlog
        net.core.somaxconn = 65535
        net.ipv4.tcp_max_syn_backlog = 65535

apply_sysctl:
  cmd.run:
    - name: sysctl -p /etc/sysctl.d/99-envoy-proxy.conf
    - require:
      - file: /etc/sysctl.d/99-envoy-proxy.conf
