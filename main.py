import json
from logging import DEBUG
from typing import Optional

import requests
from fastapi import FastAPI, Form
from loguru import logger
from pydantic import BaseModel

import mongo

logger.add("logs/myapp.log", rotation="10 MB", retention="7 days",
           enqueue=True, backtrace=True, diagnose=True,
           format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
           level=DEBUG)

logger.info("logger started")

app = FastAPI()


def d_md5(data):
    return mongo.get_md5(data['type'] + data['title'] + data['options'])


class AskRequest(BaseModel):
    type: str
    title: str
    options: Optional[str] = None


@app.post("/ask")
async def ask(q_type: str = Form(...), title: str = Form(...), options: Optional[str] = Form(None)):
    data = {"type": q_type, "title": title, "options": options}
    logger.debug(
        "接收到用户查询：题目" + data['title'] + " 类型：" + data['type'] + " 选项 " + data['options'].replace("\n", "#"))
    f = mongo.find_question(md5=d_md5(data))
    if f == 0:
        ans = get_ans_from_ai(data)
        mongo.new_question(_type=data['type'], question=data['title'], choice=data['options'], answer=ans)
        logger.info("数据库查询不到题目，AI返回结果：" + ans)
        ret = {"code": 101, "answer": ans}
    elif f["info"]["ac"] == 1:
        logger.info("数据库返回正确答案：" + f["answer"])
        ret = {"code": 102, "answer": f["answer"]}
    elif f["info"]["ac"] == 0:
        ans = get_ans_from_ai(data, f["info"]["eropt"])
        logger.info("数据库返回了错误答案，AI返回了新的答案：" + ans)
        ret = {"code": 103, "answer": ans}
    elif f["info"]["ac"] is None:
        logger.info("数据库返回了未知正误的答案：" + f["answer"])
        ret = {"code": 104, "answer": f["answer"]}
    else:
        logger.error("内部错误，数据库匹配失败！")
        ret = {"code": -1, "message": "服务器错误：501"}
    return ret


def get_ans_from_ai(data, fix=None):
    """
    用于第一次从AI获取答案
    Args:
        data: 一个包含 type, title, options 的字典
        fix: 已经确定为错误的选项
    Returns:
        AI 返回的答案
    """
    text = f"""类型：{data['type']} 题目：{data['title']} 选项：{data['options']}"""
    if fix is not None:
        text.join(f"已知选项f'{fix}是错误的'")
    url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer 3107c749-5bcb-4b80-b34b-dd3b45785d54"
    }
    request_data = {
        "model": "ep-20241016132251-pdpmd",
        "messages": [
            {
                "role": "system",
                "content": (
                    # "请严格按照以下要求回答问题：你只需要回答以下题目的答案即可，"
                    # "如果是选择题只有一个正确答案只回复正确答案，"
                    # "如果是多选题将正确答案以#分隔开，"
                    # "如果是判断题只输出正确或错误的符号，"
                    # "不需要指出错误在哪里。永远不要回复多余的内容"
                    # "例如：不要输出 空肠、回肠、十二指肠是上消化道，直肠、肛门肛管属于下消化道，所以答案是十二指肠。而是 十二指肠"
                    # "选出选项中最合适的作为答案，不要输出选项之外的答案"
                    """
                    请严格按照要求回答：对于单选题，仅回复一个正确的选项（错误的说法）；对于多选题，将正确选项用 "#" 分隔（例如：选项一 # 选项二）；对于判断题，仅回复“正确”或“错误”。不提供任何解释、解析或多余的内容。
                    
                    """
                )
            },
            {"role": "user", "content": "你只需要输出答案！" + text}
        ]
    }

    response = requests.post(url, headers=headers, data=json.dumps(request_data))
    content = response.json().get("choices")[0].get("message").get("content")
    # print(content)
    return content


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5000)
