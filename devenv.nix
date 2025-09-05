{ pkgs, lib, config, inputs, ... }:

{
  packages = [
    pkgs.openshift

    pkgs.ansible
    pkgs.ansible-navigator

    # Needed for renewal of TLS certificates
    pkgs.certbot
  ];

  languages.python = {
    enable = true;

    venv = {
      enable = true;
      requirements = ''
        # Needed for k8s ansible module
        kubernetes

        # Needed for changelog script
        click
        GitPython
        ogr

        # Needed for move-stable script
        copr
      '';
    };
  };
}
