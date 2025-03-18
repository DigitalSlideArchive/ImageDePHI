# ImageDePHI Demo

This walkthrough will guide you through using the ImageDePHI program.

## Getting the demo data

In order to get the demo data, you will need to have installed ImageDePHI and run the following command:

```bash
imagedephi demo-data
```

This will create a new directory in the location it is run called `demo_files` and download several whole slide images into that directory. These images contain fake PHI, which we will redact with ImageDePHI.

## Redacting with the Graphical User Interface (GUI)
ImageDePHI allows redaction of whole slide images through either a graphical user interface, accessible through a web browser, or a command line interface. First, let's take a look at the redaction workflow using the graphical user interface.

#### 1. Starting the program
In order to start the program, install ImageDePHI and run:

```bash
imagedephi gui
```

This will start the program, which will be accessible at a random port, and open up a browser at the correct address.

By default, this command will select a random port to serve the application from. You can specify a port if you'd like by using the `--port` flag, e.g:

```bash
imagedephi gui --port 8888
```

#### 2. Looking at the UI
If your browser is not already open to ImageDePHI, open up your browser and go to `127.0.0.1:<port>` where `<port>` is either the random port picked by the command above or the number you supplied to the `--port` flag if you used that option to start the server.

![Initial ImageDePHI UI](./images/initial_ui.png)

You should be greeted by the initial UI screen. On the left hand side there are several options for specifying which files should be redacted and how they should be redacted. We will go over each step individually.

#### 3. Select Files to be Redacted

The first thing you'll need to do is select files for redaction.

![Button to open input directory browser](./images/step_1_input_directory_open_browser.png)
Click the button in Step 1 to open up a file browser.

![Input directory browswer](./images/step_1_input_directory_select_directory.png)
Navigate your computer's file system until you come to the directory where you downloaded your demo files, then click "Select."

#### 4. Select Output Destination

Next, select a location for redacted images. ImageDePHI does not modify your original images. Instead, it creates new, redacted images saved into the location selected here.

![Output directory selector](./images/step_2_output_directory_select_directory.png)
For this demo, select the directory that is the parent of your `demo_files/` directory. A new directory will be created at this location for the redacted images.

#### 5. Preview Redaction Changes

After selecting your input directory, you will see a table previewing the redaction that is about to happen. For each file in the input directory, you'll see a row containing the file name, a thumbnail, the redaction status, and the metadata tags.

Looking at the metadata tags, you'll see that, for example, the "Date" tag is red with strikethrough. This indicates that this field will be removed and not present in the redacted output file. Scrolling over, you'll see tags like "AppMag" and "BitsPerSample" have no special styling, indicating that they will be included in the output file.

Most importantly, you'll see that there's an issue in the "Redaction Status" column for the image "SEER_Mouse_1_17158543_demo.svs". If you hover over the red icon you'll see the message "1 tag(s) missing redaction rules." Below that you'll see "55500: 55500," indicating that this image contains a metadata tag with the number "55500" that ImageDePHI doesn't know how to redact.

![Image grid showing an error](./images/image_grid_errors_ui.png)

#### 6. Creating a Custom Rule Set

The base rule set provided by ImageDePHI is used every time images are redacted. User-defined rule sets can be used to supplement or modify the behavior defined by the base rules.

The base rule set does not contain a rule for tag `55500`, so in order to redact the demo images, the program will need to be supplied a ruleset that knows what to do with tag `55500`.

Let's create that ruleset now. Create a new file called `custom_rules.yaml` and add the following:

```yaml
---
name: Custom Rules
description: Custom ruleset used for the ImageDePHI demo.
svs:
    metadata:
        '55500':
            action: delete
```

If you'd like to know the default behavior of ImageDePHI, take a look at the [base rules](../imagedephi/base_rules.yaml).

#### 7. Using Your Custom Ruleset

Now that you've created a rule to complete redaction of the demo images, let's use that rule set.

Click the folder icon in Step 3 (Rulesets) to open the file navigator.

![Custom ruleset file navigator](./images/step_3_ruleset_select_ruleset.png)

Navigate to the custom rule set you created in step 6 and select it. The rule set you select in this step will be composed with the base rule set provided by ImageDePHI. If a tag appears in both the base rules and the custom rule set, the custom rule will be applied instead of the base rule.

The table should update to reflect that the program now knows how to redact tag `55500`, and each image should have a green checkmark icon in the "Redaction Status" column.

![Image grid showing no errors](./images/image_grid_success_ui.png)

#### 8. Redact the Demo Images

All that's left to do is click redact! Click the button that says "De-PHI Images." You'll see a progress bar that indicates how much time is left in the redaction process.

![Image redaction indicated by a progress bar](./images/redaction_progress_ui.png)

Once that succeeds, you'll see a toast notification at the bottom of the screen indicating that the images have been redacted successfully.

![Redaction complete notification](./images/redaction_complete_ui.png)

You'll find a new directory in the location you selected as your output directory. This new directory will have a name starting with "Redacted_" and ending with a timestamp of when you started redacting images. It will contain redacted images. Adjacent to that directory will be a manifest file mapping input file names to output file names. If there were any issues during redaction, those would be reported in the manifest file as well.

## Using the CLI

If you would prefer to use the CLI to redact the images, follow this section to walk through the same example using that tool instead of the UI. Make sure the follow the instructions at the top of this guide to get the demo data.

#### 1. Use the `plan` command

The `plan` command is one way to determine if the files you want to redact are able to be redacted. If not, the output of the `plan` command will help you discover what you'll need to do in order to redact your images. After obtaining the test data, run the following command:

```bash
imagedephi plan demo_files
```

You'll see in the output of that command that one of the files cannot be redacted. In order to find out why, you can run:

```bash
imagedephi plan demo_files/SEER_Mouse_1_17158543_demo.svs
```

Running the `plan` command on a single image will provide a detailed report of exactly how that particular image is redacted. To see this level of detail for all images in a directory, use the `-v` (verbose) option.

The ouput of the `plan` command for that particular image reveals that it contains a metadata item with tag `55500` with no corresponding rule.

#### 2. Create an override rule set

In order to redact the demo images, we'll need to give the program a rule it can use for tag `55500`. The mechanism we can use to do this is with an override, or custom, rule set.

ImageDePHI comes with a base set of rules that covers most commonly seen metadata tags for SVS and DICOM images. If your images contain metadata not covered by the base rules, you'll need a custom rule set.

For this demo, create a file called `custom_rules.yaml` add add the following:

```yaml
---
name: Custom Rules
description: Custom ruleset used for the ImageDePHI demo.
svs:
    metadata:
        '55500':
            action: delete
```

We now have a ruleset to supplement the base rules and enable redaction of the demo images.

#### 4. Use the `plan` command with the override rule set

First, let's verify that our custom rule set works as intended. Run the following command:

```bash
imagedephi plan -R custom_rules.yaml demo_files
```

Note the message "3 images able to be redacted" in the output. This means all of the demo files can now be redacted.

#### 5. Use the `run` command to redact the images

The `run` command is very similar to `plan`, except it also needs to be told where to save the redacted files. This is done using the `-o` option. Run the following:

```bash
mkdir ./output_files
imagedephi run -R custom_rules.yaml -o ./output_files demo_files
```

After that command finishes, you'll see a new directory in `./output_files` called `Redacted_<timestamp>` containing the redacted files.

You'll also see a file next to that directory called `Redacted_<timestamp>_manifest.csv`. This will contain a mapping of input file names to output file names, as well as any errors that may have occurred during redaction.

### Using a command file in the CLI
In some instances you may want to pass a command file to the CLI. For example you may have an long list of input files that would be cumbersome to type in a terminal.

For this demo create a file called `command_file.yaml` and add the following:

```bash
---
command: plan
input_path:
  - "demo_files"
output_dir: ~/redacted_images
```
Now run the following:

```bash
imagedephi plan -c command_file.yaml
```
This option is supported by both the `plan` and `run` commands. Any option that can be added to these commands can also be added to the command file.

```bash
---
command: run
input_paths:
  - "demo_files"
output_dir: /redacted_images
recursive: True
```
**Please Note** The command file is meant to supplement the command given in the terminal. Any option supplied in the terminal takes priority.

Additionally you can supply an unformatted yaml or text file. This will be treated as a list of  `input_files`.


## Next Steps

For more information about the ImageDePHI rules system, be sure to check out the [documention](../README.md).

## Demo Data Citation
‘NCI SRP Mouse Tissue Whole Slide Images with Fake PHI/PII' data set, Version 1.0. Generated: December 29, 2021; Scanner: Leica Microsystems, Aperio AT2; Provided by: The National Cancer Institute (NCI) Surveillance Research Program (SRP).
