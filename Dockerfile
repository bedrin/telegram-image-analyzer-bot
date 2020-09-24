FROM python:3-alpine

RUN apk add py3-pip g++ make pkgconfig openssl-dev libffi-dev --upgrade

RUN pip3 install python-telegram-bot

RUN pip3 install schedule

RUN apk add jpeg-dev zlib-dev
ENV LIBRARY_PATH=/lib:/usr/lib
RUN pip3 install Pillow

WORKDIR /usr/src/app

ADD ./monitoring-bot.py /usr/src/app/monitoring-bot.py

CMD ["/usr/local/bin/python3", "/usr/src/app/monitoring-bot.py"]
