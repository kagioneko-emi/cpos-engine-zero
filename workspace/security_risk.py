import subprocess
import os

def run_backup(user_provided_path):
    # 危険: shell=True によるコマンドインジェクションの恐れ
    subprocess.run(f"tar -cvf backup.tar {user_provided_path}", shell=True)

def delete_logs():
    # 危険: os.system の使用
    os.system("rm -rf /var/log/*.log")

if __name__ == "__main__":
    run_backup("; rm -rf /")
