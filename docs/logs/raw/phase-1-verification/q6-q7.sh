#!/usr/bin/env bash
# Phase 1 verification probes Q6 (write endpoints refuse what they must) and Q7 (routing truth).
# TEST stack only: http://127.0.0.1:8471 (compose.test.yaml). Never point this at port 8470.
set -u
B=http://127.0.0.1:8471
H='X-Enderchest: 1'
J='Content-Type: application/json'

show() { # label, then curl arguments; prints status and the first 160 characters of the body
  local label=$1; shift
  local out; out=$(curl -s -w '\n%{http_code}' "$@")
  printf '%-58s %s  %s\n' "$label" "${out##*$'\n'}" "$(printf '%s' "${out%$'\n'*}" | head -c 160 | tr '\n' ' ')"
}

curl -s -o /dev/null -X POST -H "$H" "$B/api/v1/test/reset"
echo "== Q6: PUT /profile"
show "no safety header -> 403" -X PUT -H "$J" -d '{"name":"A","timezone":"UTC"}' "$B/api/v1/profile"
show "foreign Origin -> 403" -X PUT -H "$H" -H "$J" -H 'Origin: http://evil.example' -d '{"name":"A","timezone":"UTC"}' "$B/api/v1/profile"
show "Origin: null -> 403" -X PUT -H "$H" -H "$J" -H 'Origin: null' -d '{"name":"A","timezone":"UTC"}' "$B/api/v1/profile"
show "text/plain body -> 422" -X PUT -H "$H" -H 'Content-Type: text/plain' -d '{"name":"A","timezone":"UTC"}' "$B/api/v1/profile"
show "41 characters -> 422" -X PUT -H "$H" -H "$J" -d "{\"name\":\"$(printf 'x%.0s' {1..41})\",\"timezone\":\"UTC\"}" "$B/api/v1/profile"
show "spaces only -> 422" -X PUT -H "$H" -H "$J" -d '{"name":"   ","timezone":"UTC"}' "$B/api/v1/profile"
show "a number -> 422" -X PUT -H "$H" -H "$J" -d '{"name":7,"timezone":"UTC"}' "$B/api/v1/profile"
show "extra field -> 422" -X PUT -H "$H" -H "$J" -d '{"name":"A","timezone":"UTC","admin":true}' "$B/api/v1/profile"
show "unknown zone -> 422" -X PUT -H "$H" -H "$J" -d '{"name":"A","timezone":"Mars/Base"}' "$B/api/v1/profile"
show "control character -> 422" -X PUT -H "$H" -H "$J" -d '{"name":"A\u0007B","timezone":"UTC"}' "$B/api/v1/profile"
show "not JSON at all -> 422" -X PUT -H "$H" -H "$J" -d '{"name":' "$B/api/v1/profile"
show "after all refusals: profile unchanged (name null)" "$B/api/v1/profile"
show "valid, 40 characters plus spaces -> 200" -X PUT -H "$H" -H "$J" -d "{\"name\":\"  $(printf 'y%.0s' {1..40})  \",\"timezone\":\"Asia/Kolkata\"}" "$B/api/v1/profile"
show "valid -> 200" -X PUT -H "$H" -H "$J" -d '{"name":"Mohammed","timezone":"Asia/Kolkata","theme":"light"}' "$B/api/v1/profile"
echo "== Q6: PATCH /settings"
show "before" "$B/api/v1/settings"
show "one good key and one unknown key -> 422" -X PATCH -H "$H" -H "$J" -d '{"lead_days":9,"bogus":1}' "$B/api/v1/settings"
show "one good key and one bad value -> 422" -X PATCH -H "$H" -H "$J" -d '{"lead_days":9,"gemini_mode":"always"}' "$B/api/v1/settings"
show "string for a number -> 422" -X PATCH -H "$H" -H "$J" -d '{"lead_days":"9"}' "$B/api/v1/settings"
show "null value -> 422" -X PATCH -H "$H" -H "$J" -d '{"coach_enabled":null}' "$B/api/v1/settings"
show "out of range 15 -> 422" -X PATCH -H "$H" -H "$J" -d '{"lead_days":15}' "$B/api/v1/settings"
show "no safety header -> 403" -X PATCH -H "$J" -d '{"lead_days":9}' "$B/api/v1/settings"
show "after refusals: unchanged" "$B/api/v1/settings"
show "valid -> 200" -X PATCH -H "$H" -H "$J" -d '{"lead_days":9}' "$B/api/v1/settings"
echo "== Q7: routing"
show "unknown /api path -> JSON 404" "$B/api/v1/nothing"
show "unknown /api path, POST -> JSON 404" -X POST -H "$H" "$B/api/v1/nothing"
show "DELETE on /profile -> 404 or 405, never the shell" -X DELETE -H "$H" "$B/api/v1/profile"
show "gallery is not shipped -> 404" "$B/gallery.html"
show "missing asset -> JSON 404" "$B/assets/nothing.js"
printf '%-58s %s\n' "deep link /settings carries the stored theme" "$(curl -s "$B/settings" | grep -o 'data-theme-pref="[a-z]*"')"
printf '%-58s %s\n' "/ after first run" "$(curl -s -o /dev/null -w '%{http_code} %{redirect_url}' "$B/")"
printf '%-58s %s\n' "/ is the app shell (client-side redirect)" "$(curl -s "$B/" | grep -c 'id="root"') root element(s)"
printf '%-58s %s\n' "look-alike host -> 403" "$(curl -s -o /dev/null -w '%{http_code}' -H 'Host: localhost.evil.example:8471' "$B/api/v1/profile")"
printf '%-58s %s\n' "no CORS header on any answer" "$(curl -s -D - -o /dev/null -H 'Origin: http://evil.example' "$B/api/v1/profile" | grep -ci 'access-control' ) access-control headers"
