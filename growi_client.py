# クラス内で import できない？
import requests
import re
from enum import Enum, auto

class growi :

    class update_mode(Enum) :
        APPEND = auto()
        OVERWRITE = auto()

    class api_methods(Enum) :
        PAGES_UPDATE = "pages.update"
        PAGES_CREATE = "pages.create"
        PAGES_GET = "pages.get"

    def __init__(self, access_token) :
        self.growi_params = {"access_token": access_token, "user": "admin"}
        self.pages_list = {}
        return 
    
    # @param string method : Growi の API メソッド
    # @return API を叩くためのURL
    def growi_url(self, method) :
        return "http://192.168.1.71:3333/_api/{}".format(method)

    # @param string body : ページ本文
    # @param string path : growi のページの path ex) /Log/hogehoge/fugafuga
    # @caution path の 先頭に slash をつけないとページからは参照できなくなってしまう
    # @return string status 辞書型配列(?) : ページ作成成功したか
    # TODO: パスに既にページがある場合はerror を返す
    def create_page(self, body, path) :
        print("creating growi page...")
        # 先頭に slash は必ずつける
        if not path.startswith("/") :
            path = "/" + str(path)
        page_info = self.get_page_info(path)
        if (page_info) :
            # createで競合した際は全て上書きするようにする
            print("{} is exist".format(path))
            result =  self.update_page(body, path, self.update_mode.OVERWRITE)
            return result
        else :
            payload = {"body": body, "path": path}
            print(self.api_methods.PAGES_CREATE.value)
            res_post = requests.post(self.growi_url(self.api_methods.PAGES_CREATE.value), params=self.growi_params, data=payload)
            return res_post.json()['page']['status']

    # @param string body : ページ本文
    # @param string path : 更新するページのパス
    # @return string status : update 成功したか
    # TODO: 書き換えるか，追記するか選択できるようにする
    # TODO: Body をハッシュ化して更新するかどうかの判定
    def update_page(self, body, path, mode) :
        is_exist, _ = self.check_if_page_exist(path)
        if not is_exist :
            raise(Exception("can not update non-exist page {}".format(path)))
        print("updating growi page...")
        info = self.get_page_info(path)
        # print(info)
        if info is None :
            raise(Exception("can not get page info '{}'".format(path)))
        page_id, revision_id, latest_ts, old_body = info
        #print(old_body)
        if (mode is self.update_mode.APPEND) :
            print("APPEND MODE")
            body = old_body + "\n" + body
            payload = {"body": body, "page_id": page_id, "revision_id": revision_id}
            res_pages_update = requests.post(self.growi_url(self.api_methods.PAGES_UPDATE.value), params=self.growi_params, data=payload)
            #print(res_pages_update.json())
            return res_pages_update.json()["page"]["status"]
        elif (mode is self.update_mode.OVERWRITE) :
            print("OVERWRITE MODE")
            payload = {"body": body, "page_id": page_id, "revision_id": revision_id}
            res_pages_update = requests.post(self.growi_url(self.api_methods.PAGES_UPDATE.value), params=self.growi_params, data=payload)
            print(res_pages_update.json())
            return res_pages_update.json()['page']['status']

    # @param string path : ページのパス
    # @return string タプル (page_id, revision_id) : revision_id は更新に必要
    def get_page_info(self, path) :
        print("getting growi page info..")
        params_ = self.growi_params.copy()
        params_["path"] = path
        res_pages_get = requests.get(self.growi_url(self.api_methods.PAGES_GET.value), params=params_)
        #print(res_pages_get.json())
        if (res_pages_get and res_pages_get.json()["ok"]) :
            data = res_pages_get.json()
            # page の内容
            full_body = data["page"]["revision"]["body"]
            pattern_body = r"((.|\\s)*)\n"
            pattern_ts   = r"<([0-9]+\.?[0-9]+)>$"    # 行末 0-9数字とdot
            ro_body = re.search(pattern_body, full_body)
            ro_ts   = re.search(pattern_ts, full_body)

            latest_ts = ""
            body = ""
            if (ro_body) :
                print(ro_body)
                body = ro_body.group(1)
            if (ro_ts) :
                latest_ts = ro_ts.group(1)

            if (data["ok"]) :
                return (data["page"]["id"], data["page"]["revision"]["_id"], latest_ts, body)
            else :
                raise(Exception("can not get page_info because of something wrong, check path, params"))
        else :
            print("{} may not exist. or check your access right".format(path))
            return None

    
    # 渡されたpath に growi page があるか確認する
    # @param string path : growi page の path
    # @return boolean is_exist, string timestamp
    def check_if_page_exist(self, path) :
        info = self.get_page_info(path)
        if info :
            page_id, revision_id, latest_ts, _ = info
            return (True, latest_ts)
        else :
            return (False, None)

    # @param string path : 既存のページのパス
    # @param string _new_path : 新規ページのパス
    # @return request.post の返り値そのまま 
    # TODO パラメータの名前, 返り値
    def rename_page(self, path, _new_path) :
        _page_id, _revision_id, _latest_ts, _ = self.get_page_info(path)
        payload = {"page_id": _page_id, "new_path": _new_path, "revision_id": _revision_id}
        res_rename = requests.post(self.growi_url("pages.rename"), params=self.growi_params, data=payload)
        return res_rename

    # FIXME API ではページ削除は不可能？
    # 使ってません
    # @param string path : 削除するページのパス
    # @return 辞書型配列 server response
    def delete_page(self, path) :
        _page_id, _revision_id, _, _ = self.get_page_info(path)
        payload = {"page_id": _page_id, "revision_id": _revision_id}
        res_remove = requests.post(self.growi_url("pages.remove"), params=self.growi_params, data=payload)
        return res_remove
    
    # FIXME: Content-Type header を上手く指定できないためか img をupload しても growi page では text/plain になってしまう
    # @param string path : ファイルをアップロードするページのパス
    # @param string file_path : アップロードするローカルファイルのパス
    # @return string attachment_path : growi におけるアップロードしたファイルのパス (ex: /attachment/hogehoge/piyopiyo)
    def upload_attachment(self, path, file_path) :
        if (file_path == r"hidden_by_limit") : 
            return "hidden_by_limit"
        print("uploading growi attachment...")
        page_id, revision_id, latest_ts, _ = self.get_page_info(path)
        params_ = self.growi_params.copy()
        payload = {"page_id": page_id}
        print(file_path)
        file = {"file": open(file_path, 'rb')}
        res = requests.post(self.growi_url("attachments.add"), params=params_, data=payload, files=file)
        attachment_path = res.json()['attachment']['filePathProxied']
        return attachment_path
    
    # TODO 使いやすくする
    # @param string atttachment_id : 削除するファイルのGrowiにおけるid
    # @return 辞書型配列 server response
    def remove_attachment(self, attachment_id) :
        params_ = self.growi_params.copy()
        params_["attachment_id"] = attachment_id
        res_remove = requests.post(self.growi_url("attachments.remove"), params=params_)
        return res_remove