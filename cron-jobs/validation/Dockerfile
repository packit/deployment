FROM fedora:32

RUN dnf install -y python3-ogr python3-copr python3-pip && dnf clean all

RUN pip install --upgrade sentry-sdk==0.14.2

COPY packit-service-validation.py /usr/bin/

CMD ["python3", "/usr/bin/packit-service-validation.py"]
