import requests
import re
from slack_message import slack_message

class slack :
    # クラス内で import できない？
    def __init__(self, token) :
        self.slack_params = {"token": token}
        self.users = {} # user_id と real_name を簡単にキャッシュしておく
        self.fetch_users_list()
        return
    
    # @param string method : Slack の API method
    # @return API を叩く URL 全体
    def slack_url(self, method) :
        return "https://slack.com/api/{}".format(method)

    # @param
    # @return 辞書型配列 slack のチャンネルのリストを返す  (詳しくは Slack API Method 参照)
    def get_conversations_list(self) :
        res = requests.get(self.slack_url("conversations.list"), params=self.slack_params)
        return res.json()["channels"]

    # @param string channel : チャンネルの名前
    # @return string チャンネルの IDを返す
    def get_channel_id(self, channel) :
        channel_info_list = self.get_conversations_list()
        for channel_info in channel_info_list :
            if (channel_info["name"] == channel) :
                return channel_info["id"] 
        raise Exception(channel + " was not found.")
    
    # @method slack ユーザリストを取得する
    # @param
    # @return user のリストをオブジェクトのプロパティとして取得しておく (簡単なキャッシュのつもり)
    def fetch_users_list(self) :
        res_userslist = requests.get(self.slack_url("users.list"), params=self.slack_params)
        for res in res_userslist.json()["members"] :
            if ("real_name" in res) :
                self.users[res["id"]] = res["real_name"]
            elif ("name" in res) :
                self.users[res["id"]] = res["name"]
        return
    
    # dictionary 型のmessage (response 1単位が渡される)
    def get_user_name(self, message) :
        username = ""
        if ("user" in message) :
            username = self.get_user_name_by_id(message["user"])
        elif ("username" in message) :
            username = message["username"]
        return username
    
    # @ param string user_id : slack の ユーザid
    # @return string name : slack の名前
    def get_user_name_by_id(self, user_id) :
        if (user_id in self.users) :
            return self.users[user_id]
        else :
            params_ = self.slack_params.copy()
            params_["user"] = user_id
            res_user_info = requests.get(self.slack_url("users.info"), params=params_)
            self.users[user_id] = res_user_info.json()["user"]["real_name"]
            return self.users[user_id]
    
    # @param string text : slack メッセージのテキスト (本文)
    # @return string t : メッセージの中から ユーザID を名前に変換したもの
    def replace_userid_to_username(self, text) :
        uid_list = re.findall(r'<@([0-9A-Z]+)>', text)
        t = text
        if (uid_list is not None) :
            for uid in uid_list :
                if (uid in self.users) :
                    t = t.replace(uid, self.users[uid])
                print("replaced.........." + t)

        return t
    
    # slack_message を 配列で返す
    # https://api.slack.com/methods/channels.history
    # get request で メッセージの最大取得数は 1000
    # 1000 以上メッセージがある場合は，リクエストを複数回投げないといけない
    # また，取得した後に メッセージは slack_message の instance として保存していき，
    # スレッドは，children に追加していく．最新のメッセージから取得されるので時系列順に並べるために
    # 逆から参照するようにしている
    # 同じ thread_ts を持つもので，一番時系列が古いものを親として考える．
    def fetch_channel_messages(self, channel, oldest_ts) :

        channel_id = self.get_channel_id(channel)
        params_ = self.slack_params.copy()
        params_["channel"] = channel_id
        params_["count"] = 1000
        params_["oldest"] = oldest_ts or 0
        all_messages = []
        thread_ts_dict = {}
        
        while(True) :
            print("fetching channel messages...")
            messages = []
            res_fetch = requests.get(self.slack_url("channels.history"), params=params_)
            fetch_messages = res_fetch.json()["messages"]
            for i in range(len(fetch_messages)-1, -1, -1) :
                if "thread_ts" in fetch_messages[i] :
                    if fetch_messages[i]["thread_ts"] in thread_ts_dict :
                        # ここの username の取り扱いがすごい面倒
                        # もっときれいに書きたい
                        # そもそも，slackclient が id と name の対応を持っているならここでわざわざ username を渡す必要はない
                        username = self.get_user_name(fetch_messages[i])
                        sm = slack_message(fetch_messages[i], self, username)
                        messages[thread_ts_dict[fetch_messages[i]["thread_ts"]]].children.append(sm)
                        #print(fetch_messages[i])
                    else :
                        username= self.get_user_name(fetch_messages[i])
                        messages.append(slack_message(fetch_messages[i], self, username))
                        thread_ts_dict[fetch_messages[i]["thread_ts"]] = len(messages)-1
                else :
                    messages.append(slack_message(fetch_messages[i], self, self.get_user_name(fetch_messages[i])))
                    
            #print(res_fetch.json()["has_more"])
            
            all_messages = messages + all_messages
            if (res_fetch.json()["has_more"]) :
                params_["latest"] = fetch_messages[0]["ts"]
            else :
                break

        return all_messages
