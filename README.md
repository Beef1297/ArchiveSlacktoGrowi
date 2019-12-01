# Slack データ を Growi にアーカイブ

- 将来的に channel 履歴だけじゃなくてメタ的な情報も Log として自動的に残す

## About access token

- `token.json` として別ファイルに保存して利用．
```
{
    "slack": {
        "token": SLACK_TOKEN
    }, 
    "growi": {
        "token": GROWI_TOKEN
    }
} 
```
という形

## How to use

- python3 系
  - 開発環境は python3.7

- `python main.py 'slackチャンネル名' --page_name 'growi page 名' --custom_oldest_ts '一番古いslack message ts (unix time)'`
  - アクセストークンをちゃんと設定すればこれで動くはず
  - --page_name: 指定しなければ `slackチャンネル名` がページ名になる
  - --custom_oldest_ts: 基本は指定しない．イレギュラーで slack message の oldest を変更する必要がある時のみ

## Docker

- Lab Synology 上に試験的に container を作成 (DockerFile 作成中)

```
$ docker container ls (-a) # alpine container のid を確認
# もしup 状態でなかったら
($ docker start [container id])
$ docker attach [container id]
--- docker container 内部 -----
~/src # python3 main.py ~~~ (How to use 参照)
```

## TODO

- Growi Page (チャンネルアーカイブ計画) 参照 