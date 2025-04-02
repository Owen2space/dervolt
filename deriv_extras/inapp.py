from deriv_functions import fetch_deriv_user_info, extract_tokens_from_url

# user_info = fetch_deriv_user_info("a1-OC8lfmACE0B7QBi7WakozFVWr31Si")

# print(user_info[1])

url = "https://5000.dervolt.site/oauth/?acct1=CR5056855&token1=a1-OC8lfmACE0B7QBi7WakozFVWr31Si&cur1=(USD&acct2)=VRTC7061113&token2=a1-YaiqvLsUUgZWfw5jKEU4ZOZyyREn3&cur2=USD"

token1, token2 = extract_tokens_from_url(url)

print(fetch_deriv_user_info(token1)[1])

# print(token1)
