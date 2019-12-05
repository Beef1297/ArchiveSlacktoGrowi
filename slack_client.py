import requests
import re
from slack_message import slack_message
from enum import Enum

class slack :
    # クラス内で import できない？
    class api_methods(Enum) :
        CONVERSATIONS_LIST = "conversations.list"
        USERS_LIST = "users.list"
        USERS_INFO = "users.info"
        CHANNELS_HISTORY = "channels.history"
        
    def __init__(self, token) :
        self.slack_params = {"token": token}
        self.users = {} # user_id と real_name を簡単にキャッシュしておく
        self.channel_name = ""
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
        self.channel_name = channel
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
    
    # @param res_msg_list: slack api - channels history の response内の "messages" list 
    # @return それぞれの "message" より作成したslack_message インスタンスのリスト
    # thread は親メッセージの child_messsages に含まれる．
    def _reverse_slack_messages_by_ts(self, res_msg_list) :
        messages = []
        thread_ts_dict = {}
        print("instantiating slack messages...")
        # slack message は新しい方から順に来るため
        for i in range(len(res_msg_list)-1, -1, -1) :
            if "thread_ts" in res_msg_list[i] :
                if res_msg_list[i]["thread_ts"] in thread_ts_dict :
                    # ここの username の取り扱いがすごい面倒
                    # もっときれいに書きたい
                    # そもそも，slackclient が id と name の対応を持っているならここでわざわざ username を渡す必要はない
                    username = self.get_user_name(res_msg_list[i])
                    sm = slack_message(res_msg_list[i], self, username)
                    messages[thread_ts_dict[res_msg_list[i]["thread_ts"]]].children.append(sm)
                    #print(res_msg_list[i])
                else :
                    username= self.get_user_name(res_msg_list[i])
                    messages.append(slack_message(res_msg_list[i], self, username))
                    thread_ts_dict[res_msg_list[i]["thread_ts"]] = len(messages)-1
            else :
                messages.append(slack_message(res_msg_list[i], self, self.get_user_name(res_msg_list[i])))
        return messages

    # slack_message を 配列で返す
    # https://api.slack.com/methods/channels.history
    # get request で メッセージの最大取得数は 1000
    # 1000 以上メッセージがある場合は，リクエストを複数回投げないといけない
    # また，取得した後に メッセージは slack_message の instance として保存していき
    # 同じ thread_ts を持つもので，一番時系列が古いものを親として考える．
    def fetch_channel_messages(self, channel, oldest_ts) :

        self.channel_name = channel
        channel_id = self.get_channel_id(channel)
        params_ = self.slack_params.copy()
        params_["channel"] = channel_id
        params_["count"] = 1000
        params_["oldest"] = oldest_ts or "0"

        
        print("fetching slack channel messages...")
        res_msg_list = []
        # ファイルの保存などは，既にある場合は取得しないなどにすれば時間もかからないはず
        # メッセージ取得して，更新分だけ抽出し使用するというのが綺麗になりそう
        while(True) :
            res_channels_history = requests.get(self.slack_url(self.api_methods.CHANNELS_HISTORY.value), params=params_)

            if (params_["oldest"] == "0") :
            # oldest が設定されてないときは latest によった messages が取得されるので (Slack API Method 参照)
            # 最古のメッセージの ts を最新とすることで，さらに前にさかのぼることができる              
                res_msg_list = res_msg_list + res_channels_history.json()["messages"]
                if (res_channels_history.json()["has_more"]) :
                    print("setting latest ts")
                    params_["latest"] = res_msg_list[-1]["ts"]
                else :
                    break
            else :
            # oldest が設定されている時, 本プログラムでは latest を設定することは上の時しかない. 上の時は基本的に 新規にページを作成する時
            # 更新する時は，基本 oldest を設定する．だから取得したメッセージの最新ts を oldest にすることで新しいメッセージを取得できる．               
                res_msg_list = res_channels_history.json()["messages"] + res_msg_list
                if (res_channels_history.json()["has_more"]) :
                    print("setting oldest ts")
                    params_["oldest"] = res_msg_list[0]["ts"]
                else :
                    break
        messages = self._reverse_slack_messages_by_ts(res_msg_list)
        
                
        return messages
