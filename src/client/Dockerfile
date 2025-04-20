FROM python:3.12.1
LABEL authors="beto"
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
ENV PYTHONUNBUFFERED=1
ENV SERVER_IP="albertopd.ddns.net"
ENV SERVER_PORT="4444"
EXPOSE 5000
CMD ["python3", "./GUI/app.py"]