FROM python:3.12-alpine
WORKDIR /app
COPY witness.py /app/witness.py
ENV WITNESS_PORT=8089
EXPOSE 8089
CMD ["python", "/app/witness.py"]
