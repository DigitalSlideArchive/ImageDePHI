# Image DePHI Demo

This walkthrough will guide you through using the Image DePHI program.

## Getting the demo data

In order to get the demo data, you will need to have installed Image DePHI and run the following command:

```bash
imagedephi demo-data
```

This will create a new directory in the location it is run called `demo_files` and download several whole slide images into that directory. These images contain fake PHI, which we will redact with Image DePHI.

## Using the CLI

Here is one example of a workflow to redact images using only CLI commands.

#### 1. Use the `plan` command to see if there are any missing rules

```bash
imagedephi plan demo-data
```

#### 2. Create an override rule set

#### 3. Add the missing rule

#### 4. Use the `plan` command with the override rule set

#### 5. Use the `run` command to redact the images

#### 6. Inspect the manifest

#### 7. Skip renaming/use a custom name


