## Variable files

[template.yml](./template.yml) is a general variable file template.

There are also `{deployment}_template.yml` files,
where `{deployment}` is one of `prod`, `stg` or `dev`.
You have to copy those to `{deployment}.yml`
depending on what environment you want to deploy to
and fill in missing values.
The `{deployment}.yml` files are `.gitignore`d so you can't
push them to the git repo by mistake.

The Ansible playbook then includes one of the variable files depending on the
value of DEPLOYMENT environment variable and processes all the templates with
variables defined in the file.
