#!/usr/bin/env bash
# RMK-Firmware bauen und als UF2 ablegen
#
#   ./bauen.sh            baut beide Hälften
#   ./bauen.sh reset      baut zusätzlich das Rücksetz-Abbild
#
# Läuft über shell.nix, weil NixOS weder einen C-Compiler noch den
# ARM-Übersetzer im Pfad hat. Rust kommt von rustup (stable), nicht aus
# nixpkgs: die Firmware braucht eine sehr neue Fassung.
#
# Der Dongle wird NICHT gebaut. Diese Tastatur hängt mit der rechten
# Hälfte direkt am USB; ein Dongle ist nur für den Fall gedacht, dass
# der Rechner kein brauchbares Bluetooth hat.
set -euo pipefail

HIER="$(cd "$(dirname "$0")" && pwd)"
# Welcher Baum gebaut wird:
#   charybdis         die Fassung, die auf der Tastatur laeuft
#   fremd-charybdis   die unveraenderte Vorlage von jools333 -- NUR zum
#                     Nachlesen und Vergleichen, NICHT zum Aufspielen
#
# WARUM NICHT WECHSELN: RMK bildet aus Version, Commit und Features
# einen Schema-Hash (rmk/src/storage/mod.rs, SCHEMA_HASH). Stimmt er
# beim Start nicht mit dem gespeicherten ueberein, wird der GESAMTE
# Speicher geloescht -- Bluetooth-Kopplungen und die in Vial geaenderte
# Belegung. Der Commit kommt aus `git log` im Baum; charybdis/ hat kein
# .git (Commit = leer), fremd-charybdis/ hat eins. Ein Flash aus dem
# jeweils anderen Baum loescht also alles. Genau das ist am 12.10.
# passiert, die Tastatur musste neu gekoppelt werden.
#
# Seit 30.10.2026 liegt charybdis/ in einem Git-Repo. Damit der Hash
# trotzdem gleich bleibt, ist der Commit in rmk-upstream/rmk/build.rs
# fest auf "" gesetzt (wie vorher ohne .git). Zum Aufspielen immer
# von hier bauen, nie aus fremd-charybdis/.
PROJEKT="$HIER/${PROJEKT_NAME:-charybdis}"
ZIEL="$HIER/fertig${PROJEKT_NAME:+-$PROJEKT_NAME}"
BIN="$PROJEKT/target/thumbv7em-none-eabihf/release"

mkdir -p "$ZIEL"

ZIELE=(central peripheral)
[[ "${1:-}" == reset ]] && ZIELE+=(settings_reset)

nix-shell "$HIER/shell.nix" --run "
  set -e
  cd '$PROJEKT'
  cargo build --release $(printf -- '--bin %s ' "${ZIELE[@]}")

  for z in ${ZIELE[*]}; do
    case \"\$z\" in
      central)        name=rechts-zentrale ;;
      peripheral)     name=links-gegenstelle ;;
      settings_reset) name=zuruecksetzen ;;
    esac
    arm-none-eabi-objcopy -O ihex '$BIN'/\$z '$ZIEL'/\$name.hex
    # Family 0xADA52840 = nRF52840 mit Adafruit-Bootloader, den der
    # nice!nano mitbringt. Eine falsche Familie lehnt der Bootloader ab.
    python3 '$PROJEKT'/uf2conv.py '$ZIEL'/\$name.hex -c -f 0xADA52840 \
        -o '$ZIEL'/\$name.uf2 >/dev/null
    rm -f '$ZIEL'/\$name.hex
    printf '  %-20s %s\n' \"\$name.uf2\" \"\$(du -h '$ZIEL'/\$name.uf2 | cut -f1)\"
  done

  echo
  arm-none-eabi-size $(printf "'$BIN'/%s " "${ZIELE[@]}")
"
