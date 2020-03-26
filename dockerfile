FROM python:2.7
WORKDIR /freeswitch_proxy
COPY . .
RUN pip install pipenv
RUN pipenv install
