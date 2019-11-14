# Slack データ を Growi にアーカイブ

- 将来的に channel 履歴だけじゃなくてメタ的な情報も Log として自動的に残す

## About access token

- `token.json` として別ファイルに保存して利用．{"slack": {"token": SLACK_TOKEN}, "growi": {"token": GROWI_TOKEN}} という形

## How to use

- python3 系
  - 開発環境は python3.7

- `python main.py 'slackチャンネル名'`
  - アクセストークンをちゃんと設定すればこれで動くはず

## TODO

- Growi Page (チャンネルアーカイブ計画) 参照 