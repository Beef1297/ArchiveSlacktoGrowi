import requests
import os
import sys
import json
from datetime import datetime
from slack_client import slack
from growi_client import growi
from slack_message import slack_message


# growi page 制作のために，slack から取得したメッセージを整形
# 最新メッセージが一番最初に保存されているので，逆順にみていく

def formatting_messages(title, messages, slackclient) :
    print("formatting messages...")
    formattedMessages = title + "\n"
    for message in messages :
        m = slackclient.replace_userid_to_username(message.text)
        formattedMessages += "\n- " + message.username + ": " + str(datetime.fromtimestamp(int(float(message.ts))))+"\n"+ m + "\n"
        for attachment in message.growi_attachments :
            if (attachment is not "hidden_by_limit") :
                formattedMessages += "\n<img src={} width=50% />\n".format(attachment)
            else :
                formattedMessages += "\n`hidden_by_limit image`\n"
            #formattedMessages += "![" + attachment + "](" + attachment + ")\n" 
        
        for child_message in message.children :
            formattedMessages += "\n- |→ " + child_message.username + ": " + str(datetime.fromtimestamp(int(float(message.ts))))+"\n" + child_message.text + "\n"
            
            if (attachment is not "hidden_by_limit") :
                formattedMessages += "\n<img src={} width=50% />\n".format(attachment)
            else :
                formattedMessages += "\n`hidden_by_limit image`\n"
 
    
    # Timestamp の追加
    # TODO: response の latest key と上手く兼ね合わせて単純にしたい
    if (len(messages[-1].children) > 0) :
        formattedMessages += "<{}>\n".format(messages[-1].children[-1].ts)
    else :
        formattedMessages += "<{}>\n".format(messages[-1].ts)
        
    return formattedMessages

if __name__ == "__main__" :
    # slack, growi object はsingleton のように扱う
    with open("token.json", 'r') as token_file :
        tokens = json.load(token_file)

    channel_name = ""
    if (len(sys.argv) > 1) :
        channel_name = sys.argv[1]
    if (channel_name == "") :
        channel_name = input() #python3

    log_path = "/Log/slack_channel/"
    path = log_path + channel_name
    growi = growi(tokens["growi"]["token"])
    slack = growi(tokens["slack"]["token"])
    messages = slack.fetch_channel_messages(channel_name)
    '''
    for m in messages :
        print(m.text)
        for c in m.children :
            print(c.text)
    '''
    # FIXME: Create -> Update は無駄
    growi.create_page("just making a page", path)
    for message in messages :
        for file in message.files :
            message.growi_attachments.append(growi.upload_attachment(path, file))
        for child_message in message.children :
            for file in child_message.files :
                child_message.growi_attachments.append(growi.upload_attachment(path, file))
    formattedMessages = formatting_messages("# Archive: " + channel_name, messages, slack)
    res = growi.update_page(formattedMessages, path)
