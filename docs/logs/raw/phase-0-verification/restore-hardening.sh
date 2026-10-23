#!/usr/bin/env bash
# Phase 0 verification, the items left NOT VERIFIED: restore over HTTP (wrong confirmation, state
# ok, double submit) and the hardening extras. TEST stack only: http://127.0.0.1:8471.
set -u
B=http://127.0.0.1:8471
H='X-Enderchest: 1'
J='Content-Type: application/json'

show() {
  local label=$1; shift
  local out; out=$(curl -s -w '\n%{http_code}' "$@")
  printf '%-60s %s  %s\n' "$label" "${out##*$'\n'}" "$(printf '%s' "${out%$'\n'*}" | head -c 150 | tr '\n' ' ')"
}

echo "== setup: reset, a name, one manual backup"
curl -s -o /dev/null -X POST -H "$H" "$B/api/v1/test/reset"
curl -s -o /dev/null -X PUT -H "$H" -H "$J" -d '{"name":"Restore Probe","timezone":"Asia/Kolkata"}' "$B/api/v1/profile"
name=$(curl -s -X POST -H "$H" "$B/api/v1/backups" | sed -n 's/.*"name":"\([^"]*\)".*/\1/p')
echo "backup made: $name"

echo "== restore while the state is ok"
show "restore in state ok -> 409 conflict" -X POST -H "$H" -H "$J" -d "{\"name\":\"$name\",\"confirm\":\"RESTORE\"}" "$B/api/v1/boot/restore"
show "start-empty in state ok -> 409 conflict" -X POST -H "$H" -H "$J" -d '{"confirm":"START EMPTY"}' "$B/api/v1/boot/start-empty"

echo "== into recovery: delete only the test database file"
show "delete-db -> recovery" -X POST -H "$H" "$B/api/v1/test/delete-db"
show "wrong confirmation (lower case) -> 422" -X POST -H "$H" -H "$J" -d "{\"name\":\"$name\",\"confirm\":\"restore\"}" "$B/api/v1/boot/restore"
show "no confirmation -> 422" -X POST -H "$H" -H "$J" -d "{\"name\":\"$name\"}" "$B/api/v1/boot/restore"
show "unknown backup name -> 409" -X POST -H "$H" -H "$J" -d '{"name":"manual-20000101T000000Z","confirm":"RESTORE"}' "$B/api/v1/boot/restore"
show "path in the name -> 409" -X POST -H "$H" -H "$J" -d '{"name":"../db/enderchest","confirm":"RESTORE"}' "$B/api/v1/boot/restore"
show "still recovery after the refusals" "$B/health"

echo "== double submit: two restores of the same backup at the same moment"
tmp=$(mktemp -d)
for i in 1 2; do
  curl -s -o "$tmp/body$i" -w '%{http_code}' -X POST -H "$H" -H "$J" \
    -d "{\"name\":\"$name\",\"confirm\":\"RESTORE\"}" "$B/api/v1/boot/restore" > "$tmp/code$i" &
done
wait
for i in 1 2; do printf '%-60s %s  %s\n' "restore request $i" "$(cat "$tmp/code$i")" "$(head -c 150 "$tmp/body$i")"; done
show "state after the double submit" "$B/health"
show "the owner's name came back" "$B/api/v1/profile"
printf '%-60s %s\n' "restore-safety backups made (one per restore that ran)" "$(curl -s "$B/api/v1/backups" | grep -o '"name":"[a-z-]*' | sort | uniq -c | tr '\n' ' ')"

echo "== hardening extras"
for host in 'localhost.evil.example:8471' '127.0.0.1.nip.io:8471' 'evil.example' 'localhost' '127.0.0.1:9999' '[::1]:9999' 'LOCALHOST:8471'; do
  printf '%-60s %s\n' "Host: $host" "$(curl -s -o /dev/null -w '%{http_code}' -H "Host: $host" "$B/health")"
done
show "OPTIONS preflight (no safety header) -> 403, no CORS" -X OPTIONS -H 'Origin: http://evil.example' -H 'Access-Control-Request-Method: PUT' "$B/api/v1/profile"
printf '%-60s %s\n' "  Access-Control headers on that answer" "$(curl -s -D - -o /dev/null -X OPTIONS -H 'Origin: http://evil.example' -H 'Access-Control-Request-Method: PUT' "$B/api/v1/profile" | grep -ci 'access-control')"
show "multipart on a non-upload path -> 422" -X PUT -H "$H" -F 'name=A' -F 'timezone=UTC' "$B/api/v1/profile"
show "form-urlencoded -> 422" -X PUT -H "$H" -d 'name=A&timezone=UTC' "$B/api/v1/profile"
show "chunked body with no content type -> 422" -X PUT -H "$H" -H 'Transfer-Encoding: chunked' --data-binary '{"name":"A","timezone":"UTC"}' "$B/api/v1/profile"
big=$(mktemp); head -c 20000000 /dev/zero | tr '\0' 'x' > "$big"
start=$(date +%s.%N)
show "20 MB JSON string as the name -> 422 (no size cap yet)" -X PUT -H "$H" -H "$J" --data-binary @<(printf '{"name":"'; cat "$big"; printf '","timezone":"UTC"}') "$B/api/v1/profile"
printf '%-60s %s\n' "  seconds for that request" "$(echo "$(date +%s.%N) - $start" | bc 2>/dev/null || echo n/a)"
show "app still answers after it" "$B/health"
rm -rf "$tmp" "$big"
