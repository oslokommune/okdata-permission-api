FROM public.ecr.aws/lambda/python:3.11

COPY dataplatform_keycloak ${LAMBDA_TASK_ROOT}/dataplatform_keycloak
COPY jobs ${LAMBDA_TASK_ROOT}/jobs
COPY models ${LAMBDA_TASK_ROOT}/models
COPY resources ${LAMBDA_TASK_ROOT}/resources
COPY app.py ${LAMBDA_TASK_ROOT}
COPY handler.py ${LAMBDA_TASK_ROOT}
COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install --no-cache-dir -r requirements.txt

RUN yum install shadow-utils -y
RUN /sbin/groupadd -r app
RUN /sbin/useradd -r -g app app
RUN chown -R app:app ${LAMBDA_TASK_ROOT}
USER app

CMD ["set-me-in-serverless.yaml"]
