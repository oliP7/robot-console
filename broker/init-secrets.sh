#!/bin/sh
# Generates the local secrets on first start, into a named Docker volume.
# Idempotent: existing secrets are kept, the hashed broker password file is
# rebuilt from them on every run. Nothing secret is ever written to the repo.
set -eu
umask 077
dir="${SECRETS_DIR:-/secrets}"

gen() {
    # 32 random bytes, base64 without characters that need quoting.
    head -c 32 /dev/urandom | base64 | tr -d '/+=\n' | cut -c1-40
}

for name in mqtt-backend.pw api.token; do
    if [ ! -s "$dir/$name" ]; then
        gen > "$dir/$name" || { echo "init-secrets: cannot write $dir/$name" >&2; exit 1; }
        echo "init-secrets: generated $name"
    fi
done

# Hashed (PBKDF2-SHA512) password file for Mosquitto.
rm -f "$dir/passwd"
touch "$dir/passwd"
mosquitto_passwd -b "$dir/passwd" backend "$(cat "$dir/mqtt-backend.pw")"

# Mosquitto runs as uid 1883, the backend and test runner as uid 10001.
chown 1883:1883 "$dir/passwd" && chmod 0600 "$dir/passwd"
chown 10001:10001 "$dir/mqtt-backend.pw" "$dir/api.token"
chmod 0400 "$dir/mqtt-backend.pw" "$dir/api.token"
echo "init-secrets: done"
