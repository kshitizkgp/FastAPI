# --------- requirements ---------

FROM python:3.11 as requirements-stage

WORKDIR /tmp

RUN pip install poetry

COPY ./pyproject.toml ./poetry.lock* /tmp/

RUN poetry export -f requirements.txt --output requirements.txt --without-hashes


# --------- final image build ---------
FROM python:3.11

WORKDIR /code

COPY --from=requirements-stage /tmp/requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

#TODO (kshitizkr): Need to remove this env file when setting up CI/CD.
COPY ./src/.env.production /code/.env.production
COPY ./src/app /code/app

# -------- replace with comment to run with gunicorn --------
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]
#CMD ["gunicorn", "app.main:app", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8080"]
