{
  description = "Silicon Heaven CLI";
  inputs = {
    pyshv.url = "git+https://gitlab.com/elektroline-predator/pyshv.git";
  };

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
      requires-dev = p:
        pypi2nix pyproject.project.optional-dependencies.lint p
        ++ [p.build p.twine];

      shvcli = {python3Packages}:
        python3Packages.buildPythonApplication {
          pname = pyproject.project.name;
          inherit (pyproject.project) version;
          format = "pyproject";
          inherit src;
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
        packages = {
          inherit (pkgs) shvcli;
          default = pkgs.shvcli;
        };
        legacyPackages = pkgs;

        devShells = let
          mkShell = pythonX:
            pkgs.mkShell {
              packages = with pkgs; [
                (pythonX.withPackages (p:
                  foldl (prev: f: prev ++ f p) [] [
                    requires
                    requires-dev
                  ]))
                editorconfig-checker
                gitlint
              ];
            };
        in
          filterPackages system {
            default = mkShell pkgs.python3;
            python310 = mkShell pkgs.python310;
            python311 = mkShell pkgs.python311;
          };

        checks.default = self.packages.${system}.default;

        formatter = pkgs.alejandra;
      });
}
