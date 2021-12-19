FROM nixos/nix

# setup certs and cachix cache
RUN mkdir -p /etc/ssl/certs && \
  ln -s $NIX_SSL_CERT_FILE /etc/ssl/certs/ca-certificates.crt && \
  nix-env -iA cachix -f https://cachix.org/api/v1/install && \
  cachix use sohi

WORKDIR /src

COPY . ./

RUN nix-env --verbose --install --file default.nix

ENTRYPOINT ["webcam-filters", "--input-dev", "/input-dev", "--output-dev", "/output-dev"]
