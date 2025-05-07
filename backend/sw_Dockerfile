# Use AWS-provided Python base image
FROM public.ecr.aws/lambda/python:3.10
# Copy function code
COPY search_imms_handler.py ${LAMBDA_TASK_ROOT}

# Set the CMD to your function's handler
CMD ["search_imms_handler.search_imms_handler"]