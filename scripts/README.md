# Updating the changelog

In order to simplify the process of Github releases (mainly in packit and ogr), we generate the changelog semi-automatically. The script `changelog.py` goes through the merge commits starting from the specified ref (typically the tag of the last release) and parses the changelog entry from our PR template.

In order to generate the changelog

1. [OPTIONAL] Add the changelog script to your `PATH` to simplify its usage, e.g. by adding `export PATH="~/repos/deployment/scripts:$PATH"` to your `.bashrc` or `.zshrc`.
2. Call the script:

```
# get changes in the current directory since the last release
$ changelog.py

# specify a ref explicitly
$ changelog.py 0.34.0

# use a different git-repo
$ changelog.py --git-repo ~/repos/packit 0.34.0

# refer to the help message for more information
$ changelog.py --help

```

3. Manually adjust the output and add it to `CHANGELOG.md` with a header.
