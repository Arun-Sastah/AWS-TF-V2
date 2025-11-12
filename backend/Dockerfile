FROM hashicorp/terraform:1.8.0
RUN apk add --no-cache python3 py3-pip
COPY . /app
WORKDIR /app
RUN pip install fastapi uvicorn boto3
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
