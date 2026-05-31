# Copyright (C) 2026 小盒子社区
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import smtplib
import logging
from email.mime.text import MIMEText
import config

logger = logging.getLogger(__name__)


# NOTE:发送邮件，使用config配置的SMTP服务器，返回True表示成功
def email(user, content, subject):
    try:
        mail_host = config.EMAIL_HOST
        mail_user = config.EMAIL_USER
        mail_pass = config.EMAIL_PASS
        sender = config.EMAIL_SENDER
        mail_port = getattr(config, "SMTP_PORT", 465)
        use_ssl = getattr(config, "SMTP_USE_SSL", True)
    except Exception:
        logger.warning("发送邮件失败：无邮箱授权码配置")
        return False

    if not mail_host or not mail_user or not mail_pass:
        logger.warning("发送邮件失败：邮箱配置不完整")
        return False

    receivers = [user]

    html_content = f"""
    <html>
        <body>
            <h3>小盒子社区（sbox）消息提醒</h3>
            <p>{content}</p>
        </body>
    </html>
    """
    message = MIMEText(html_content, "html", "utf-8")
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = receivers[0]

    try:
        if use_ssl:
            smtpObj = smtplib.SMTP_SSL(mail_host, mail_port)
        else:
            smtpObj = smtplib.SMTP(mail_host, mail_port)
        smtpObj.login(mail_user, mail_pass)
        smtpObj.sendmail(sender, receivers, message.as_string())
        smtpObj.quit()
        logger.info("邮件发送成功: %s", user)
        return True
    except Exception as e:
        logger.error("邮件发送失败 (%s:%d): %s", mail_host, mail_port, e)
        return False


# NOTE:返回Flask SECRET KEY
def key():
    return config.SECRET_KEY


# NOTE:返回JWT SECRET KEY
def jwt_key():
    return config.JWT_SECRET_KEY
