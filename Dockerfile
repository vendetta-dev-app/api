FROM python:3.11.4-slim-bookworm
ENV PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update
ADD requirements.txt /app
RUN pip install -r requirements.txt
ADD . /app
EXPOSE 8000
CMD ["sh", "run.sh"]