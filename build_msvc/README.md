Building Bitcoin Core with Visual Studio
========================================

Introduction
---------------------
Solution and project files to build the Bitcoin Core applications with `msbuild` or [Visual Studio 2017](https://visualstudio.microsoft.com/vs/community/) can be found in the `build_msvc` directory.

Building with Visual Studio is an alternative to the Linux based [cross-compiler build](https://github.com/bitcoin/bitcoin/blob/master/doc/build-windows.md).

Dependencies
---------------------
A number of [open source libraries](https://github.com/bitcoin/bitcoin/blob/master/doc/dependencies.md) are required in order to be able to build Bitcoin.

Options for installing the dependencies in a Visual Studio compatible manner are:

- Use Microsoft's [vcpkg](https://docs.microsoft.com/en-us/cpp/vcpkg) to download the source packages and build locally. This is the recommended approach.
- Download the source code, build each dependency, add the required include paths, link libraries and binary tools to the Visual Studio project files.
- Use [nuget](https://www.nuget.org/) packages with the understanding that any binary files have been compiled by an untrusted third party.

The external dependencies required for the Visual Studio build are (see the [dependencies doc](https://github.com/bitcoin/bitcoin/blob/master/doc/dependencies.md) for versions):

- Berkeley DB,
- Boost,
- DoubleConversion
- libevent,
- OpenSSL,
- Protobuf,
- Qt5,
- RapidCheck
- ZeroMQ.

Qt
---------------------
All the Bitcoin Core applications are configured to build with static linking. In order to build the Bitcoin Core Qt applications a static build of Qt is required.
The runtime library version and platform type (x86 or x64) must also match. OpenSSL must also be linked into the Qt binaries in order to provide full functionality
of the Bitcoin Core Qt programs. An example of the configure command to build Qtv5.9.7 locally to link with Bitcoin Core is shown below (adjust paths accordingly),
note it can be expected that the configure and subsequent build will fail numerous times until dependency issues are resolved.

````
..\Qtv5.9.7_src\configure -developer-build -confirm-license -debug-and-release -opensource -platform win32-msvc -opengl desktop -no-shared -static -no-static-runtime -mp -qt-zlib -qt-pcre -qt-libpng -qt-libjpeg -ltcg -make libs -make tools -nomake examples -no-compile-examples -no-dbus -no-libudev -no-qml-debug -no-icu -no-gtk -no-opengles3 -no-angle -no-sql-sqlite -no-sql-odbc -no-sqlite -no-libudev -skip qt3d -skip qtactiveqt -skip qtandroidextras -skip qtcanvas3d -skip qtcharts -skip qtconnectivity -skip qtdatavis3d -skip qtdeclarative -skip qtdoc -skip qtgamepad -skip qtgraphicaleffects -skip qtimageformats -skip qtlocation -skip qtmacextras -skip qtmultimedia -skip qtnetworkauth -skip qtpurchasing -skip qtquickcontrols -skip qtquickcontrols2 -skip qtscript -skip qtscxml -skip qtsensors -skip qtserialbus -skip qtserialport -skip qtspeech -skip qtvirtualkeyboard -skip qtwayland -skip qtwebchannel -skip qtwebengine -skip qtwebsockets -skip qtwebview -skip qtx11extras -skip qtxmlpatterns -nomake tests -openssl-linked -IC:\Dev\github\vcpkg\installed\x64-windows-static\include -LC:\Dev\github\vcpkg\installed\x64-windows-static\lib OPENSSL_LIBS="-llibeay32 -lssleay32 -lgdi32 -luser32 -lwsock32 -ladvapi32" -prefix C:\Qt5.9.7_ssl_x64_static_vs2017
````

A prebuilt version for x64 and Visual C++ runtime v141 (Visual Studio 2017) can be downloaded from [here](https://github.com/sipsorcery/qt_win_binary/releases). Please be
aware this download is NOT an officially sanctioned Bitcoin Core distribution and is provided for developer convenience. It should NOT be used for builds that will
be used in a production environment or with real funds.

To build Bitcoin Core without Qt unload or disable the bitcoin-qt, libbitcoin_qt and test_bitcoin-qt projects.

Building
---------------------
The instructions below use `vcpkg` to install the dependencies.

- Clone `vcpkg` from the [github repository](https://github.com/Microsoft/vcpkg) and install as per the instructions in the main vcpkg README.md.
- Install the required packages (replace x64 with x86 as required):

```
    PS >.\vcpkg install --triplet x64-windows-static berkeleydb boost-filesystem boost-signals2 boost-test double-conversion libevent openssl protobuf rapidcheck zeromq
```

- Use Python to generate a number of the library *.vcxproj files from the Makefile

```
    PS >python msvc-autogen.py [-qtdir "C:\\Qt5.9.7_ssl_x64_static_vs2017"] [-protocpath "C:\\Tools\\vcpkg\\installed\\x64-windows-static\\tools\\protobuf\\protoc.exe"]
```

- An optional step is to adjust the settings in the build_msvc directory and the `Directory.Build.props` and `Directory.Build.targets` files. These files contain settings that
  are common to multiple projects such as the runtime library version and target Windows SDK version. The Qt directory and protoc path that can be set in the previous step can
  also be set directly by editing `Directory.Build.props`.

- Build by opening the `build_msvc\bitoin.sln` file with Visual Studio 2017 or alternatively with `msbuild` from a `VS 20017 Native Tools Command Prompt`:

```
    C:\src\bitcoin >msbuild build_msvc\bitcoin.sln /p:Platform=x64 /p:Configuration=Release /t:build
```

AppVeyor
---------------------
The .appveyor.yml in the root directory is suitable to perform builds on [AppVeyor](https://www.appveyor.com/) Continuous Integration servers. The simplest way to perform an
AppVeyor build is to fork Bitcoin Core and then configure a new AppVeyor Project pointing to the forked repository.

For safety reasons the Bitcoin Core .appveyor.yml file has the artifact options disabled. The build will be performed but no executable files will be available. To enable
artifacts on a forked repository uncomment the two lines shown below:

```
    #- 7z a bitcoin-%APPVEYOR_BUILD_VERSION%.zip %APPVEYOR_BUILD_FOLDER%\build_msvc\%platform%\%configuration%\*.exe
    #- path: bitcoin-%APPVEYOR_BUILD_VERSION%.zip
```
