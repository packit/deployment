FROM fedora:32

RUN dnf install -y origin-clients && \
    dnf clean all

COPY delete-pvcs.sh /usr/bin/

CMD ["bash", "/usr/bin/delete-pvcs.sh"]
