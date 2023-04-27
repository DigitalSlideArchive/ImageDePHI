## Development
* create and activate a virtualenv: [venv docs](https://docs.python.org/3/library/venv.html)
* run :
    ```bash
    pip install -e .
    ```
* execute with:
    ```bash
    imagedephi
    ```

## Web GUI Development
While developing the web GUI, it may be useful to maintain a running web server
which will auto-reload code changes:
```bash
hypercorn --reload imagedephi.gui:app
```

## Testing
Install tox:
```bash
pip install tox
```
Run all tox environments
```bash
tox
```
Format all code to comply to linting checks
```bash
tox -e format
```
