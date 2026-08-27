from google import genai

client = genai.Client(api_key="AQ.Ab8RN6I9donKR5W9xnjnYd8DlUEfLSgAKc6y8cfdPu7yXGvtNQ")

def get_knitting_advice(item,color):
    prompt = f"{color}の{item}を作りたいです。おすすめの毛糸と簡単なコツを教えて！"
    return prompt

my_knitting_advice = get_knitting_advice("コースター", "黄色")

response = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents = my_knitting_advice
)

print("AIからのアドバイス:")
print(response.text)