FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml setup.py setup.cfg ./
COPY src/ src/
COPY lead_scorer/ lead_scorer/
COPY scripts/ scripts/
COPY config.py .

RUN pip install --no-cache-dir .

RUN python scripts/generate_data.py && python src/pipeline/run_pipeline.py

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "src/app/main.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
