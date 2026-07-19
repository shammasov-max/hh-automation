#!/bin/bash
# Барьер внешних эффектов (введён@2026-07-19 по аудиту): любой Bash с "--send"
# (apply.py / chat_send.py / chat_leave.py — реальные POST работодателям)
# требует подтверждения человека, даже в auto-режиме permissions.
# Dry-run'ы (без --send) проходят бесшумно.
input=$(cat)
cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // ""' 2>/dev/null)
case "$cmd" in
  *--send*)
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"Внешняя отправка на hh.ru (--send). Подтверди явно."}}'
    ;;
esac
exit 0
