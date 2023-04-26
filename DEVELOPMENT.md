# ImageDePHI

This project has been funded in whole or in part with Federal funds from the National Cancer Institute, National Institutes of Health, Department of Health and Human Services, under Contract No. 75N91022C00033

## To Run as a CLI

`pip install -r requirements.txt`

`python imagedephi.py <directory of input images> <directory to store redacted images>`


## Development

### Web GUI Development
While developing the web GUI, it may be useful to maintain a running web server
which will auto-reload code changes:
```bash
hypercorn --reload imagedephi.gui:app
```
