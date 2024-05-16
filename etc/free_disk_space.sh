#!/usr/bin/env bash
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


#
# The Azure provided machines typically have the following disk allocation:
# Total space: 85GB
# Allocated: 67 GB
# Free: 17 GB
# This script frees up 28 GB of disk space by deleting unneeded packages and
# large directories.
# The Flink end to end tests download and generate more than 17 GB of files,
# causing unpredictable behavior and build failures.
#
echo "=============================================================================="
echo "Freeing up disk space on CI system"
echo "=============================================================================="

set -x
echo "Listing 100 largest packages"
dpkg-query -Wf '${Installed-Size}\t${Package}\n' | sort -n | tail -n 100
df -h
echo "Removing large packages"
sudo apt-get update -y
# purge is like remove, but also removes configuration
sudo apt-get purge -y '^ghc-.*' || true
sudo apt-get purge -y '^dotnet-.*' || true
sudo apt-get purge -y '^llvm-.*' || true
sudo apt-get purge -y '^libclang-.*' || true
sudo apt-get purge -y '^gcc-.*' || true
sudo apt-get purge -y '^temurin-.*-jdk' || true
sudo apt-get purge -y 'php.*' || true
sudo apt-get purge -y 'google-cloud.*' || true
sudo apt-get purge -y 'google-chrome.*' || true
sudo apt-get purge -y azure-cli || true
sudo apt-get purge -y hhvm || true
sudo apt-get purge -y firefox || true
sudo apt-get purge -y powershell || true
sudo apt-get purge -y mono-devel || true
sudo apt-get purge -y microsoft-edge-stable || true
sudo apt-get autoremove -y
sudo apt-get clean
sudo apt-get update -y
echo "Listing 100 largest remaining packages"
dpkg-query -Wf '${Installed-Size}\t${Package}\n' | sort -n | tail -n 100
df -h
echo "Removing large directories"
# deleting 15GB
rm -rf /usr/share/dotnet/
df -h
du -sh /opt/hostedtoolcache/* | sort -h
rm -rf /opt/hostedtoolcache/go /opt/hostedtoolcache/CodeQL
df -h
