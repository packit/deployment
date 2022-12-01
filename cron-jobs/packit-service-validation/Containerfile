FROM fedora:37

RUN dnf install -y python3-ogr python3-copr python3-pip && dnf clean all

RUN pip3 install --upgrade sentry-sdk && pip3 check

COPY packit-service-validation.py /usr/bin/

CMD ["python3", "/usr/bin/packit-service-validation.py"]
