---
name: clipboard
description: Copy content to the OS clipboard via the platform-appropriate CLI (pbcopy / Set-Clipboard / clip.exe / wl-copy). No arg = most recent artifact.
user-invocable: true
---

Args: $ARGUMENTS

Copy content to the user's clipboard via the OS-appropriate CLI rather than printing it and asking them to copy it manually.

## How to reason

1. Determine the content to copy:
   - If $ARGUMENTS contains the literal content, use it as-is.
   - If $ARGUMENTS describes what to copy (e.g. "the draft reply", "the KB article", "the last command"), pick the most recent matching artifact from the conversation.
   - If $ARGUMENTS is empty, copy the most recent generated artifact (draft reply, KB article, feature request, command, code block, etc.). If there are multiple plausible candidates, ask which one before piping.
2. Detect the OS and pipe the content in. Avoid any form that appends a trailing newline.

   **macOS** (`uname -s` = `Darwin`) - pipe into `pbcopy`. Use `printf '%s'` (not `echo`) and a heredoc for multi-line content:

   ```
   printf '%s' "<content>" | pbcopy
   ```

   ```
   cat <<'EOF' | pbcopy
   line one
   line two
   EOF
   ```

   **Linux** (`uname -s` = `Linux`) - check for WSL first (`grep -qi microsoft /proc/version 2>/dev/null`).

   - **WSL:** use `clip.exe` (always available; copies to the Windows clipboard).
     ```
     printf '%s' "<content>" | clip.exe
     ```
   - **Native Linux:** prefer `wl-copy` (Wayland); fall back to `xclip` or `xsel` if `wl-copy` is unavailable or the session is X11.
     ```
     printf '%s' "<content>" | wl-copy
     ```

   **Windows** (`OS` = `Windows_NT`) - use PowerShell, not POSIX shell. `printf` and `<<'EOF'` heredocs are not available. For single-line content:

   ```
   Set-Clipboard -Value '<content>'
   ```

   For multi-line content, use a PowerShell here-string piped into `Set-Clipboard`:

   ```
   @'
   line one
   line two
   '@ | Set-Clipboard
   ```

   The cmd.exe fallback is `echo <content> | clip`, which always appends a trailing newline; only use it if PowerShell is unavailable.

3. If the required tool is not installed, say so and suggest the install command rather than silently substituting a different tool (e.g. on Linux: `sudo apt install wl-clipboard`).

4. Confirm briefly what was copied (one short line, e.g. `Copied draft reply to clipboard.`). Do not echo the full content back.
