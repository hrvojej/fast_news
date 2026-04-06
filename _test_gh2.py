import subprocess, shutil, os

gh = shutil.which("gh")

# Test with a medium-length prompt (simulate real prompt size)
prompt = "Summarize this text in one paragraph with key entities:\n\n" + ("Lorem ipsum dolor sit amet. " * 200)
print(f"Prompt length: {len(prompt)} chars")

# Method: Pass as argument
cmd = [gh, "models", "run", "openai/gpt-4o-mini", "--max-tokens", "200", prompt]
result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, encoding='utf-8')
print(f"Return code: {result.returncode}")
print(f"Stdout ({len(result.stdout)} chars): {result.stdout[:300]}")
print(f"Stderr: {result.stderr[:300]}")
