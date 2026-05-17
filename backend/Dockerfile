# 1. Base Python Image
FROM python:3.14-slim

# 2. # Set working directory inside the container
WORKDIR /app

# 3. Install system dependencies required by Playwright and PostgreSQL driver
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 4. Install Poetry inside the container
RUN pip install poetry

# 5. Tell Poetry to NOT create a virtual environment inside the container
# Since Docker itself is already an isolated environment, venv is redundant
RUN poetry config virtualenvs.create false

# 6. Copy ONLY dependency files first to leverage Docker layer caching
# Docker will only re-run the install step if these files change
COPY pyproject.toml poetry.lock ./

# 7. Install dependencies via Poetry
# --no-root = don't install the project itself, just its dependencies
# --no-interaction = don't ask any interactive questions
# --no-ansi = disable colored output (cleaner Docker logs)
RUN poetry install --no-root --no-interaction --no-ansi

# 8. Install Playwright's Chromium browser inside the container
RUN poetry run playwright install chromium
RUN poetry run playwright install-deps chromium

# 9. Copy the rest of the project code into the container
# This step is intentionally AFTER dependency install to maximize cache reuse
COPY . .

# 10. Expose port 8000 so it is accessible outside the container
EXPOSE 8000

# 11. Command to run when the container starts
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]