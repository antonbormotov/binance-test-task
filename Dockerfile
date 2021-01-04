FROM python:3.8-buster

ENV PYTHONPATH="$PYTHONPATH:/usr/src/binance"
ENV PYTHONUNBUFFERED 1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN rm -rf /root/.cache/pip /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN mkdir -p /usr/src/binance
CMD [ "python", "/usr/src/binance/main.py" ]
