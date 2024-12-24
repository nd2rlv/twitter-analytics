import tweepy
from PIL import Image
import io

# Ваші API ключі
API_KEY = "yYRL2zqYZihr1SAZhutKmysBz"
API_SECRET = "WTSAurCNG6jbNP4fltIifeA3I7RRzFRWvjx5qDaGxLbiZvsfMA"
ACCESS_TOKEN = "1514592843683225603-qKAJMW5sadmPDqIBmjvfOu84TYVzwd"
ACCESS_SECRET = "c8ji4RGo42Nh9qUhBlMEtp5RRqbUKSp8HTxjpUEmrAvZf"

# Аутентифікація в Twitter
def authenticate():
    auth = tweepy.OAuthHandler(API_KEY, API_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_SECRET)
    return tweepy.API(auth)

# Перевірка формату зображення
def get_image_format(image_data):
    try:
        with Image.open(io.BytesIO(image_data)) as img:
            return img.format
    except IOError:
        return None

def main():
    # Ініціалізація API Twitter
    api = authenticate()
    print("Успішно аутентифіковано!")

    # Отримання останніх 5 твітів користувача
    username = "elonmusk"
    tweets = api.user_timeline(screen_name=username, count=5, tweet_mode="extended")

    for tweet in tweets:
        print(f"Твіт: {tweet.full_text}\n")
        
        # Якщо є медіа (зображення), обробляємо
        if 'media' in tweet.entities:
            for media in tweet.entities['media']:
                if media['type'] == 'photo':
                    image_url = media['media_url']
                    image_data = requests.get(image_url).content
                    image_format = get_image_format(image_data)
                    print(f"Формат зображення: {image_format}")

if __name__ == "__main__":
    main()