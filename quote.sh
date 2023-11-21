#!/bin/bash
q=$(motivate | sed -e 's/\x1b\[[0-9;]*m//g' | tr -d "[:cntrl:]")

echo $q
