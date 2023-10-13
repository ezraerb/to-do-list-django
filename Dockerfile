FROM python:3.8
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . code
WORKDIR /code
RUN chmod +x ./entrypoint.sh
EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
