FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY app ./app
COPY static ./static
COPY run.py ./
RUN pip install --no-cache-dir .
ENV HOMEOPS_HOST=0.0.0.0
ENV HOMEOPS_PORT=8000
EXPOSE 8000
CMD ["python", "run.py"]
