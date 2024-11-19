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

### Development
#### Requirements

```bash
python ^3.11
node ^20
```

#### Initial Install
This project uses yarn modern. As such you'll need to enable corepack to detect the correct yarn version:

```bash
cd /client
corepack enable
```


#### Developing the Web GUI
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
