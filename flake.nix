{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      python = pkgs.python311;
      pp = pkgs.python311Packages;
      fhs = pkgs.buildFHSUserEnv {
        name = "fhs-shell";
        targetPkgs = pkgs: [pkgs.gcc pkgs.libtool (python.withPackages(ps: with ps; [ pyqt5 qscintilla-qt5 pyyaml bitstring darkdetect lark ])) pkgs.libz pkgs.glib pkgs.libGL pkgs.qt5.qtbase] ;
      };
    in
    {
      packages.${system} = {
        pyqtads = pp.buildPythonPackage rec {
          pname = "PyQtAds";
          version = "3.8.1";
          pyproject = false;

          disabled = pp.pythonOlder "3.7";

          src = pkgs.fetchFromGitHub {
                  owner = "githubuser0xFFFF";
                  repo = "Qt-Advanced-Docking-System";
                  rev = "refs/tags/${version}";
                  hash = "sha256-Zl1AAYERX76rC+wAvk8/uXSuKkmHMbUovbU8O6LgQTw=";
          };


          env.PYQT5_SIP_DIR="${pp.pyqt5}/${pp.python.sitePackages}/PyQt5/bindings";
          env.PYQT_SIP_DIR_OVERRIDE="${pp.pyqt5}/${pp.python.sitePackages}/PyQt5/bindings";
          build-system = [
                  pp.setuptools
                  pp.sip4
                  pp.pyqt5
                  pp.cython
          ];

          nativeBuildInputs = [
                  #pp.setuptools-scm
                  #pp.pyqt5-sip
                  #pp.pyqt5
                  #pp.sip4
                  pkgs.libsForQt5.qt5.full
          ];
          dependencies = [
                  pp.pyqt5
                  pp.pyqt5-sip
          ];
          propagatedBuildInputs = [
                  #pkgs.qt5.full
          ];
          dontWrapQtApps = true;

          buildPhase = ''
          python setup.py build_ext --pyqt-sip-dir "${pp.pyqt5}/${pp.python.sitePackages}/PyQt5/bindings"
          '';


          nativeCheckInputs = [  ];

          #disabledTestPaths = [ "tests/test_builds.py" ];

          pythonImportsCheck = [ "PyQtAds" ];

          meta = {
                  #description = "MkDocs plugin that enables displaying the date of the last git modification of a page";
                  homepage = "https://github.com/githubuser0xFFFF/Qt-Advanced-Docking-System";
                  #changelog = "https://github.com/timvink/mkdocs-git-revision-date-localized-plugin/releases/tag/v${version}";
                  license = pkgs.lib.licenses.lgpl21;
                  #maintainers = with maintainers; [ totoroot ];
          };
        };
      };

        
      devShells.${system}.default = fhs.env;
    };
}
