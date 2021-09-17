{
  nixpkgs ? import (fetchTarball "https://github.com/NixOS/nixpkgs/archive/a3c4956cf9cb921d61b4a5c30df6ef1c07d2fae4.tar.gz") { },
  poetry2nix ? import (fetchTarball "https://github.com/jashandeep-sohi/poetry2nix/archive/3efdf3d0fced9f333fcc8a8970031305e9fdf0d2.tar.gz") { pkgs = nixpkgs; poetry = nixpkgs.poetry; },
}:
  poetry2nix.mkPoetryApplication {
    projectDir = ./.;
    python = nixpkgs.python3;
    preferWheels = true;

    overrides = poetry2nix.overrides.withDefaults (self: super: { cython = null; });

    # https://github.com/NixOS/nixpkgs/issues/56943
    strictDeps = false;

    nativeBuildInputs = [
      nixpkgs.wrapGAppsHook
      nixpkgs.gobject-introspection
    ];

    buildInputs = [
      nixpkgs.gst_all_1.gstreamer
      nixpkgs.gst_all_1.gst-plugins-base
      nixpkgs.gst_all_1.gst-plugins-good
    ];

    propagatedBuildInputs = [
      nixpkgs.python3.pkgs.gst-python
      nixpkgs.python3.pkgs.pygobject3
    ];

  }
