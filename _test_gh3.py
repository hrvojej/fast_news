import subprocess, shutil, sys, os
sys.path.insert(0, os.path.join('news_aggregator', 'nlp', 'summarizer'))
sys.path.insert(0, 'news_aggregator')

from summarizer_path_config import configure_paths
configure_paths()
from summarizer_prompt import create_prompt

gh = shutil.which("gh")

# Generate a realistic prompt
test_content = """US president Donald Trump has been invited to meet King Charles in Scotland to discuss 
an unprecedented second state visit to the UK. An official letter from the monarch, delivered by Prime Minister 
Sir Keir Starmer on Thursday, offered a meeting at either Dumfries House in Ayrshire or Balmoral Castle. 
The invitation was extended during a diplomatic exchange focused on strengthening US-UK relations.""" * 5

prompt = create_prompt(test_content, len(test_content))
print(f"Full prompt length: {len(prompt)} chars")

# Test as CLI argument
cmd = [gh, "models", "run", "openai/gpt-4o-mini", "--max-tokens", "200", prompt]
print(f"Command line total length: {sum(len(a) for a in cmd)} chars")

result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, encoding='utf-8')
print(f"Return code: {result.returncode}")
print(f"Stdout ({len(result.stdout)} chars): {result.stdout[:400]}")
print(f"Stderr: {result.stderr[:300]}")
