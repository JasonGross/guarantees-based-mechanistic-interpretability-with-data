# Guarantees-Based Mechanistic Interpretability

This is the codebase for the [_Guarantees-Based Mechanistic Interpretability_](https://www.cambridgeaisafety.org/mars/jason-gross) MARS stream.
Successor to https://github.com/JasonGross/neural-net-coq-interp.

## Setup

The code can be run under any environment with Python 3.9 and above.

We use [poetry](https://python-poetry.org) for dependency management, which can be installed following the instructions [here](https://python-poetry.org/docs/#installation).

To build a virtual environment with the required packages, simply run

```bash
poetry config virtualenvs.in-project true
poetry install
```

Notes
- On some systems you may need to set the environment variable `PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring` to avoid keyring-based errors.
- The first line tells poetry to create the virtual environment in the project directory, which allows VS Code to find the virtual environment.

## Running notebooks

To open a Jupyter notebook, run

```bash
poetry run jupyter lab
```

If this doesn't work (e.g. you have multiple Jupyter kernels already installed on your system), you may need to make a new kernel for this project:

```bash
poetry run python -m ipykernel install --user --name=gbmi
```

## Training models

Models for existing experiments can be trained by running e.g.

```bash
poetry run python -m gbmi.exp_max_of_n.train
```

or by running e.g.

```python
from gbmi.exp_max_of_n.train import MAX_OF_10_CONFIG
from gbmi.model import train_or_load_model

rundata, model = train_or_load_model(MAX_OF_10_CONFIG)
```

from a Jupyter notebook.

This function will attempt to pull a trained model with the specified config from Weights and Biases; if such a model does not exist, it will train the relevant model and save the weights to Weights and Biases.

## Adding new experiments

The convention for this codebase is to store experiment-specific code in an `exp_[NAME]/` folder, with
- `exp_[NAME]/analysis.py` storing functions for visualisation / interpretability
- `exp_[NAME]/verification.py` storing functions for verification
- `exp_[NAME]/train.py` storing training / dataset code

See the `exp_template` directory for more details.

## Adding dependencies

To add new dependencies, run `poetry add my-package`.

## Code Style

We use black to format our code.
To set up the pre-commit hooks that enforce code formatting, run

```bash
make pre-commit-install
```


## Tests

This codebase advocates for [expect tests](https://blog.janestreet.com/the-joy-of-expect-tests) in machine learning, and as such uses @ezyang's [expecttest](https://github.com/ezyang/expecttest) library for unit and regression tests.

[TODO: add tests?]
