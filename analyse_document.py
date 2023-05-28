from PyPDF2 import PdfReader
from tqdm import tqdm
import openai
import os
import hashlib
import re
import numpy as np


with open(f'openai_key.txt', 'r') as f:
    openai.api_key = f.read().replace('\n', '')

if not os.path.exists('cache'):
    os.mkdir('cache')

def deterministic_hash(input_string):
    return hashlib.sha256(input_string.encode()).hexdigest()

def read_document(file_path):
    """
    This function reads a PDF file and returns the text.

    Args:
        file_path (str): The path to the PDF file.

    Returns:
        text (str): The text extracted from the PDF file.
    """
    # Open the file in read-binary mode
    with open(file_path, 'rb') as file:
        # Create a PDF reader
        reader = PdfReader(file)
        # Initialize an empty string to hold the text
        texts = [page.extract_text() for page in tqdm(reader.pages)]
    return texts

def query_openai(query, system_message, model='gpt-4'):
    key = deterministic_hash(query + system_message + model)
    if os.path.exists(f'cache/{key}.txt'):
        with open(f'cache/{key}.txt', 'r') as f:
            rv = f.read() 
    else:

        result = openai.ChatCompletion.create(model=model, messages=[{"role": "system", "content": system_message}, {"role": "user", "content": query}], temperature=0)
        rv = result['choices'][0]['message']['content']
        with open(f'cache/{key}.txt', 'w') as f:
            f.write(rv)
    print('====Query:====')
    print(query)
    print('====RV:====')
    print(rv)
    return rv

def format_page(page):
    system_message = """You are a helpful AI Assistant. Given a badly formatted page of text extracted from a pdf, format it properly, removing pdf creation artifacts, with correct spacing and punctuation."""
    return query_openai(page, system_message)

def generate_questions(page, sample_questions=None):
    system_message = """
    You are helpful AI assistant. Your goal is to help a farmer generate a design document related to mangrove restoration. 
    Read a sample section of the document, and generate 10 questions as possible for farmer's specific use case to get 
    information you would need to adapt the document for their use case. If it is relevant, also generate any specific 
    questions for the farmer's name, email, address, etc. Write questions in second person, e.g. 'What is your name?'. 
    Be sure to ask about all names, institutions, locations, etc, and also more general questions about the project plan.

    Write sample answers with the label [Simulated Answer]. The intent is to simulate the responses of a different farmer who 
    is using the design document for guidence. E.g.

    - How will your project contribute to the social, economic, and environmental aspects of sustainable development in your region?\n[Simulated Answer]: Our project will result in improved biodiversity, increased fish resources, climate change mitigation, job creation, and poverty alleviation through sustainable livelihoods.'
    - What are some specific project activities or measures you plan to implement to ensure the sustainability and success of your project?\n[Simulated Answer]: We will be providing training and capacity building for local communities, promoting sustainable land use practices, monitoring and evaluating project progress, and integrating our project into local and regional development plans.',
    """
    if sample_questions is not None:
        system_message += sample_questions
    return query_openai(page, system_message)

def create_summary(text):
    system_message = """Create a summary of the text in 500 words or less."""
    return query_openai(text, system_message)


def rank_pair(text, question_1, question_2):
    system_message = """
    You are a helpful AI assistant. Given a the initial document related to mangrove restoration, a new farmer is trying 
    to adapt the questions to his own farm. Given two pairs of questions and answers, determine if question A is better
    than question B, or vice versa. Factors to consider are consider are relevance to the text, 
    specificity to the farmer's situation, and quality of the response. 

    You should frame this as a debate, where you write 
    [A argument]
    Arguments that question A is better than question B, drawing from the text. 
    [B argument]
    Arguments that question B is better than question A, drawing from the text.
    [Conclusion]
    Enter conclusion
    enter 'AAA' if A is better or 'BBB' if B is better.
    """
    prompt = f"""Original Design Doc:

    {text}

    Question A:

    {question_1}

    Question B:

    {question_2}
    """
    return query_openai(prompt, system_message, model='gpt-3.5-turbo')

def rank_list(text, questions_and_answers):
    system_message = """
    You are helpful AI assistant. Your goal is to help a farmer generate a design document related to mangrove restoration. 
    Given the sample text and the questions and simulated answers, Return the top 5 question/answer pairs, labeled from 
    1 to 5. Factors to consider are consider are relevance to the text,  specificity to the farmer's situation, 
    and quality of the response, and the degree to which the question is interpretable by the farmers. 
    """
    text = f"""Original Design Doc:

    {text}

    Questions/Simulated Answers:

    {questions_and_answers}
    """
    return query_openai(text, system_message)


def final_sorting_and_pruning(good_questions):
    system_message = """
    You are helpful AI assistant. Your goal is to help a farmer generate a design document related to mangrove restoration. 
    Sort these questions/answer pairs in order of complexity, and remove redundant questions. Make sure all questions have the same formatting,
    and that there is no extra text. Remove questions/answer pairs which reference to baseline analysis. 

    The format is as follows:
    
    1. What is the start date of your mangrove restoration project?
    [Simulated Answer]: Our project started on June 1, 2020.

    2. What is the crediting period for your project?
    [Simulated Answer]: Our project has a crediting period of 20 years, from June 1, 2020, to May 31, 2040.

    etc.
    """
    return query_openai(good_questions, system_message)

def modify_prompt(original, questions_and_answers):
    system_message = """
    You are helpful AI assistant. Your goal is to help a farmer generate a design document related to mangrove restoration. 
    Given the sample text and the questions and simulated answers, modify the sample text to reflect the changes in the 
    simulated answers. Feel free to change the structure/ordering of the output, and make sure that the output text is 
    formatted well, and is interpretable by the farmers."""
    text = f"""Original Design Doc:

    {original}

    Questions/Simulated Answers:

    {questions_and_answers}

    New Design Doc:

    """
    return query_openai(text, system_message)


if __name__ == "__main__":
    doc = read_document('new_pdd.pdf')
    intro_text = '\n'.join(doc[2:10])
    questions_and_answers = generate_questions(intro_text, sample_questions=None)
    good_questions = []
    for i in range(3):
        rankings = rank_list(intro_text, questions_and_answers)
        good_questions.append(re.sub(r'\d+\. ', '- ', rankings))
        questions_and_answers = generate_questions(intro_text, sample_questions='\n'.join(good_questions))
    rankings = rank_list(intro_text, questions_and_answers)
    good_questions.append(re.sub(r'\d+\. ', '- ', rankings))
    good_questions = '\n'.join(good_questions)
    good_questions = final_sorting_and_pruning(good_questions)
    new_prompt = modify_prompt(intro_text, good_questions)


