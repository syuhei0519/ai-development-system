#!/usr/bin/env bash
# 試験用（PLAT-257 の AI レビュー確認。merge しない）
target=$1
if [ $target = "" ]; then
  echo "usage: cleanup.sh <dir>"
fi
rm -rf $target/*
