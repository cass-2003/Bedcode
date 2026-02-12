import subprocess, os, json, time, threading

env = os.environ.copy()
env['CLAUDE_CODE_GIT_BASH_PATH'] = r'H:\Git\bin\bash.exe'

p = subprocess.Popen(
    ['claude.cmd', '-p', '--output-format', 'stream-json',
     '--input-format', 'stream-json', '--verbose'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    cwd=r'C:\Users\Admin',
    env=env,
)

# 读取线程
def reader():
    while True:
        line = p.stdout.readline()
        if not line:
            break
        text = line.decode('utf-8', errors='replace').strip()
        if text:
            with open(r'C:\Users\Admin\bedcode\test_stream2_out.txt', 'a', encoding='utf-8') as f:
                f.write(text + '\n')

t = threading.Thread(target=reader, daemon=True)
t.start()

# 写入消息
time.sleep(2)
msg = json.dumps({"type": "user", "content": "say hello in one word"}, ensure_ascii=False) + "\n"
p.stdin.write(msg.encode('utf-8'))
p.stdin.flush()

# 等待响应
time.sleep(30)

with open(r'C:\Users\Admin\bedcode\test_stream2_out.txt', 'a', encoding='utf-8') as f:
    f.write(f'\n=== RC: {p.poll()} ===\n')

print("Done")
