# Define the image name for Docker
IMAGE_NAME = $(shell cat .env | grep IMAGE_NAME | cut -d '=' -f 2)

# Define the tag for Docker
TAG = $(shell cat .env | grep TAG | cut -d '=' -f 2)

all: release-ui

release-ui: build-ui push-ui

# This is a Makefile target named 'build'
build-ui:
	docker buildx build --platform linux/amd64 --tag $(IMAGE_NAME):$(TAG)-ui -f docker/Dockerfile-ui .
	
# This is a Makefile target named 'push'
push-ui:
	docker push $(IMAGE_NAME):$(TAG)-ui
	