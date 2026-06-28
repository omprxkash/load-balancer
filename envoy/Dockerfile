FROM envoyproxy/envoy:v1.31-latest
COPY bootstrap.yaml /etc/envoy/envoy.yaml
EXPOSE 10000 9901
CMD ["envoy", "-c", "/etc/envoy/envoy.yaml", "--log-level", "info"]
