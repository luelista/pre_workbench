{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      python = pkgs.python311;    # currently only works on python 3.11
              # seems to be related to this bug : https://www.riverbankcomputing.com/pipermail/pyqt/2023-June/045325.html
              # maybe only PyQt6 will work with newer python ???
      pp = pkgs.python311Packages;
    in
    {
      packages.${system} = {
        pyqtads = pp.buildPythonPackage rec {
          pname = "PyQtAds";
          version = "4.3.1";  # 4.4.0 has a change making DockComponentsFactory.h / DockComponentsFactory.sip incompatbile (QSharedPointer return type)
          pyproject = true;

          disabled = pp.pythonOlder "3.11";

          src = pkgs.fetchFromGitHub {
                  owner = "githubuser0xFFFF";
                  repo = "Qt-Advanced-Docking-System";
                  rev = "refs/tags/${version}";
                  hash = "sha256-5wOmhjV/RoKvd018YC4J8EFCCkq+3B6AXAsPtW+RZHU=";
          };

          # from https://github.com/NixOS/nixpkgs/blob/46606678d54c34c1b2f346605224acae7908cd67/pkgs/development/python-modules/pyqtdatavisualization/default.nix#L6
          postPatch = ''
            substituteInPlace pyproject.toml \
              --replace-fail "[tool.sip.project]" "[tool.sip.project]''\nsip-include-dirs = [\"${pp.pyqt5}/${pp.python.sitePackages}/PyQt5/bindings\"]" \
              --replace-warn "dunder-init = true" ""
          '';

          build-system = [
                  pp.pip
                  pp.pyqt-builder
                  pp.sip
                  pp.pyqt5
                  pp.cython
          ];

          nativeBuildInputs = [
                  #pp.setuptools-scm
                  pp.pyqt5-sip
                  #pp.pyqt5
                  #pp.sip4
                  pkgs.libsForQt5.qt5.qtbase
                  pkgs.xorg.libxcb
          ];
          buildInputs = [
                  pkgs.libsForQt5.qt5.qtbase
                  pkgs.xorg.libxcb
          ];
          propagatedBuildInputs = [ pp.pyqt5 pp.pyqt5-sip ];
          dependencies = [
                  pp.pyqt5
                  pp.pyqt5-sip
                  pp.sip
          ];
          dontWrapQtApps = true;

          #buildPhase = ''
          #python setup.py build_ext --pyqt-sip-dir "${pp.pyqt5}/${pp.python.sitePackages}/PyQt5/bindings"
          #pip build .
          #'';


          nativeCheckInputs = [  ];

          #disabledTestPaths = [ "tests/test_builds.py" ];

          pythonImportsCheck = [ "PyQtAds" ];

          meta = {
                  homepage = "https://github.com/githubuser0xFFFF/Qt-Advanced-Docking-System";
                  license = pkgs.lib.licenses.lgpl21;
          };
        };

        pre_workbench = pp.buildPythonApplication {
          pname = "pre_workbench";
          version = "0.9.0";
          pyproject = true;

          disabled = pp.pythonOlder "3.11";

          build-system = [
            pp.setuptools-scm
            pp.setuptools
            pp.cython
          ];
          dependencies = [
            self.packages.${system}.pyqtads
            pp.appdirs
            pp.qscintilla-qt5
            pp.darkdetect
            pp.bitstring
            pp.pyyaml
            pp.psutil
            pp.lark
          ];
          nativeBuildInputs = [
            pkgs.libsForQt5.qt5.qtbase
            pkgs.libsForQt5.wrapQtAppsHook
          ];

          nativeInputs = [ pkgs.qt5.wrapQtAppsHook ];
          dontWrapGApps = true;
          dontWrapQtApps = true;

          src = ./.;

          # Arguments to be passed to `makeWrapper`, only used by buildPython*
          preFixup = ''
          makeWrapperArgs+=("''${qtWrapperArgs[@]}")
          '';

          desktopItems = [
            (pkgs.makeDesktopItem {
              name = "pre_workbench";
              desktopName = "PRE Workbench";
              icon = ./pre_workbench/icons/appicon.png;
              exec = "prewb";
            })
          ];

          meta = {
            mainProgram = "prewb";
            homepage = "https://luelista.net/pre_workbench/";
            license = pkgs.lib.licenses.gpl3;
          };
        };

        default = self.packages.${system}.pre_workbench;

      };

      devShells.${system}.test = (pkgs.buildFHSUserEnv {
        name = "fhs-shell";
        targetPkgs = pkgs: [
          pkgs.gcc pkgs.gdb pkgs.libtool
          (python.withPackages(ps: with ps; [
            pyqt5 qscintilla-qt5 pyyaml bitstring darkdetect lark
            appdirs
            self.packages.${system}.pyqtads
          ]))
          pkgs.libz pkgs.glib pkgs.libGL
          pkgs.libsForQt5.qt5.full
        ];
      }).env;
    };
}
