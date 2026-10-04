# xngl

Publication maps of `xarray` data with PyNGL, with less boilerplate and full control.

## Install

PyNGL and PyNIO are not on PyPI. Install them from conda-forge first:

```bash
conda env create -f environment.yml      # or: conda install -c conda-forge pyngl pynio
conda activate xngl-dev
pip install -e .
```

xngl v1 needs Python 3.11 and numpy 1.x, because the conda-forge builds of PyNGL and PyNIO stop at these versions.
