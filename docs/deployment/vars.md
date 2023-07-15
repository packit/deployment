---
title: Variable files
---

[template.yml](https://github.com/packit/deployment/blob/main/vars/template.yml) is a general variable file template.

There are also `{service}/{deployment}_template.yml` files,
where

- `{service}` is either `packit` or `stream`
- `{deployment}` is one of `prod`, `stg` or `dev`

You have to copy `{service}/{deployment}_template.yml` to `{service}/{deployment}.yml`
depending on what service and environment you want to deploy to
and fill in missing values.
The `{service}/{deployment}.yml` files are `.gitignore`d so you can't
push them to the git repo by mistake.

The Ansible playbooks then include one of the variable files depending on the
value of `SERVICE` (optional, defaults to `packit`) and `DEPLOYMENT`
environment variables and processes all the templates with
variables defined in the file.
