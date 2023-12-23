{
  description = "Add filters (background blur, etc) to your webcam on Linux.";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-parts.url = "github:hercules-ci/flake-parts";
    poetry2nix.url = "github:nix-community/poetry2nix";
    nix2container.url = "github:nlewo/nix2container";

    poetry2nix.inputs.nixpkgs.follows = "nixpkgs";
    nix2container.inputs.nixpkgs.follows = "nixpkgs";
  };

  nixConfig = {
    extra-substituters = [
      "https://sohi.cachix.org"
    ];

    extra-trusted-public-keys = [
      "sohi.cachix.org-1:kc+1e94Jt8SW31aCSNFUKYeJDDmMd5PhVXnJgE86xls="
    ];
  };

  outputs = inputs@{ flake-parts, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } {
      systems = [ "x86_64-linux" "aarch64-linux" "aarch64-darwin" "x86_64-darwin" ];
      perSystem = { pkgs, config, inputs', ... }:
      let
        poetry2nix = inputs.poetry2nix.lib.mkPoetry2Nix { inherit pkgs; };
      in
      {
        devShells.default = pkgs.mkShell {
          inputsFrom = [ config.packages.default ];
          packages = [ pkgs.poetry ];
        };

        packages.container = with inputs'.nix2container.packages; nix2container.buildImage {
          name = "webcam-filter";
          tag = "latest";
          config = {
            entrypoint = [
              "${config.packages.default}/bin/webcam-filters"
              "--input-dev" "/input-dev"
              "--output-dev" "/output-dev"
            ];
          };
          layers = [
            (nix2container.buildLayer { deps = [ config.packages.default.dependencyEnv ]; })
          ];
        };

        packages.default = poetry2nix.mkPoetryApplication {
          projectDir = inputs.self;
          python = pkgs.python311;
          preferWheels = true;

          overrides = poetry2nix.overrides.withDefaults (self: super: {
            cython = null;
          });

          nativeBuildInputs = [
            pkgs.wrapGAppsHook
            pkgs.gobject-introspection
          ];

          propagatedBuildInputs = [
            pkgs.gst_all_1.gstreamer
            pkgs.gst_all_1.gst-plugins-base
            pkgs.gst_all_1.gst-plugins-good
            pkgs.gst_all_1.gst-vaapi
            pkgs.python311.pkgs.gst-python
            pkgs.python311.pkgs.pygobject3
          ];
        };
      };
    };
}
