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
          version = "3.8.4";
          pyproject = true;

          disabled = pp.pythonOlder "3.11";

          src = pkgs.fetchFromGitHub {
                  owner = "githubuser0xFFFF";
                  repo = "Qt-Advanced-Docking-System";
                  rev = "refs/tags/${version}";
                  hash = "sha256-LojmwuCdcwJLlgDcg/09WTfr8ROCZCL56eZuBuuyQvk=";
          };

          # from https://github.com/NixOS/nixpkgs/blob/46606678d54c34c1b2f346605224acae7908cd67/pkgs/development/python-modules/pyqtdatavisualization/default.nix#L6
          postPatch = ''
            substituteInPlace pyproject.toml \
              --replace-fail "[tool.sip.project]" "[tool.sip.project]''\nsip-include-dirs = [\"${pp.pyqt5}/${pp.python.sitePackages}/PyQt5/bindings\"]" \
              --replace-warn '"sip >=6.0.2, <6.6"' '"sip >=6.0.2, <6.9"' \
              --replace-warn '# "src/linux/FloatingWidgetTitleBar.h",' '"'"src/linux/FloatingWidgetTitleBar.h; platform_system == 'Linux'"'",' \
              --replace-warn '# "src/linux/FloatingWidgetTitleBar.cpp",' '"'"src/linux/FloatingWidgetTitleBar.cpp; platform_system == 'Linux'"'",'
            substituteInPlace project.py \
              --replace-fail 'super().apply_user_defaults(tool)' 'self.builder_settings.append("unix:!macx {\nLIBS += -lxcb\nQT += gui-private\n}"); super().apply_user_defaults(tool)'
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
          propagatedBuildInputs = [ pp.pyqt5 ];
          dependencies = [
                  pp.pyqt5
                  pp.pyqt5-sip
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
          dontWrapQtApps = true;

          src = ./.;

          # Arguments to be passed to `makeWrapper`, only used by buildPython*
          preFixup = ''
          for app in "$out/bin/"*; do
            wrapQtApp "$app"
          done
          '';
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
