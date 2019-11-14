import requests
import os
# slack の message をクラス化
# thread のメッセージなら _is_thread が True になる
# thread_ts が スレッドのtime stamp
# file だったら private_url が urlに
class SlackMessage :
    def __init__(self, _message, _slackclient, _username) :
        self.slackclient = _slackclient
        self.message = _message
        self.username = _username
        self.text = self.getText()
        self.thread_ts = self.getThread_TS() if self.isThread() else None
        self.ts = self.getTS()
        self.files = self.getFiles()
        self.growi_attachments = []
        self.children = [] # thread 下のslack message
    
    def getUserName(self) :
        username = ""
        if ("user" in self.message) :
            username = self.getUserNamebyId(self.message["user"])
        elif ("username" in self.message) :
            username = self.message["username"]
        return username
    
    def getUserNamebyId(self, user_id) :
        params_ = self.slackclient.slack_params.copy()
        params_["user"] = user_id
        res_user_info = requests.get(self.slackclient.slack_url("users.info"), params=params_)
        return res_user_info.json()["user"]["real_name"]
    
    def getText(self) :
        return self.slackclient.replaceUserIdtoUserName(self.message["text"])
        
    def getTS(self) :
        if ("ts" in self.message) :
            return self.message["ts"]
        else :
            return None
    
    def isThread(self) :
        return "thread_ts" in self.message
    
    def getThread_TS(self) :
        return self.message["thread_ts"]
    
    def getFiles(self) :
        full_filenames = []
        if ("files" in self.message) :
            for file_info in self.message["files"] :
                if ("url_private" not in file_info) : 
                    full_filenames.append(file_info["mode"])
                    continue
                header = {"Authorization" : "Bearer " + self.slackclient.slack_params["token"]}
                res_file = requests.get(file_info["url_private"], headers=header)
                file_type = file_info["filetype"]
                file_path = "data"
                if (file_type == "jpg" or file_type == "png") :
                    file_path = "img"
                filename = file_info["id"] + "." + file_type
                full_filename = os.path.join(file_path, filename)
                
                if (file_path == "img") :
                    full_filenames.append(full_filename)
                
                with open(full_filename, 'wb') as f :
                    f.write(res_file.content)
        return full_filenames

    def replaceIdtoName(self) :
        pass
    
