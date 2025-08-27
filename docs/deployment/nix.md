---
title: Nix & devenv support
author: mfocko
---

# Nix & devenv support

:::tip tl;dr

Ideal for atomic linux distributions and macOS setup.

There's one file (`devenv.nix`) containing everything that's needed to set up an
environment for the project (`packit/deployment` in this case). All tools and
deps are kept only for this project, i.e., they don't pollute the host system.

Since Nix and devenv.sh support pinning, it is also possible to acquire
a reproducible environment.

[`direnv`](https://devenv.sh/automatic-shell-activation/) makes sure the development environment is set up upon entering the repo.

:::

## What is [Nix](https://nixos.org/)?

From the homepage:

> Nix is a tool that takes a unique approach to package management and system
> configuration. Learn how to make reproducible, declarative and reliable systems.

Basically you have global environment and smaller `nix-shell`s that are usually
tied to git repos (or any other directory). You aim for as small base environment
as possible, i.e., you don't want to keep all utilities / dependencies everywhere.

One benefit, in comparison to containers, lies in the fact that the packages are
defined by hash, name and version which allows them to be stored in a global
location (usually `/nix`). Including packages in “environments” is done by
adjusting `$PATH` (and related) variable.

## What is [devenv.sh](https://devenv.sh/)?

Builds on top of the _Nix_ and _nix-shell_ themselves. Is a bit more robust,
cause it also allows specifying environment variables, defining tasks, services,
and processes. For example it allows you to automatically spin up `nginx` or
`postgres` server once you enter the repo.

## Getting started

Feel free to follow the [devenv.sh' “Getting Started”](https://devenv.sh/getting-started/).

1. You need to have _Nix_ set up. (single-user / non-daemon setup is recommended
   for users with SELinux enabled)
2. Install the _devenv.sh_ itself.
3. Have _direnv_ present (since it automatically loads the environment upon
   entering the directory with _devenv.sh_).

## Caveats

Bitwarden CLI is currently broken on macOS, therefore it's not included in the
devenv.sh' config.

There's also a need to set `ANSIBLE_PYTHON` as _devenv.sh_ creates a venv with
the dependencies that need to be installed manually (such as `kubernetes`) for
the playbooks to work properly.
