import re


def extract_session_id(session_str:str):
    path = re.search("sessions\/(.*?)\/contexts\/", session_str)
    if path:
        return path.group(1)
    return " "

def get_str_from_food_dict(food_dict: dict):
    result = ", ".join([f"{int(value)} {key}" for key, value in food_dict.items()])
    return result

if __name__ == "__main__":
    # print(extract_session_id("projects/alexa-chatbot-ovve/agent/sessions/7820e965-3d9b-130d-1583-d134e6981204/contexts/ongoing-order"))
    print(get_str_from_food_dict({"Samosa": 5}))