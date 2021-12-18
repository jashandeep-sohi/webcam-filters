FROM nixos/nix

RUN nix-channel --add https://nixos.org/channels/nixpkgs-unstable nixpkgs
RUN nix-channel --update

ARG tag_ver=v0.3.0
RUN nix-env --install --file https://github.com/jashandeep-sohi/webcam-filters/archive/refs/tags/${tag_ver}.tar.gz

COPY start.sh .

CMD ["/bin/sh","start.sh"]

