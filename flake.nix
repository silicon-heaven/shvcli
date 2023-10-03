{
  description = "Silicon Heaven CLI";
  inputs = {
    pyshv.url = "git+https://gitlab.com/elektroline-predator/pyshv.git?ref=shv3";
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
      attrList = attr: list: attrValues (getAttrs list attr);

      requires = p: attrList p pyproject.project.dependencies;
      requires-docs = p: attrList p pyproject.project.optional-dependencies.docs;
      requires-test = p: attrList p pyproject.project.optional-dependencies.test;
      requires-dev = p:
        attrList p pyproject.project.optional-dependencies.lint
        ++ [p.build p.twine];

      pypkgs-shvcli = {
        buildPythonPackage,
        pipBuildHook,
        setuptools,
        pytestCheckHook,
        pythonPackages,
        sphinxHook,
      }:
        buildPythonPackage {
          pname = pyproject.project.name;
          inherit (pyproject.project) version;
          format = "pyproject";
          src = builtins.path {
            path = ./.;
            filter = path: type: ! hasSuffix ".nix" path;
          };
          outputs = ["out" "doc"];
          propagatedBuildInputs = requires pythonPackages;
          nativeBuildInputs = [sphinxHook] ++ requires-docs pythonPackages;
          nativeCheckInputs = [pytestCheckHook] ++ requires-test pythonPackages;
        };
    in
      {
        overlays = {
          shvcli = final: prev: {
            python3 = prev.python3.override (oldAttrs: let
              prevOverride = oldAttrs.packageOverrides or (_: _: {});
            in {
              packageOverrides = composeExtensions prevOverride (
                pyself: pysuper: {
                  shvcli = pyself.callPackage pypkgs-shvcli {};
                }
              );
            });
            python3Packages = final.python3.pkgs;
          };
          default = composeManyExtensions [
            pyshv.overlays.default
            self.overlays.shvcli
          ];
        };
      }
      // eachDefaultSystem (system: let
        pkgs = nixpkgs.legacyPackages.${system}.extend self.overlays.default;
      in {
        packages = rec {
          inherit (pkgs.python3Packages) shvcli;
          default = shvcli;
        };
        legacyPackages = pkgs;

        devShells = filterPackages system {
          default = pkgs.mkShell {
            packages = with pkgs; [
              editorconfig-checker
              gitlint
              (python3.withPackages (p:
                [p.sphinx-autobuild]
                ++ foldl (prev: f: prev ++ f p) [] [
                  requires
                  requires-docs
                  requires-test
                  requires-dev
                ]))
            ];
          };
        };

        checks.default = self.packages.${system}.default;

        formatter = pkgs.alejandra;
      });
}
