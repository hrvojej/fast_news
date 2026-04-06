import subprocess, tempfile, os, shutil

gh = shutil.which("gh")
prompt = "Summarize in one paragraph: US president Donald Trump has been invited to meet King Charles in Scotland."

# Method 1: Write to temp file, open as stdin (same as summarizer_api.py)
tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
tmp.write(prompt)
tmp.close()

cmd = [gh, "models", "run", "openai/gpt-4o-mini"]
print(f"Command: {' '.join(cmd)}")
print(f"Temp file: {tmp.name}")
print(f"Temp file contents ({os.path.getsize(tmp.name)} bytes):")
with open(tmp.name, 'r', encoding='utf-8') as f:
    content = f.read()
    print(repr(content[:200]))

print("\n--- Running with stdin from file ---")
with open(tmp.name, 'r', encoding='utf-8') as f:
    result = subprocess.run(cmd, stdin=f, capture_output=True, text=True, timeout=60, encoding='utf-8')

print(f"Return code: {result.returncode}")
print(f"Stdout ({len(result.stdout)} chars): {repr(result.stdout[:500])}")
print(f"Stderr ({len(result.stderr)} chars): {repr(result.stderr[:500])}")
os.unlink(tmp.name)

# Method 2: Pass prompt as argument
print("\n--- Running with prompt as argument ---")
cmd2 = [gh, "models", "run", "openai/gpt-4o-mini", prompt]
result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=60, encoding='utf-8')
print(f"Return code: {result2.returncode}")
print(f"Stdout ({len(result2.stdout)} chars): {repr(result2.stdout[:500])}")
print(f"Stderr ({len(result2.stderr)} chars): {repr(result2.stderr[:500])}")
