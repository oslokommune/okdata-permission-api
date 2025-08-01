FROM public.ecr.aws/lambda/python:3.11

COPY dataplatform_keycloak ${LAMBDA_TASK_ROOT}/dataplatform_keycloak
COPY jobs ${LAMBDA_TASK_ROOT}/jobs
COPY models ${LAMBDA_TASK_ROOT}/models
COPY resources ${LAMBDA_TASK_ROOT}/resources
COPY app.py ${LAMBDA_TASK_ROOT}
COPY handler.py ${LAMBDA_TASK_ROOT}
COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install --no-cache-dir -r requirements.txt

CMD ["set-me-in-serverless.yaml"]
