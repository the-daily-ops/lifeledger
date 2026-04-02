#!/bin/bash
TITLE="$1"
MESSAGE="$2"
osascript -e "display notification \"$MESSAGE\" with title \"$TITLE\" sound name \"Glass\""
