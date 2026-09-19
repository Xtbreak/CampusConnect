"""首次运行配置向导：凭据只写入本地 credentials.json，不进入 Git。"""
import getpass
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main():
    config_path = ROOT / 'config.json'
    example = ROOT / 'config.example.json'
    if not config_path.exists():
        config_path.write_text(example.read_text(encoding='utf-8'), encoding='utf-8')
        print('已从 config.example.json 创建 config.json；如学校地址不同，请先编辑它。')

    account = input('请输入学号/账号：').strip()
    token = getpass.getpass('请输入校园网密码或 Token（输入不回显）：').strip()
    if not account or not token:
        raise SystemExit('账号和 Token 不能为空。')

    credentials_path = ROOT / 'credentials.json'
    credentials_path.write_text(
        json.dumps({'account': account, 'token': token}, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    print(f'配置完成：{credentials_path}')
    print('请确认 credentials.json 已被 .gitignore 忽略，然后运行：python AutoConnect.py --login-once')


if __name__ == '__main__':
    main()
