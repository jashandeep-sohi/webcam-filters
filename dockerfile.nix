{
  nixpkgs ? import ./nixpkgs.nix { },
  webcam-filters ? import ./default.nix { },
  imageName ? "webcam-filters",
  imageTag ? null,
}:

nixpkgs.dockerTools.streamLayeredImage {
  name = imageName;
  tag = imageTag;

  config = {
    Entrypoint = [
      "${webcam-filters}/bin/webcam-filters"
      "--input-dev" "/input-dev"
      "--output-dev" "/output-dev"
    ];
  };
}
