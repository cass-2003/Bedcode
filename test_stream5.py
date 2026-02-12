import subprocess, os, json, time, threading

env = os.environ.copy()
env['CLAUDE_CODE_GIT_BASH_PATH'] = r'H:\Git\bin\bash.exe'

# 方式: prompt 作为参数，不用 stdin
p = subprocess.Popen(
    ['claude.cmd', '-p', '--output-format', 'stream-json', '--verbose', 'say hello in one word'],
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
            with open(r'C:\Users\Admin\bedcode\test_stream5_out.txt', 'a', encoding='utf-8') as f:
                f.write(f'[{label}] {text}\n')

t1 = threading.Thread(target=reader, args=(p.stdout, 'OUT'), daemon=True)
t2 = threading.Thread(target=reader, args=(p.stderr, 'ERR'), daemon=True)
t1.start()
t2.start()

p.wait(timeout=30)

with open(r'C:\Users\Admin\bedcode\test_stream5_out.txt', 'a', encoding='utf-8') as f:
    f.write(f'\n=== RC: {p.returncode} ===\n')

print("Done")
