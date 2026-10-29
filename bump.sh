#!/bin/sh
# 每次更新前執行：換新版號，手機開啟時就會提示更新
sed -i "s/^<meta name=\"app-ver\" content=\"[^\"]*\"/<meta name=\"app-ver\" content=\"$(date +%Y%m%d-%H%M)\"/" index.html
