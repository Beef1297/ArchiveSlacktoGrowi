import requests
import os
# slack の message をクラス化
# thread のメッセージなら _is_thread が True になる
# thread_ts が スレッドのtime stamp
# file だったら private_url が urlに
class slack_message :
    def __init__(self, _message, _slackclient, _username) :
        self.slackclient = _slackclient
        self.message = _message
        self.username = _username
        self.text = self.get_text()
        self.thread_ts = self.getThread_TS() if self.isThread() else None
        self.ts = self.get_ts()
        self.files = self.get_files()
        self.growi_attachments = []
        self.children = [] # thread 下のslack message
    
    def get_text(self) :
        return self.slackclient.replace_userid_to_username(self.message["text"])
        
    def get_ts(self) :
        if ("ts" in self.message) :
            return self.message["ts"]
        else :
            return None
    
    def isThread(self) :
        return "thread_ts" in self.message
    
    def getThread_TS(self) :
        return self.message["thread_ts"]
    
    def get_files(self) :
        full_filenames = []
        if ("files" in self.message) :
            print("getting slack files...")
            for file_info in self.message["files"] :
                if ("url_private" not in file_info) : 
                    full_filenames.append(file_info["mode"])
                    continue
                header = {"Authorization" : "Bearer " + self.slackclient.slack_params["token"]}
                res_file = requests.get(file_info["url_private"], headers=header)
                file_type = file_info["filetype"]
                base_path = "data"
                file_path = ""
                if (file_type == "jpg" or file_type == "png") :
                    file_path = os.path.join(base_path, self.slackclient.channel_name, "img")
                else :
                    file_path = os.path.join(base_path, self.slackclient.channel_name, "others")
                print(file_path)
                if (not os.path.isdir(file_path)) :
                    os.makedirs(file_path)
                filename = file_info["id"] + "." + file_type
                full_filename = os.path.join(file_path, filename)
                
                if (file_path == os.path.join(base_path, self.slackclient.channel_name, "img")) :
                    full_filenames.append(full_filename)

                if (os.path.exists(full_filename)) :
                    print("{} is already exist. so skip save")
                    continue

                with open(full_filename, 'wb') as f :
                    f.write(res_file.content)
        return full_filenames
