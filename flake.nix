{
  description = "Silicon Heaven CLI";
  inputs.pyshv.url = "gitlab:elektroline-predator/pyshv";

  outputs = {
    self,
    flake-utils,
    nixpkgs,
    pyshv,
  }:
    with builtins;
    with flake-utils.lib;
    with nixpkgs.lib; let
      pyproject = trivial.importTOML ./pyproject.toml;
      src = builtins.path {
        path = ./.;
        filter = path: type: ! hasSuffix ".nix" path;
      };

      list2attr = list: attr: attrValues (getAttrs list attr);
      pypi2nix = list:
        list2attr (map (n: elemAt (match "([^ ]*).*" n) 0) list);
      requires = pypi2nix pyproject.project.dependencies;

      shvcli = {python3Packages}:
        python3Packages.buildPythonApplication {
          pname = pyproject.project.name;
          inherit (pyproject.project) version;
          format = "pyproject";
          inherit src;
          nativeBuildInputs = [python3Packages.setuptools];
          propagatedBuildInputs = requires python3Packages;
        };
    in
      {
        overlays = {
          noInherit = final: prev: {
            shvcli = final.callPackage shvcli {};
          };
          default = composeManyExtensions [
            pyshv.overlays.default
            self.overlays.noInherit
          ];
        };
      }
      // eachDefaultSystem (system: let
        pkgs = nixpkgs.legacyPackages.${system}.extend self.overlays.default;
      in {
        packages.default = pkgs.shvcli;
        legacyPackages = pkgs;

        devShells = filterPackages system {
          default = pkgs.mkShell {
            packages = with pkgs; [
              editorconfig-checker
              gitlint
              ruff
              (python3.withPackages (p:
                [
                  p.build
                  p.twine
                  p.sphinx-autobuild
                  p.mypy
                ]
                ++ (requires p)))
            ];
          };
        };

        apps.default = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/shvcli";
        };

        checks.default = self.packages.${system}.default;

        formatter = pkgs.alejandra;
      });
}
