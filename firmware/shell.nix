# Bauumgebung für die RMK-Firmware (Rust) auf NixOS
#
#   nix-shell            und darin:  ./bauen.sh
#
# Warum überhaupt: NixOS hat keinen C-Compiler im Pfad. Rust braucht
# ihn nicht für die Firmware selbst -- die läuft auf ARM --, wohl aber
# für die Bauskripte mancher Pakete, und die laufen auf diesem Rechner.
# Ohne gcc bricht der Bau mit "linker `cc` not found" ab.
#
# Die Rust-Werkzeuge kommen bewusst NICHT von hier, sondern von
# rustup: die Firmware braucht eine sehr neue Fassung (1.93+ wegen des
# Pakets `fixed`), und nixpkgs hinkt da regelmässig hinterher.
{ pkgs ? import <nixpkgs> { } }:

pkgs.mkShell {
  name = "charybdis-rmk";

  nativeBuildInputs = with pkgs; [
    gcc                 # für die Bauskripte der Pakete (laufen hier)
    gcc-arm-embedded    # für C-Teile, die FÜR den nRF52840 übersetzt werden
    llvmPackages.libclang   # bindgen liest damit die Nordic-Kopfdateien
    pkg-config
    python3             # uf2conv.py wandelt die Firmware ins UF2-Format
  ];

  shellHook = ''
    export RUSTUP_TOOLCHAIN=stable

    # Zwei verschiedene Compiler, und cc-rs muss wissen, welcher wofür:
    # die Bauskripte laufen auf diesem Rechner (x86), ein Paket
    # (p256-cortex-m4) bringt aber handgeschriebenen Assembler für den
    # Cortex-M4 mit, der mit dem ARM-Compiler übersetzt werden muss.
    export CC_thumbv7em_none_eabihf=arm-none-eabi-gcc
    export AR_thumbv7em_none_eabihf=arm-none-eabi-ar
    export CC_x86_64_unknown_linux_gnu=gcc

    # Die Nordic-Funkbibliothek kommt als C-Bibliothek; bindgen erzeugt
    # daraus die Rust-Schnittstelle und braucht dafür libclang.
    export LIBCLANG_PATH="${pkgs.llvmPackages.libclang.lib}/lib"

    echo "RMK-Bauumgebung"
    echo "  rustc:     $(rustc --version 2>/dev/null || echo FEHLT)"
    echo "  ARM-gcc:   $(arm-none-eabi-gcc -dumpversion 2>/dev/null || echo FEHLT)"
    echo "  Ziel:      thumbv7em-none-eabihf (nRF52840, Cortex-M4F)"
  '';
}
