# ImageDePHI
ImageDePHI is an application to redact personal data (PHI) from whole slide images (WSIs).

> This project has been funded in whole or in part with Federal funds from the National Cancer Institute, National Institutes of Health, Department of Health and Human Services, under Contract No. 75N91022C00033

## Installation
* Download the [latest ImageDePHI release](https://github.com/DigitalSlideArchive/ImageDePHI/releases/latest).

* Unzip the downloaded file, which will extract the executable named `imagedephi` (or `imagedephi.exe` on Windows).

* Please note that on Linux, only Ubuntu 20.04+ is supported.

## Usage
From a command line, execute the application to get full usage help.

Alternatively **on Windows only**, directly open `imagdephi.exe` in Windows Explorer to launch the ImageDePHI GUI.

If running on macOS, you may need to [add the executable to the list of trusted software](https://support.apple.com/guide/mac-help/apple-cant-check-app-for-malicious-software-mchleab3a043/mac) to launch ImageDePHI in the same way you would any other registered app.

# Rules
Image redaction is determined by a set of rules. By default, the base set of rules are used. These rules are provided by the `imagedephi` package and can be found [here](https://github.com/DigitalSlideArchive/ImageDePHI/blob/main/imagedephi/base_rules.yaml).

## Rule Application
All runs of `imagedephi` use the provided base set of rules as a foundation. End users can use the ruleset framework to build custom rulesets that handle additional or custom metadata not covered by the base rules, or override the behavior of the base rule set.

Override rule sets can be specified by using the `-R my_ruleset.yaml` or `--override-rules my_ruleset.yaml` option. This option is available for both the `imagedephi run` and `imagedephi plan` commands. Override rules sets are not provided by `imagedephi`, and must de defined by the end user.

When `imagedephi` determines the steps to redact a file, it checks each piece of metadata in the file. For each piece of metadata found this way, it will first consult the override rule set, if present, for an applicable rule. If the override rule set does not contain a rule for that piece of metadata, the program will check the base ruleset.

If neither the override rule set or base rule set cover a piece of metadata, redaction will fail, and the program will list the metadata that it could not redact. There is no default behavior for unknown metadata.

### Redaction Profiles

#### Strict Redaction
For whole slide image formats based on the tiff standard, `imagedephi` allows a strict type of redaction. Using the `--profile strict` option when calling `imagedephi` from the CLI will use this mode. In this mode, only tags strictly required by the tiff standard will remain, and all other metadata will be stripped from the images. For a full list of metadata tags that will remain after strict redaction, see the [minimum rules file](https://github.com/DigitalSlideArchive/ImageDePHI/blob/main/imagedephi/minimum_rules.yaml).

#### Fuzzing Dates and Times
Using the `--profile dates` option will replace dates, times, datetimes, and UTC offsets with values that semantically represent those things but with less precison than the original value. Dates will preserve the year, but the month and day will be set to January 1st. Times will be set to midnight and UTC offsets to +0000. Rules for this profile can be found in [modify_dates_rules.yaml](https://github.com/DigitalSlideArchive/ImageDePHI/blob/main/imagedephi/modify_dates_rules.yaml). For DICOM images, the [Attribute Confidentiality Profiles](https://dicom.nema.org/dicom/2013/output/chtml/part15/chapter_E.html) were used to determine which tags should be modified according to this profile.


## Ruleset Format Overview
In order to read the base rules and build your own custom rule sets, it is important to understand the format in which rulesets are specified. Rulesets are defined by `.yaml` files (one ruleset per file), and are a dictionary with the following top-level tags: `name`, `description`, `output_file_name`, `tiff`, `svs`, and `dicom`.

### Generic Properties
The following three properties belong to the rulesets themselves, and don't influence redaction behavior.

#### `name`
Provide a name for a ruleset. This is used by the `imagedephi plan` command to specify which ruleset is being used to redact a particular piece of metadata.

#### `description`
You can add a description to your custom rulesets. This is not used by the program, but can be helpful to communicate what cases your custom rulesets are designed for.

#### `output_file_name`
Specify how the output files should be named here. The base ruleset contains the value `study_slide`. In this case, if the input slides are named: `john_smith_lung.svs` and `john_smith_pancreas.svs`, the redacted output images will be named `study_slide_1.svs` and `study_slide_2.svs`.

### Other Top-level Properties

#### `strict`
The `strict` property of rulesets is used to denote that ALL unspecified tags should be deleted. This is supported for `tiff` and `svs` files. An example of using the strict flag can be seen in the `minimum_rules.yaml` rule set.

### File Format Rules
Redaction behavior is specified per file type. Currently pure `tiff` files, Aperio (`.svs`), and DICOM files are supported. Each image type has its own groups of data that can be redacted. For example, Aperio images have `tiff` metadata, certain associated images, and additional metadata specified in the `ImageDescription` tag. `svs` rulesets take the following shape:


```yaml
svs:
    associated_images:
        ...
    metadata:
        ...
    image_description:
        ...
```

Each group is a dictionary whose keys represent a way to identify a specific piece of metadata or specific associated image, and whose values are dictionaries that define redaction behavior. Each entry (key-value pair) in the dictionary is a "rule." Take the following `associated_image` rule from the base ruleset

```yaml
svs:
    ...
    associated_images:
        label:
            action: replace
            replace_with: blank_image
    ...
```

This describes how `imagedephi` handles `label` images for Aperio files by default. Since label images frequently contain PHI, but are required by the Aperio (.svs) format, they are replaced with a black square of the same size.

#### Image Rules

Image rules take the following form:

```yaml
<image_key>:
    action:
```

Where `image_key` identifies a particular associated image. For a catch-all rule, use the key `default`.

Image rules can have the following actions:

* `replace`: Replace an image with another. If specified, a value for `replace_with` must also be provided
* `keep`: Does nothing. The associated image matching this key will be included in the output file
* `delete`: The image will not be included in the output file

For image rules, the only supported value of `replace_with` is `blank_image`.

#### Metadata Rules

Metadata rules take the following form:

```yaml
<metadata_key>:
    action:
```

Where `metadata_key` identifies a piece of metadata. Possible values for this key depend on the type of metadata being redacted. For example, rules listed under

```yaml
tiff:
    metadata:
```
have `metadata_keys` for particular tiff tags (e.g. `ImageDescription`, `ImageWidth`).

Available actions for metadata rules are:

* `delete`: the metadata will not appear in the output file
* `keep`: the metadata will appear unchanged in the output file
* `replace`: replace the metadata with a specified value. If this is the `action`, additional fields are required.
* `check_type`: This will either keep the metadata if the type matches or delete the metadata if the type does not match. Requires additional fields
* `modify_date`: This will fuzz dates, times, datetimes, and time zone offsets. See the "Profiles" section for more details.

##### `replace` rules
Require the additional property `replace_with`. The value specified by the `replace_with` key will be used to override the metadata in the output image.

##### `check_type` rules
Use the additional properties:
* `expected_type`: one of `integer`, `number`, `text`, `rational`
* `expected_count` (optional): if the piece of metadata can contain multiple values, specify how many are expected using this property. Defaults to `1`. If the `expected_type` is `rational`, this should be the expected number of rationals. That is, an `expected_count` of 1 would match with 2 integer values in the metadata.

### Supported Formats
Currently, `imagedephi` supports redaction of the following types of files:
* TIFF
* Aperio (a tiff-like format, typically uses the extension `.svs`)
* DICOM

#### Tiff
Tiff rules have the following shape:

```yaml
tiff:
    associated_images:
        ...
    metadata:
        ...
```

The keys for the `metadata` rules are the names of tiff tags defined by the tiff standard.

#### Aperio
Aperio format rules have the following shape:

```yaml
svs:
    associated_images:
        ...
    metadata:
        ...
    image_description:
        ...
```

The keys for the `metadata` rules are the names of tiff tags defined by the tiff standard. Names are case insensitive and common variations are accepted, e.g. `GrayResponseUnit` and `GreyResponseUnit` are both accepted

For Aperio files, additional metadata is stored as key-value pairs in the `ImageDescription` tag. See more information about this [here](https://openslide.org/formats/aperio/). Each key in the `image_description` section is a key found in this `ImageDescription` string.

#### DICOM
DICOM format rules are much the same:

```yaml
dicom:
    associated_images:
        ...
    delete_custom_metadata: ...
    metadata:
        ...
```

Note that here there is an eplicit format-level setting for dealing with custom metadata. Any tag with an odd group number is custom metadata. If not specified, this value default to `True`. Tag-level rules will override this behavior.

Additionally, DICOM redaction supports additional redaction operations.

* `empty`: Replace the tag's value with `None`
* `replace_dummy`: Replace the tag's value with a dummy value, which is dependant on the original value type. For example, if the tag's value is a string, the dummy value is the empty string. If the tag's value is an integer, the dummy value is 0.
* `replace_uid`: If the tag's value is a UID, it will be replaced with a randomly generated UID of the form `"2.25.<uuid>"` where `<uuid>` is a UUID generated a run time. The new custom UID is stored by Image DePHI and used to replace other UIDs that share the same initial value. This way, if a UID is used in different tags within an image, they all get the same replacement value.
