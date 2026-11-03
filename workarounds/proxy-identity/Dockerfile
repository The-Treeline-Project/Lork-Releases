ARG LORK_IMAGE=ghcr.io/the-treeline-project/lork-releases/lork@sha256:e862e237f92cbf351676d0a67239d856a80f9649e507c069d9a654f483a3490e
FROM ${LORK_IMAGE}
WORKDIR /lork
COPY proxy_identity.py /lork/proxy_identity_compat.py
COPY test_proxy_identity.py /lork/test_proxy_identity_compat.py
RUN ["/opt/venv/bin/python3", "-m", "test_proxy_identity_compat"]
ENTRYPOINT ["/opt/venv/bin/python3", "-m", "proxy_identity_compat"]
