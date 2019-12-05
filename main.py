import requests
import os
import sys
import json
import argparse
from datetime import datetime
from slack_client import slack
from growi_client import growi
from slack_message import slack_message


HIDDEN_BY_LIMIT = "hidden_by_limit" # 制限によって削除されたもの
TOMBSTONE = "tombstone" #ユーザによって削除されたファイル

def _is_hidden_or_deleted(attachment) :
    return attachment is not HIDDEN_BY_LIMIT and attachment is not TOMBSTONE

def _file_text_mdtype(attachment) :
    if attachment is HIDDEN_BY_LIMIT :
        return "\n`hidden_by_limit`\n"
    elif attachment is TOMBSTONE :
        return "\ntombstone (削除されました)\n"
    else :
        return "\n<img src={} width=50% />\n".format(attachment)

def _message_text_mdtype(slackclient, message, is_thread) :
    m = slackclient.replace_userid_to_username(message.text)
    if not is_thread :
        return "\n- " + message.username + ": " + str(datetime.fromtimestamp(int(float(message.ts))))+"\n"+ m + "\n"
    else :
        return "\n- |→ " + message.username + ": " + str(datetime.fromtimestamp(int(float(message.ts))))+"\n" + m + "\n"

# growi page 制作のために，slack から取得したメッセージを整形
# 最新メッセージが一番最初に保存されているので，逆順にみていく
# TODO: 正規表現をつかって簡潔に書きたい, マジックナンバー(string) をなくす
def formatting_messages(body, messages, slackclient) :
    print("formatting messages...")
    if (len(messages) <= 0) :
        raise(Exception("There is no messages for create/update"))
    for message in messages :
        body += _message_text_mdtype(slackclient, message, False)
        for attachment in message.growi_attachments :
            body += _file_text_mdtype(attachment)
        
        for child_message in message.children :
            body += _message_text_mdtype(slackclient, message, True)

            for attachment in child_message.growi_attachments : 
                body += _file_text_mdtype(attachment)
 
    # Timestamp の追加
    # TODO: response の latest key と上手く兼ね合わせて単純にしたい
    if (len(messages[-1].children) > 0) :
        body += "\n<{}>".format(messages[-1].children[-1].ts)
    else :
        body += "\n<{}>".format(messages[-1].ts)
        
    return body

def create_log_page(path, growi, slack, messages) :
    # ファイルアップロード
    # ページがない場合は Growi 側で自動的に作成される - ファイルアップロードで作成した場合鍵付きになってしまう
    # FIXME: 二度手間
    growi.create_page("creating page....", path)

    for message in messages :
        for file in message.files :
            message.growi_attachments.append(growi.upload_attachment(path, file))
        for child_message in message.children :
            for file in child_message.files :
                child_message.growi_attachments.append(growi.upload_attachment(path, file))

    body = "# Archive: {}\n".format(channel_name)
    body = formatting_messages(body, messages, slack)
    res = growi.create_page(body, path)
    return res

def update_log_page(path, growi, slack, messages) :
    for message in messages :
        for file in message.files :
            message.growi_attachments.append(growi.upload_attachment(path, file))
        for child_message in message.children :
            for file in child_message.files :
                child_message.growi_attachments.append(growi.upload_attachment(path, file))
    body = formatting_messages("", messages, slack)
    res = growi.update_page(body, path, growi.update_mode.APPEND)
    return res


if __name__ == "__main__" :
    # slack, growi object はsingleton のように扱う
    with open("token.json", 'r') as token_file :
        tokens = json.load(token_file)

    argparser = argparse.ArgumentParser(description="slack のチャンネルメッセージを Growi ページとしてアーカイブする")
    argparser.add_argument("channel_name", help="slack のチャンネル名")
    argparser.add_argument("--page_name", help="growi のページ名．指定しない場合は channel_name になる")
    argparser.add_argument("--custom_oldest_ts", help="oldest_ts を指定する．Growi ページの ts は使わずに強制的に指定した ts でメッセージ取得する")

    args = argparser.parse_args()
    channel_name = args.channel_name
    page_name = args.page_name
    custom_oldest_ts = args.custom_oldest_ts

    if (page_name is None) :
        print("input growi page name")
        page_name = channel_name
    
    log_path = "/Log/slack_channel/"
    path = log_path + page_name
    g = growi(tokens["growi"]["token"])
    s = slack(tokens["slack"]["token"])

    is_exist, oldest_ts = g.check_if_page_exist(path)
    if oldest_ts == "" :
        oldest_ts = "0"
    if custom_oldest_ts is not None :
        oldest_ts = custom_oldest_ts

    print(oldest_ts)
    if (is_exist) :
        print("{} is exist. update growi page".format(path))
        messages = s.fetch_channel_messages(channel_name, oldest_ts)
        update_log_page(path, g, s, messages)
    else :
        print("create growi page")
        messages = s.fetch_channel_messages(channel_name, oldest_ts)
        create_log_page(path, g, s, messages)