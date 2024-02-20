#!/bin/bash

set -ex

runner_os=$1
tag_name=$2

cd dist/

if [ -f "./imagedephi.exe" ]; then
    executable="imagedephi.exe"
else
    executable="imagedephi"
fi

chmod +x $executable
zipfile="${runner_os}-imagedephi-cli.zip"

if [[ "$runner_os" = "Windows" ]]; then
    powershell Compress-Archive $executable $zipfile
else
    zip $zipfile $executable
fi

gh release upload \
    $tag_name \
    "${zipfile}#${runner_os} executable" \
    --clobber
