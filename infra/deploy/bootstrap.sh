#!/bin/bash
# cloud-init / user_data: install Docker, add swap, clone the repo.
# Interpolated by Terraform templatefile — shell vars use $${…}.
set -euxo pipefail

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl git gnupg

# 2 GB swap for t3.small + Mongo
if [ ! -f /swapfile ]; then
  fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$${VERSION_CODENAME}") stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
usermod -aG docker ubuntu || true

# Attach and mount the Mongo data volume if present (/dev/nvme1n1 or /dev/xvdf).
DATA_DEV=""
for cand in /dev/nvme1n1 /dev/xvdf /dev/sdf; do
  if [ -b "$${cand}" ]; then DATA_DEV="$${cand}"; break; fi
done
if [ -n "$${DATA_DEV}" ]; then
  mkdir -p /var/lib/trao-mongo
  if ! blkid "$${DATA_DEV}" >/dev/null 2>&1; then
    mkfs.ext4 -L trao-mongo "$${DATA_DEV}"
  fi
  if ! grep -q trao-mongo /etc/fstab; then
    echo "LABEL=trao-mongo /var/lib/trao-mongo ext4 defaults,nofail 0 2" >> /etc/fstab
  fi
  mount -a || mount "$${DATA_DEV}" /var/lib/trao-mongo || true
fi

install -d -o ubuntu -g ubuntu /home/ubuntu/trao
if [ ! -d /home/ubuntu/trao/.git ]; then
  sudo -u ubuntu git clone "${repo_url}" /home/ubuntu/trao || true
fi

echo "bootstrap complete"
