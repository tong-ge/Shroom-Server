import socket
import openai
from typing import Optional

prompt="""You are a web server. Return an HTTP response and nothing else for each request.
An example of request and response is shown below:
Request:```http
GET / HTTP/1.1
Host: example.com
Connection: keep-alive
Cache-Control: max-age=0
sec-ch-ua: "Not:A-Brand";v="99", "Microsoft Edge";v="145", "Chromium";v="145"
sec-ch-ua-mobile: ?0
sec-ch-ua-platform: "Windows"
DNT: 1
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36 Edg/145.0.0.0
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7
Sec-Fetch-Site: none
Sec-Fetch-Mode: navigate
Sec-Fetch-User: ?1
Sec-Fetch-Dest: document
Accept-Encoding: utf-8
Accept-Language: zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7,en-GB;q=0.6

```
Response:```http
HTTP/1.1 200 OK
Date: Mon, 09 Mar 2026 12:46:33 GMT
Content-Type: text/html
Content-Encoding: utf-8
Connection: keep-alive
Cache-control: no-cache
Last-Modified: Thu, 05 Mar 2026 11:54:13 GMT
Allow: GET, HEAD
Age: 53
Accept-Ranges: bytes
Server: nginx

<!doctype html>
<html lang="en">
<head>
    <title>Example Domain</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body{background:#eee;width:60vw;margin:15vh auto;font-family:system-ui,sans-serif}
        h1{font-size:1.5em}div{opacity:0.8}a:link,a:visited{color:#348}
    </style>
</head>
<body>
    <div>
        <h1>Example Domain</h1>
        <p>This domain is for use in documentation examples without needing permission. Avoid use in operations.</p>
        <p><a href="http://iana.org/domains/example">Learn more</a></p>
    </div>
</body>
</html>


```
IMPORTANT: Return the raw response and do not wrap it in the markdown format. Content-Encoding should always be UTF-8 instead of those provided by browser.  
Try writing the actual response based on the query string, Hosts header and your knowledge. Write a modern-looking web page with links and javascript, as realistic as possible. 
Use relative location in your links. If pictures are needed, use [Lorem Picsum](http://picsum.photos/{x}/{y}). Here x and y should be plain numbers in pixels.  
Using of embedded scripts instead of <script:src> is encouraged.  
Set a longer Keep-Alive header to guarantee that the browser will not interrupt receiving.  
If a non-text object (such as /favicon.ico, but this does not include scripts and stylesheets) is requested, you should response with a 404 Not Found.  
If a script or stylesheet is requested, response as `Content-Type: text/javascript` or `Content/Type:text/css`.
If a normal HTTP proxy request is invoked, try imitating the target website. If a CONNECT with HTTPS:443 is invoked, response with 403 Forbidden.  
"""

def get_stream_response(req:str,client:openai.OpenAI):
    global prompt
    response=client.chat.completions.create(
        model='Qwen/Qwen3-8B',
        messages=[
            {'role':'system','content':prompt},
            {'role':'user','content':req}
        ],
        max_tokens=4096,
        stream=True,
        extra_body={'thinking':{'type':'disabled'}},
        timeout=5,
        temperature=2,
        top_p=0.2
    )
    return response

def read_full_request(client_socket: socket.socket) -> Optional[str]:
    """读取完整请求（优化Windows兼容性）"""
    client_socket.settimeout(86400)
    request_data = b""
    
    try:
        while len(request_data) < 32768:
            chunk = client_socket.recv(1024)
            if not chunk:
                break
            request_data += chunk
            if b"\r\n\r\n" in request_data:
                if b"Content-Length:" in request_data:
                    length_match = re.search(rb"Content-Length:\s*(\d+)", request_data)
                    if length_match:
                        content_length = int(length_match.group(1))
                        current_body_length = len(request_data.split(b"\r\n\r\n")[1])
                        if current_body_length < content_length:
                            continue
                break
        return request_data.decode("utf-8", errors="ignore").strip()
    except socket.timeout:
        print("请求读取超时，关闭连接")
        return None
    except Exception as e:
        print(f"读取请求失败: {e}")
        return None

if __name__ == '__main__':
    client=openai.OpenAI(
        base_url="https://api.siliconflow.cn/v1",
        api_key="YOUR_SILICONFLOW_API_KEY"
    )
    s=socket.socket()
    host='0.0.0.0'
    port=8080
    s.bind((host,port))

    s.listen(5)
    while True:
        print("Accepting connection...")
        c,addr=s.accept()
        req:str|None=read_full_request(c)
        if(req == None):
            print("Connection closed.")
            c.close()
            continue
        print(f"Request:\r\n{req}\r\n")
        try:
            stream=get_stream_response(req,client)
            print("Response:")
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    response=content.encode('utf-8')
                    print(content,end='')
                    c.send(response)
            print()
        except Exception as e:
            print(e)
            continue
        finally:
            print("Connection closed.")
            c.close()
