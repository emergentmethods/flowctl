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
docker run -ti --rm -v "$(pwd)":/data --network host ghcr.io/emergentmethods/flowctl:latest --help
```

If you'd like, you can set an alias for the docker command to make it easier to use. For example, in bash you can add the following to your `.bashrc` or `.bash_profile` file:

```bash
alias flowctl='docker run -ti --rm -v "$(pwd)":/data --network host ghcr.io/emergentmethods/flowctl:latest'
```

Then you can use `flowctl` as if it were installed on your system.

```bash
flowctl --help
```

## Documentation
For documentation on how to use `flowctl`, please see the [CLI Reference](cli.md).
