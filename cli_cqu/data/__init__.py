from .ua import UA_IE11


class HOST:
    SCHEME = "http"
    DOMAIN = "jxgl.cqu.edu.cn"
    PREFIX = f"{SCHEME}://{DOMAIN}"


HEADERS = {
    'host': HOST.DOMAIN,
    'connection': "keep-alive",
    'cache-control': "max-age=0",
    'upgrade-insecure-requests': "1",
    'user-agent': UA_IE11,
    'accept':
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
    'referer': HOST.PREFIX,
    'accept-encoding': "gzip, deflate",
    'accept-language': "zh-CN,zh;q=0.9",
}
"默认使用的请求头"
