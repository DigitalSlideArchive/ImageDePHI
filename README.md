# ImageDePHI
ImageDePHI is an application that can be used to redact PHI from whole slide images.


# Installation
ImageDePHI is under active development and as such the best way to test the latest features is to download the most current artifact.


## [ImageDePHI Artifacts](https://github.com/DigitalSlideArchive/ImageDePHI/actions/workflows/ci.yml?query=branch%3Amain)

Select the most recent run:
![ci run](imagedephi/assets/ci_run.png)

Then select the appropriate artifact for your OS:
![artifacts](imagedephi/assets/artifacts_list.png)

# Usage
## CLI:
Open a terminal and navigate to the directory that where the artifact was downloaded.

run:
```
./imagedephi
```
to get a list of cli options

```
Usage: imagedephi [OPTIONS] COMMAND [ARGS]...

  Redact microscopy whole slide images.

Options:
  -r, --override-rules FILENAME  Specify user-defined rules to override
                                 defaults
  --help                         Show this message and exit.

Commands:
  gui   Run a web-based GUI.
  plan  Print the redaction plan for a given image and rules.
  run   Redact images in a folder according to given rule sets.
```

To redact a set of images supply the directory of the images to be processed and [optionally] an output directory to deposit the redacted images:
```
imagedephi run [path/to/images] [optional/output/path]
```

## GUI
Alternatively you can use the gui to navigate to the desired directories:
```
imagedephi gui
```
### **Note**: Windows users can double click the imagdephi executable icon to launch the gui outside of the terminal workflow
