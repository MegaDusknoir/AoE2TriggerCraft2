import shutil
import subprocess
import zipfile
import os
import sys

def createVersionFile(path: str, verTuple: tuple[int, int, int, int], verStr: str):
    new = f'VERSION_STRING = "{verStr}"\n' \
        + f'VERSION_TUPLE = {verTuple}\n'
    if os.path.isfile(path):
        with open(path, "r") as f:
            old = f.read()
    else:
        old = ''
    if old != new:
        with open(path, "w") as f:
            f.write(new)

def updateVersionTxt(path: str, templatePath: str, verTuple: tuple[int, int, int, int], verStr: str):
    with open(templatePath, "r") as f:
        versionText = f.read()
    versionText = versionText.replace('VERSION_TUPLE', str(verTuple))
    versionText = versionText.replace('VERSION_STRING', f"u'{verStr}'")
    with open(path, "w") as f:
        f.write(versionText)

def git_last_commit_hash(path):
    try:
        hash = subprocess.check_output([
            'git',
            '--git-dir=%s' % os.path.join(path, '.git'),
            '--work-tree=%s' % path,
            'rev-list', 'head', '-1',
        ]).decode('utf-8', 'ignore').strip()
    except (subprocess.CalledProcessError, UnicodeError):
        sys.stderr.write('WARNING: Git hash unavailable\n')
    return hash

def git_last_commit_date(path):
    try:
        date = subprocess.check_output([
            'git',
            '--git-dir=%s' % os.path.join(path, '.git'),
            '--work-tree=%s' % path,
            'log', '-1', r'--format=%cd', r'--date=format:%Y/%m/%d',
        ]).decode('utf-8', 'ignore').strip()
    except (subprocess.CalledProcessError, UnicodeError):
        sys.stderr.write('WARNING: Git date unavailable\n')
    return date

def get_version(path) -> tuple[str, tuple[int, int, int, int]]:
    date = git_last_commit_date(path)
    hash = git_last_commit_hash(path)
    year, month, day = date.split('/')
    versionString = f'{year}/{month}/{day}-g{hash[:7]}'
    versionTuple = (int(year), int(month), int(day), 0)
    return versionString, versionTuple

def get_git_tracked_files(target_dir):
    result = subprocess.run(['git', 'ls-files'], stdout=subprocess.PIPE, text=True)
    files = result.stdout.strip().split('\n')
    return files

DIR_INCLUDING = [
    'resources',
    'images',
    'resources/en_US',
    'resources/zh_CN'
]

if __name__ == '__main__':
    workDir = os.path.dirname(sys.argv[0])

    if os.path.isdir(f'_prebuild') == False:
        os.makedirs(f'_prebuild')
    versionString, versionTuple = get_version(workDir)
    createVersionFile('_prebuild/version.py', versionTuple, versionString)
    updateVersionTxt('_prebuild/version.txt', 'version.txt', versionTuple, versionString)

    result = subprocess.run(f'pyinstaller "{workDir}/main.spec" --distpath "{workDir}/release"', stdout=subprocess.PIPE, text=True)

    if result.returncode != 0:
        print(f'Pyinstaller fail at {result.returncode}')
        exit()

    tracked = get_git_tracked_files(workDir)
    if os.path.isdir(f'{workDir}/release') == False:
        os.makedirs(f'{workDir}/release')
    with zipfile.ZipFile(f"{workDir}/release/TriggerCraft.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for dir in DIR_INCLUDING:
            if os.path.isdir(f'{workDir}/{dir}'):
                for file in os.listdir(f'{workDir}/{dir}'):
                    if f'{dir}/{file}' in tracked:
                        zf.write(f'{workDir}/{dir}/{file}', f'{dir}/{file}')
                        print(f'Write "{workDir}/{dir}/{file}" to "{dir}/{file}"')
        zf.write(f"{workDir}/release/Trigger Craft.exe", "Trigger Craft.exe")
        print(f'Write "Trigger Craft.exe"')
    print(f'Packed')