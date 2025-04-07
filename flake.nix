{
  description = "Silicon Heaven CLI";
  inputs.pyshv.url = "gitlab:silicon-heaven/pyshv";

  outputs = {
    self,
    pyshv,
  }: let
    inherit (pyshv.inputs) nixpkgs flakepy;
    inherit (flakepy.inputs.flake-utils.lib) eachSystem defaultSystems;
    inherit (nixpkgs.lib) composeManyExtensions;

    pyproject = flakepy.lib.pyproject ./. {};

    pypackage = pyproject.package ({
      runCommandLocal,
      python,
      shvcli,
    }: {
      pythonImportsCheck = ["shvcli"];
      meta.mainProgram = "shvcli";

      passthru.withPlugins = plugins:
        runCommandLocal "shvcli-${pyproject.version}" {
          env = python.buildEnv.override {extraLibs = [shvcli] ++ plugins;};
        } "mkdir -p $out/bin && ln -sf $env/bin/shvcli $out/bin/shvcli";
    });
  in
    {
      overlays = {
        pythonPackages = final: _: {
          "${pyproject.pname}" = final.callPackage pypackage {};
        };
        packages = final: prev: {
          pythonPackagesExtensions =
            prev.pythonPackagesExtensions ++ [self.overlays.pythonPackages];
          "${pyproject.pname}" =
            final.python3Packages.toPythonApplication final.python3Packages.shvcli;
        };
        default = composeManyExtensions [
          pyshv.overlays.default
          self.overlays.packages
        ];
      };
      inherit self;
    }
    // eachSystem (defaultSystems ++ ["armv7l-linux"]) (system: let
      pkgs = nixpkgs.legacyPackages.${system}.extend self.overlays.default;
    in {
      packages.default = pkgs."${pyproject.pname}";
      legacyPackages = pkgs;

      devShells.default = pkgs.mkShell {
        packages = with pkgs; [
          deadnix
          editorconfig-checker
          gitlint
          mypy
          ruff
          shellcheck
          shfmt
          statix
          twine
          (python3.withPackages (pypkgs: with pypkgs; [build sphinx-autobuild]))
        ];
        inputsFrom = [self.packages.${system}.default];
      };

      checks.default = self.packages.${system}.default;

      formatter = pkgs.alejandra;
    });
}
