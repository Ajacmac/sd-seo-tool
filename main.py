import json
import re

import src.lm
import src.prompts
import src.jobs
import src.twinword

def test_all():
    print("Testing all models")
    print("\n----------------\n")

    print("Testing Groq:")
    print("    Llama 3 8b:")
    response = src.lm.llama3_8b("Hello. Can you write a poem for me?")
    print(response)

    print("    Llama 3 70b:")
    response = src.lm.llama3_70b("Hello. Can you write a poem for me?")
    print(response)

    print("    Gemma 2 9b:")
    response = src.lm.gemma2_9b("Hello. Can you write a poem for me?")
    print(response)

    print("    Mixtral 8x7b:")
    response = src.lm.mixtral8x7b("Hello. Can you write a poem for me?")
    print(response)

    print("\n----------------\n")

    print("Testing OpenAI: GPT-4o:")
    response = src.lm.gpt4o("Hello. Can you write a poem for me?")
    print(response)

    print("\n----------------\n")

    print("Testing Anthropic: Claude 3.5 Sonnet:")
    response = src.lm.sonnet("Hello. Can you write a poem for me?")
    print(response)

def example_chain():
    turtle_poem = src.lm.llama3_8b("Please write a haiku about the north american box turtle for me.")

    critique = src.lm.llama3_70b(f"Can you critique this poem for me? {turtle_poem}.")

    print("----------------")
    print(turtle_poem)
    print("----------------")
    print(critique)
    print("----------------")

def extract_json_from_string(text):
    # Try to find a JSON block enclosed in triple backticks
    match = re.search(r"(.*?)```([\s\S]*?)```(.*)", text, re.DOTALL)
    if match:
        before = match.group(1).strip()
        json_content = match.group(2).strip()
        after = match.group(3).strip()
        commentary = f"{before} {{{{json went here}}}} {after}"
        return {
            "commentary": commentary,
            "json": json_content
        }
    return {
        "commentary": text.strip(),
        "json": None
    }

def faq_schema_test():
    '''
        This confirmed that gpt4o knows FAQ schema well enough to generate a FAQ page.
        We used an online tool to validate the generated content.

        It might not get it right every time though. We should us
    '''
    print("Testing FAQ schema:")
    response = src.lm.gpt4o("Please write me a FAQ page for a website with the url https://example.com/faq. Use proper FAQ schema from schema.org. Generate 5 questions and answers, and have the subject be for an independent financial advisor. Include a question about fees, a question about services, a question about qualifications, a question about experience, and a question about location.")
    print(response)

    extracted_content = extract_json_from_string(response)
    
    print("Extracted commentary:\n")
    print(extracted_content["commentary"])

    if extracted_content["json"]:
        try:
            parsed_response = json.loads(extracted_content["json"])
            print("Successfully parsed JSON.")
            
            print("FAQ schema:")
            print(parsed_response['faq schema'])

            output_file = open("/volume/output.html", "w")
            json.dump(parsed_response['html'], output_file)
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {e}")
            print("First 100 characters of extracted JSON content:")
            print(extracted_content["json"][:100])
    else:
        print("No JSON block found in triple backticks.")

# if __name__ == "__main__":
#     input_file = open("example-data.json", "r")
#     data = json.load(input_file)

#     # data["prompts"][0] is for models other than Sonnet
#     # data["prompts"][1] is for Sonnet
#     # Sonnet has a lower token limit than other models and tailwind increases output length too much
    
#     response = src.lm.gpt4o(str(data["prompts"][0]))
#     response_file = open("/volume/response.json", "w")
#     response_file.write(response)

#     print("Raw response length:", len(response), "\n")

#     extracted_content = extract_json_from_string(response)
    
#     print("Extracted commentary:\n")
#     print(extracted_content["commentary"])

#     if extracted_content["json"]:
#         try:
#             parsed_response = json.loads(extracted_content["json"])
#             print("Successfully parsed JSON.")
            
#             print("Analysis and comments:")
#             print(parsed_response['analysis and comments'])

#             output_file = open("/volume/output.html", "w")
#             json.dump(parsed_response['html'], output_file)
#         except json.JSONDecodeError as e:
#             print(f"JSON Decode Error: {e}")
#             print("First 100 characters of extracted JSON content:")
#             print(extracted_content["json"][:100])
#     else:
#         print("No JSON block found in triple backticks.")

def test_hero_section():
    file = open("test_flow_data/example_one.json", "r")
    data = json.loads(file.read())
    full_prompt = src.prompts.hero_section(data["m_keyword"], data["cta"], data["palette"])

    response = src.lm.gpt4o(full_prompt)
    print(response)

def keyword_test():
    response = src.twinword.get_keywords("dog", "CA")
    print(response)

    output_file = open("/volume/keyword_test_output.json", "w")
    json.dump(response, output_file)

if __name__ == "__main__":
    # faq_schema_test()
    # test_hero_section()
    # src.jobs.test()
    keyword_test()

