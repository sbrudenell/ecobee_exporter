FROM python:3-slim

COPY . /src
ADD http://github.com/alertedsnake/python-ecobee/archive/master.zip /python-ecobee.zip

RUN python -c "import zipfile; zipfile.ZipFile('/python-ecobee.zip', 'r').extractall('/')" && \
    pip install /python-ecobee-master && \
    rm -rf /python-ecobee-master && \
    pip install /src && \
    cp /usr/local/bin/ecobee_exporter /ecobee_exporter

EXPOSE 9756

ENTRYPOINT ["/ecobee_exporter"]
