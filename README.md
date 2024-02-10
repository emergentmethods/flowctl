# flowctl

![GitLab Release (latest by SemVer)](https://img.shields.io/gitlab/v/release/emergentmethods/flowctl?style=flat-square)
![GitLab](https://img.shields.io/gitlab/license/emergentmethods/flowctl?style=flat-square)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/flowctl?style=flat-square)

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
