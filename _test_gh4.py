import subprocess, shutil, tempfile, os

gh = shutil.which("gh")
prompt = "Summarize in one paragraph: US president Donald Trump has been invited to meet King Charles in Scotland."

# Test using subprocess.PIPE for stdin instead of file
cmd = [gh, "models", "run", "openai/gpt-4o-mini", "--max-tokens", "200"]
result = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=60, encoding='utf-8')
print(f"Method PIPE input:")
print(f"  Return code: {result.returncode}")
print(f"  Stdout ({len(result.stdout)} chars): {result.stdout[:300]}")
print(f"  Stderr: {result.stderr[:200]}")
