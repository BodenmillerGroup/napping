# napping

![PyPI](https://img.shields.io/pypi/v/napping)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/napping)
![PyPI - License](https://img.shields.io/pypi/l/napping)
![GitHub issues](https://img.shields.io/github/issues/BodenmillerGroup/napping)
![GitHub pull requests](https://img.shields.io/github/issues-pr/BodenmillerGroup/napping)

Control point mapping and coordination transformation using napari

## Requirements

This package requires Python 3.7 or newer.

Python package dependencies are listed in [requirements.txt](https://github.com/BodenmillerGroup/napping/blob/main/requirements.txt).

Using virtual environments is strongly recommended.

## Installation

Install napping and its dependencies with:

    pip install napping

### Environment setup example: mapping IMC and slidescanner images

As napari is under active development, the use of virtual environments is strongly encouraged. For example, to set up an environment for aligning Imaging Mass Cytometry (IMC, .mcd/.txt) and bright-field/immunofluorescence slidescanner (.czi) images:

    conda create -n napping python
    conda activate napping
    pip install napping napari-imc napari-czifile2

Afterwards, napping can be started from inside the environment:

    napping

## Usage

Use `napping` for control point mapping and coordinate transformation

## Authors

Created and maintained by Jonas Windhager [jonas.windhager@uzh.ch](mailto:jonas.windhager@uzh.ch)

## Contributing

[Contributing](https://github.com/BodenmillerGroup/napping/blob/main/CONTRIBUTING.md)

## Changelog

[Changelog](https://github.com/BodenmillerGroup/napping/blob/main/CHANGELOG.md)

## License

[MIT](https://github.com/BodenmillerGroup/napping/blob/main/LICENSE.md)
