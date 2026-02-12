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

def reader(stream, label):
    while True:
        line = stream.readline()
        if not line:
            break
        text = line.decode('utf-8', errors='replace').strip()
        if text:
            with open(r'C:\Users\Admin\bedcode\test_stream4_out.txt', 'a', encoding='utf-8') as f:
                f.write(f'[{label}] {text}\n')

t1 = threading.Thread(target=reader, args=(p.stdout, 'OUT'), daemon=True)
t2 = threading.Thread(target=reader, args=(p.stderr, 'ERR'), daemon=True)
t1.start()
t2.start()

time.sleep(3)

# 尝试不同的格式
formats = [
    {"type": "user", "role": "user", "content": "say hi"},
    {"role": "user", "content": [{"type": "text", "text": "say hi"}]},
    {"type": "human", "message": {"role": "user", "content": [{"type": "text", "text": "say hi"}]}},
]

for i, fmt in enumerate(formats):
    msg = json.dumps(fmt, ensure_ascii=False) + "\n"
    with open(r'C:\Users\Admin\bedcode\test_stream4_out.txt', 'a', encoding='utf-8') as f:
        f.write(f'[SEND-{i}] {msg}')
    try:
        p.stdin.write(msg.encode('utf-8'))
        p.stdin.flush()
    except:
        break
    time.sleep(5)

time.sleep(20)

with open(r'C:\Users\Admin\bedcode\test_stream4_out.txt', 'a', encoding='utf-8') as f:
    f.write(f'\n=== RC: {p.poll()} ===\n')

print("Done")
