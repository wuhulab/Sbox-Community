权限范围（Scope）
只允许获取用户名，邮箱，id

1. 注册OAuth应用
/OAuth

2. 获取授权码

3.访问
http://localhost:5219/oauth/authorize?
  client_id=YOUR_CLIENT_ID&
  redirect_uri=http://localhost:5000/callback&
  response_type=code&
  scope=basic

用户授权后，会重定向到您的回调地址：

http://localhost:5000/callback?code=EXAMPLE_CODE

# main.py
import requests

resp = requests.post('http://localhost:5219/oauth/token', json={
    "grant_type": "authorization_code",
    "code": "YOUR_AUTHORIZATION_CODE",
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "redirect_uri": "http://localhost:5000/"
})

print("Status Code:", resp.status_code)
print("Response Headers:", resp.headers)
print("Raw Response Text:")
print(resp.text)


# get_user_info.py
import requests

ACCESS_TOKEN = "YOUR_ACCESS_TOKEN"

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}"
}

resp = requests.get("http://localhost:5219/oauth/user", headers=headers)

print("Status:", resp.status_code)
print("User Info:", resp.json())