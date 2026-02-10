import smtplib
# 测试连接
try:
    server = smtplib.SMTP_SSL("smtp.qq.com", 465)
    server.login("2361542526@qq.com", "cyafrtlsbwztdjii")
    print("SMTP开启成功，授权码有效！")
    server.quit()
except Exception as e:
    print(f"失败原因：{e}")