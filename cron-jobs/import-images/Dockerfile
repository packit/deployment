FROM fedora:33

RUN dnf install -y origin-clients && \
    dnf clean all

COPY import-images.sh /usr/bin/

CMD ["bash", "/usr/bin/import-images.sh"]
