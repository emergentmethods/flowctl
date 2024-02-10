# flowctl

The CLI tool for managing and operating flowdapt.


## Installation

For normal use users can install flowctl via pip:
```bash
pip install flowctl
```

Or you can use the docker images provided:
```bash
docker run -ti --rm -d -v "$(pwd)":/app --network host ghcr.io/emergentmethods/flowctl:latest --server http://my-flowdapt-server:8080 get workflows
```

## Documentation
For documentation on how to use `flowctl`, please see the [CLI Reference](cli.md).
