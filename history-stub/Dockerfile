FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir "Flask>=3.1,<4"
COPY app.py .
EXPOSE 5005
CMD ["flask", "--app", "app", "run", "--host=0.0.0.0", "--port=5005"]
