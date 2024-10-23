import hashlib
import os

from pymongo import MongoClient

uri = os.environ.get("MONGO_URI")
client = MongoClient(uri)

db = client.get_database("parksi_test")
col = db.get_collection("question")


def get_md5(string):
    md5 = hashlib.md5()
    md5.update(string.encode('utf-8'))
    return md5.hexdigest()


def new_question(_type, question, choice, answer):
    """
    向数据库新加一条问题
    :param _type: 题类型
    :param question: 题目
    :param choice: 选项
    :param answer: 答案
    :return: 数据 id
    """
    doc = {
        "md5": get_md5(_type + question + choice),
        "type": _type,
        "question": question,
        "choice": choice,
        "answer": answer,
        "info":
            {
                "ac": None,
                "eropt": None
            }
    }

    res = col.insert_one(doc)
    return res.inserted_id


def find_question(question=None, md5=None):
    """
    从数据库查询题目
    :param question: 题目
    :param md5: 拼接类型 题目 选项得到的md5值
    :return: json, not found:0
    """
    if question is not None:
        ret = col.find_one({"question": question})
    elif md5 is not None:
        ret = col.find_one({"md5": md5})
    else:
        return 0
    if ret is not None:
        return ret
    else:
        return 0


def fix_question(answer, __id=None, question=None, md5=None):
    """
    修正一个问题的答案
    :param answer: 新答案
    :param __id: id
    :param question: 问题
    :param md5: md5
    :return: empty, err:0
    """
    if __id is not None:
        query = {"_id": __id}
    elif question is not None:
        query = {"question": question}
    elif md5 is not None:
        query = {"md5": md5}
    else:
        return 0
    upd = {
        '$set': {
            "answer": answer
        }
    }
    col.update_one(query, upd)
    return 1


def mark_question(ac: bool, __id=None, question=None, md5=None):
    """
    标记问题正确与否
    :param ac: bool: 正确/错误
    :param __id: id
    :param question: 问题
    :param md5: 拼接类型 题目 选项得到的md5值
    :return: ac:1, err:0
    """
    if __id is not None:
        query = {"_id": __id}
    elif question is not None:
        query = {"question": question}
    elif md5 is not None:
        query = {"md5": md5}
    else:
        return 0
    upd = {
        '$set': {
            "info": {
                "ac": int(ac),
            }
        }
    }
    col.update_one(query, upd)
    return 1
