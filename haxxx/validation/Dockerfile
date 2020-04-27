FROM fedora:31

RUN dnf install -y python-ogr python-copr python-copr-doc pip && dnf clean all

RUN pip install --upgrade sentry-sdk==0.14.2

COPY packit-service-validation.py /usr/bin/

CMD ["python3", "/usr/bin/packit-service-validation.py"]
