---
description: Copy content to the OS clipboard via the platform-appropriate CLI (pbcopy / Set-Clipboard / wl-copy).
argument-hint: [content or description of what to copy]
---

Args: $ARGUMENTS

Copy content to the user's clipboard via the OS-appropriate CLI rather than printing it and asking them to copy it manually.

## How to reason

1. Determine the content to copy:
   - If $ARGUMENTS contains the literal content, use it as-is.
   - If $ARGUMENTS describes what to copy (e.g. "the draft reply", "the KB article", "the last command"), pick the most recent matching artifact from the conversation.
   - If $ARGUMENTS is empty, copy the most recent generated artifact (draft reply, KB article, feature request, command, code block, etc.). If there are multiple plausible candidates, ask which one before piping.
2. Detect the OS and pick the clipboard CLI:
   - macOS (`uname -s` = `Darwin`): `pbcopy`
   - Linux (`uname -s` = `Linux`): `wl-copy` (from the `wl-clipboard` package). Prefer this over `xclip`/`xsel` even when both are installed.
   - Windows (`OS` = `Windows_NT`): PowerShell `Set-Clipboard -Value '<content>'`, or cmd `echo <content> | clip`.
3. Pipe the content in. Use `printf '%s'` (not `echo`) to avoid an unwanted trailing newline. For multi-line content, use a heredoc:

   ```
   printf '%s' "<content>" | pbcopy
   ```

   ```
   cat <<'EOF' | pbcopy
   line one
   line two
   EOF
   ```

4. If the required tool is not installed, say so and suggest the install command rather than silently substituting a different tool (e.g. on Linux: `sudo apt install wl-clipboard`).

5. Confirm briefly what was copied (one short line, e.g. `Copied draft reply to clipboard.`). Do not echo the full content back.
