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
    inherit (flake-utils.lib) eachDefaultSystem filterPackages;
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

    package = {python3Packages}:
      python3Packages.buildPythonApplication {
        pname = pyproject.project.name;
        inherit version src;
        pyproject = true;
        build-system = [python3Packages.setuptools];
        propagatedBuildInputs = requires python3Packages;
        meta.mainProgram = "shvcli";
      };
  in
    {
      overlays = {
        noInherit = final: _: {
          "${name}" = final.callPackage package {};
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
      packages.default = pkgs."${name}";
      legacyPackages = pkgs;

      devShells = filterPackages system {
        default = pkgs.mkShell {
          packages = with pkgs; [
            editorconfig-checker
            statix
            deadnix
            gitlint
            ruff
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
