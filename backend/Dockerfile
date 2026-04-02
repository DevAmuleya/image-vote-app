# AWS Lambda base image — Python 3.12 on Amazon Linux 2023 (x86_64)
# Lambda Runtime Interface Client (RIC) is already bundled in this base image.
FROM public.ecr.aws/lambda/python:3.12

# Install dependencies first — this layer is cached unless requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Lambda handler: file `lambda_handler.py`, function `handler`
CMD ["lambda_handler.handler"]
