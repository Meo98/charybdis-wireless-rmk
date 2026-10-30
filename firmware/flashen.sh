#!/usr/bin/env bash
# Firmware auf eine Hälfte spielen
#
#   ./flashen.sh rechts|links|beide
#
# Die Hälfte muss im Bootloader sein: zweimal schnell auf Reset
# drücken, dann erscheint ein Laufwerk NICENANO. Welches Laufwerk zu
# welcher Hälfte gehört, wird über den USB-Anschluss bestimmt und nicht
# über den Namen -- der ist bei beiden gleich und die Nummerierung
# hängt davon ab, welche zuerst angesteckt wurde.
set -euo pipefail

HIER="$(cd "$(dirname "$0")" && pwd)"
FERTIG="$HIER/fertig"

# Welcher USB-Anschluss ist welche Hälfte. Steht hier, weil es sich
# nur ändert, wenn umgesteckt wird.
ANSCHLUSS_RECHTS="usb3/3-2"      # die mit dem Trackball, Zentrale
ANSCHLUSS_LINKS="usb3/3-1"

finde_laufwerk() {
  local anschluss="$1"
  for m in /run/media/meo/NICENANO*; do
    [[ -d "$m" ]] || continue
    local quelle pfad
    quelle="$(findmnt -no SOURCE "$m" 2>/dev/null)" || continue
    pfad="$(udevadm info -q path -n "$quelle" 2>/dev/null)"
    if [[ "$pfad" == *"$anschluss"* ]]; then
      echo "$m"
      return 0
    fi
  done
  return 1
}

spiele_auf() {
  local seite="$1" anschluss datei ziel
  case "$seite" in
    rechts) anschluss="$ANSCHLUSS_RECHTS"; datei=rechts-zentrale.uf2 ;;
    links)  anschluss="$ANSCHLUSS_LINKS";  datei=links-gegenstelle.uf2 ;;
    *) echo "unbekannte Seite: $seite" >&2; return 2 ;;
  esac

  [[ -f "$FERTIG/$datei" ]] || { echo "$datei fehlt -- erst ./bauen.sh" >&2; return 1; }

  if ! ziel="$(finde_laufwerk "$anschluss")"; then
    # Rueckfall fuer andere Rechner (meo-work, Dock): die Anschluesse oben
    # stimmen nur auf meo. Steckt GENAU ein NICENANO, ist es eindeutig --
    # die Seite hast du ja beim Aufruf genannt. Bei zweien wird nicht geraten.
    local alle=(/run/media/meo/NICENANO*)
    if [[ ${#alle[@]} -eq 1 && -d "${alle[0]}" ]]; then
      ziel="${alle[0]}"
      echo "Anschluss $anschluss nicht gefunden, nehme das einzige NICENANO: $ziel"
    else
      echo "'$seite' ist nicht im Bootloader (kein NICENANO an $anschluss)." >&2
      echo "Zweimal schnell auf Reset druecken -- an einem fremden Rechner" >&2
      echo "nur EINE Haelfte gleichzeitig einstecken." >&2
      return 1
    fi
  fi

  cp "$FERTIG/$datei" "$ziel/"
  sync
  echo "'$seite' bespielt: $datei -> $ziel"
}

case "${1:-}" in
  rechts|links) spiele_auf "$1" ;;
  beide)        spiele_auf links; sleep 2; spiele_auf rechts ;;
  *) echo "Aufruf: $0 rechts|links|beide" >&2; exit 2 ;;
esac
