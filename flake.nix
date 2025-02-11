{
  description = "Silicon Heaven CLI";
  inputs.pyshv.url = "gitlab:silicon-heaven/pyshv";

  outputs = {
    self,
    flake-utils,
    nixpkgs,
    pyshv,
  }: let
    inherit (builtins) match;
    inherit (flake-utils.lib) eachSystem defaultSystems filterPackages;
    inherit (nixpkgs.lib) head trivial hasSuffix attrValues getAttrs composeManyExtensions;

    pyproject = trivial.importTOML ./pyproject.toml;
    inherit (pyproject.project) name version;
    src = builtins.path {
      path = ./.;
      filter = path: _: ! hasSuffix ".nix" path;
    };

    pypi2nix = list: pypkgs:
      attrValues (getAttrs (map (n: let
          pyname = head (match "([^ =<>;]*).*" n);
          pymap = {};
        in
          pymap."${pyname}" or pyname)
        list)
        pypkgs);
    requires = pypi2nix pyproject.project.dependencies;

    pypackage = {
      buildPythonPackage,
      pythonPackages,
      python,
      setuptools,
      runCommandLocal,
    }:
      buildPythonPackage {
        pname = pyproject.project.name;
        inherit version src;
        pyproject = true;
        build-system = [setuptools];
        propagatedBuildInputs = requires pythonPackages;
        pythonImportsCheck = ["shvcli"];
        meta.mainProgram = "shvcli";

        passthru.withPlugins = plugins:
          runCommandLocal "shvcli-${version}" {
            env = python.buildEnv.override {extraLibs = [pythonPackages.shvcli] ++ plugins;};
          } "mkdir -p $out/bin && ln -sf $env/bin/shvcli $out/bin/shvcli";
      };
  in
    {
      overlays = {
        pythonPackagesExtension = final: _: {
          "${name}" = final.callPackage pypackage {};
        };
        noInherit = final: prev: {
          pythonPackagesExtensions = prev.pythonPackagesExtensions ++ [self.overlays.pythonPackagesExtension];
          "${name}" = final.python3Packages.toPythonApplication final.python3Packages.shvcli;
        };
        default = composeManyExtensions [
          pyshv.overlays.default
          self.overlays.noInherit
        ];
      };
    }
    // eachSystem (defaultSystems ++ ["armv7l-linux"]) (system: let
      pkgs = nixpkgs.legacyPackages.${system}.extend self.overlays.default;
    in {
      packages.default = pkgs."${name}";
      legacyPackages = pkgs;

      devShells = filterPackages system {
        default = pkgs.mkShell {
          packages = with pkgs; [
            deadnix
            editorconfig-checker
            gitlint
            ruff
            shellcheck
            shfmt
            statix
            (
              python3.withPackages (p:
                [p.build p.twine p.mypy] ++ (requires p))
            )
          ];
        };
      };

      checks.default = self.packages.${system}.default;

      formatter = pkgs.alejandra;
    });
}
