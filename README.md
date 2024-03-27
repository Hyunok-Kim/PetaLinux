# PetaLinux
PetaLinux CMD utils and Templates.

## PetaLinux Live Tool Setup
When PetaLinux Tool installed On Shared Location and want to update PetaLinux util scripts,
use the livetool_setup.sh script to use the PetaLinux Repo as local Tool.
This will map the Buildtools, trim-xsct and other dependencies as simbolic links from PetaLinux installed area.
```
./scripts/bash/livetool_setup.sh <PetaLinux Local/Shared Tool Path>
```

## Maintainers, Patches/Submissions, Community

Please open pull requests for any changes.

For more details follow the OE community patch submission guidelines, as described in:
https://www.openembedded.org/wiki/Commit_Patch_Message_Guidelines

> **Note:** When creating patches, please use below format. To follow best practice,
> if you have more than one patch use `--cover-letter` option while generating the
> patches. Edit the 0000-cover-letter.patch and change the title and top of the
> body as appropriate.

**Syntax:**
`git format-patch -s --subject-prefix="PETALINUX][<BRANCH_NAME>][PATCH" -1`

**Example:**
`git format-patch -s --subject-prefix="PETALINUX][xlnx_rel_v2024.1][PATCH" -1`

**Maintainers:**

	Varalaxmi Bingi <varalaxmi.bingi@amd.com>
	Raju Kumar Pothuraju <rajukumar.pothuraju@amd.com>
	Swagath Gadde <swagath.gadde@amd.com>
	Ashwini Lomate <ashwini.lomate@amd.com>
