FROM python:3.11-slim

# Don't write .pyc files; show Python output immediately
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy requirements first so Docker can cache the install step
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create the normal (non-root) user BEFORE copying the app,
# then make that user the owner of the copied file.
RUN useradd --create-home appuser
COPY --chown=appuser:appuser app.py .
USER appuser

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--browser.gatherUsageStats=false"]
