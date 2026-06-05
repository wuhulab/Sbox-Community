import secrets


def generate_captcha():
    num1 = secrets.randbelow(20) + 1
    num2 = secrets.randbelow(20) + 1
    operator = secrets.choice(["+", "-"])
    if operator == "+":
        answer = num1 + num2
    else:
        if num1 < num2:
            num1, num2 = num2, num1
        answer = num1 - num2
    problem = f"{num1} {operator} {num2} = ?"
    return problem, answer


def verify_captcha(session, captcha_id, user_answer):
    captchas = session.get("captchas", {})
    correct_answer = captchas.get(captcha_id)
    if correct_answer is None:
        return False
    del captchas[captcha_id]
    session["captchas"] = captchas
    try:
        return int(user_answer) == correct_answer
    except (ValueError, TypeError):
        return False
