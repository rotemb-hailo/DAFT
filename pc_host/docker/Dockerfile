FROM python:3.7

WORKDIR /usr/src/app

COPY .. .
RUN python3 setup.py install


ENTRYPOINT [ "python", "./main.py" ]
