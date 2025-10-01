{
  description = "Silicon Heaven CLI";
  inputs.pyshv.url = "gitlab:silicon-heaven/pyshv";

  outputs = {
    self,
    pyshv,
  }: let
    inherit (pyshv.inputs) nixpkgs flakepy;
    inherit (nixpkgs.lib) composeManyExtensions genAttrs;
    forSystems = genAttrs (import flakepy.inputs.systems);
    withPkgs = func: forSystems (system: func self.legacyPackages.${system});

    pyproject = flakepy.lib.readPyproject ./. {};

    pypackage = pyproject.buildPackage ({
      dependencies,
      runCommandLocal,
      python,
      pyshv,
      shvcli,
    }: {
      dependencies =
        dependencies
        ++ pyshv.optional-dependencies.canbus
        ++ pyshv.optional-dependencies.websockets;
      pythonImportsCheck = ["shvcli"];
      meta.mainProgram = "shvcli";

      passthru.withPlugins = plugins:
        runCommandLocal "shvcli-${pyproject.version}" {
          environ = python.buildEnv.override {extraLibs = [shvcli] ++ plugins;};
        } "mkdir -p $out/bin && ln -sf $environ/bin/shvcli $out/bin/shvcli";
    });
  in {
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

    legacyPackages =
      forSystems (system:
        nixpkgs.legacyPackages.${system}.extend self.overlays.default);

    packages = withPkgs (pkgs: {
      default = pkgs."${pyproject.pname}";
    });

    devShells = withPkgs (pkgs: {
      default = pkgs.mkShell {
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
          (python3.withPackages (pypkgs:
              with pypkgs; [build sphinx-autobuild]))
        ];
        inputsFrom = [pkgs.python3Packages."${pyproject.pname}"];
      };
    });

    checks = withPkgs (pkgs: {
      python311 = pkgs.python311Packages."${pyproject.pname}";
      python312 = pkgs.python312Packages."${pyproject.pname}";
      python313 = pkgs.python313Packages."${pyproject.pname}";
    });

    formatter = withPkgs (pkgs: pkgs.alejandra);
  };
}
