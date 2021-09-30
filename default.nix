{
  nixpkgs ? import (fetchTarball "https://github.com/NixOS/nixpkgs/archive/a3c4956cf9cb921d61b4a5c30df6ef1c07d2fae4.tar.gz") { },
  poetry2nix ? import (fetchTarball "https://github.com/nix-community/poetry2nix/archive/refs/tags/1.20.0.tar.gz") { pkgs = nixpkgs; poetry = nixpkgs.poetry; },
}:
  poetry2nix.mkPoetryApplication {
    projectDir = ./.;
    python = nixpkgs.python3;
    preferWheels = true;

    overrides = poetry2nix.overrides.withDefaults (self: super: {
      cython = null;

      zipp = super.zipp.overridePythonAttrs (old: { prePatch = null; });
    });

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
      nixpkgs.gst_all_1.gst-vaapi
    ];

    propagatedBuildInputs = [
      nixpkgs.python3.pkgs.gst-python
      nixpkgs.python3.pkgs.pygobject3
    ];

  }
