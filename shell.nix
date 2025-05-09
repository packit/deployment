with import <nixpkgs> {};

stdenv.mkDerivation {
  name = "packit/deployment";
  buildInputs = [
    pkgs.openshift

    pkgs.ansible
    pkgs.ansible-navigator

    # Needed for k8s ansible module
    pkgs.python312Packages.kubernetes
  ];
}
