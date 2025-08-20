# README

## Docker build command

Step 0: Login to the ECR

```shell
aws ecr get-login-password --region ap-northeast-1 | docker login --username AWS --password-stdin [ecr-registry-url]
```

例；

```shell
aws ecr get-login-password --region ap-northeast-1 | docker login --username AWS --password-stdin 345804926022.dkr.ecr.ap-northeast-1.amazonaws.com
```

Step 1: Build container image

```shell
docker buildx build --platform linux/amd64 --provenance=false -t [container-name]
```

例；

```shell
docker buildx build --platform linux/amd64 --provenance=false -t iot-telemetry-lambda .
```

Step 2: Tag the built image

```shell
docker tag [container-name]:latest [ecr-registry-url]/[container-name]:latest
```

例：

```shell
docker tag iot-telemetry-lambda:latest 345804926022.dkr.ecr.ap-northeast-1.amazonaws.com/iot-telemetry-lambda:latest
```

Step 3: Push to ECR registry

```shell
docker push [ecr-registry-url]/[container-name]:latest
```

例：

```shell
docker push 345804926022.dkr.ecr.ap-northeast-1.amazonaws.com/iot-telemetry-lambda:latest
```

## Test code

Install `requests` package for Test API code

```shell
python3 -m venv venv
source venv/bin/activate
pip install requests

pip3 install -r requirements.txt
```