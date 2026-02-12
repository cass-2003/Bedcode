import subprocess, os, sys, time

env = os.environ.copy()
env['CLAUDE_CODE_GIT_BASH_PATH'] = r'H:\Git\bin\bash.exe'
env['PYTHONIOENCODING'] = 'utf-8'

p = subprocess.Popen(
    ['claude.cmd', '-p', '--output-format', 'stream-json', '--verbose', 'say hello'],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    cwd=r'C:\Users\Admin',
    env=env,
)

time.sleep(30)

out = p.stdout.read(16384)
err = p.stderr.read(4096)

with open(r'C:\Users\Admin\bedcode\test_stream_out.txt', 'wb') as f:
    f.write(b'=== STDOUT ===\n')
    f.write(out)
    f.write(b'\n=== STDERR ===\n')
    f.write(err)
    f.write(f'\n=== RC: {p.poll()} ===\n'.encode())

print("Done, check test_stream_out.txt")
