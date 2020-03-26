FROM python:2.7-alpine
RUN apk add --update --no-cache g++ alpine-sdk postgresql postgresql-dev libffi libffi-dev openrc bash python2-dev
WORKDIR /freeswitch_proxy
COPY . .
RUN pip install pipenv
RUN pipenv install
