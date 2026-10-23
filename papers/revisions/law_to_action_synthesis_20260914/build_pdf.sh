#!/bin/sh
set -eu
if [ "$#" -ne 1 ]; then
  printf '%s\n' 'Usage: ./build_pdf.sh FRESH_OUTPUT_DIRECTORY' >&2
  exit 2
fi
law_source_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
case "$1" in
  /*) law_build_output=$1 ;;
  *) law_build_output=$(pwd)/$1 ;;
esac
if [ -e "$law_build_output" ]; then
  printf '%s\n' 'Choose an output directory that does not exist.' >&2
  exit 2
fi
command -v pdflatex >/dev/null
command -v bibtex >/dev/null
mkdir -p -- "$law_build_output"
cd "$law_source_dir/manuscript"
pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error -file-line-error -output-directory="$law_build_output" main.tex
(
  cd "$law_build_output"
  BIBINPUTS="$law_source_dir/manuscript:" bibtex main
)
pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error -file-line-error -output-directory="$law_build_output" main.tex
pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error -file-line-error -output-directory="$law_build_output" main.tex
