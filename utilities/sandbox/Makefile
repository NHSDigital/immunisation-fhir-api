project_name = immunisation-fhir-api

build: spec
	docker build -t $(project_name) -f Dockerfile .

run: build
	docker run --rm -it -p 9000:9000 --name $(project_name) $(project_name)

spec:
	make -C .. publish

.PHONY: build run spec
