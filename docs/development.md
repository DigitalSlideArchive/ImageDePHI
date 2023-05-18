# Development

## Installation
To install for development:
* [Create and activate a Python virtual environment](https://docs.python.org/3/library/venv.html).
* Install for local development:
    ```bash
    pip install -e .
    ```
* Install [Tox](https://tox.wiki/) to run development tasks:
    ```bash
    pip install tox
    ```

## Running the CLI
With the virtual environment active, run the CLI:
```bash
imagedephi
```

### Developing the Web GUI
While developing the web GUI, it may be useful to launch web server
that auto-reloads code changes and shows in-browser exception tracebacks:
```bash
DEBUG=1 hypercorn --reload imagedephi.gui:app
```

## Auto-format Code Changes:
To format all code to comply with style rules:
```bash
tox -e format
```

## Running Tests
To run all tests:
```bash
tox
```
