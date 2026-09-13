#!/bin/sh
# Requires latexmk and an installed TeX distribution; performs no installation.
set -eu
if [ "$#" -ne 1 ]; then echo 'Usage: ./build_pdf.sh /absolute/fresh/output' >&2; exit 2; fi
case "$1" in /*) ;; *) echo 'Choose an absolute fresh output directory' >&2; exit 2;; esac
mkdir -- "$1"
OUTPUT=$1
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$HERE/manuscript"
exec latexmk -g -pdf -interaction=nonstopmode -halt-on-error -file-line-error -outdir="$OUTPUT" main.tex
