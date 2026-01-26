import json

ARTCOUNT = 'sentartcount.json'

def get_user_artcount_json():
    try:
        with open(ARTCOUNT, 'r') as file:
            artcount_data = json.load(file)
        return artcount_data
    except FileNotFoundError:
        return {}
    
def increment_user_artcount(user_id : int, key : str):
    user_artcount_data = get_user_artcount_json()

    user_id = str(user_id)

    if user_id not in user_artcount_data:
        user_artcount_data[user_id] = {"art": 0, "yaoi": 0, "yuri": 0}

    try:
        user_artcount_data[user_id][key] += 1
        print(f"[artcounting] +1 {key} to {user_id}")
    except:
        return False

    with open(ARTCOUNT, 'w') as file:
        json.dump(user_artcount_data, file, indent=4)

    return True