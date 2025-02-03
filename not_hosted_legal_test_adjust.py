import openai
import streamlit as st
from dotenv import load_dotenv
import datetime
import re
import json
from os.path import basename
from openai import AssistantEventHandler
import os
import smtplib, ssl
from typing_extensions import override
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.utils import formataddr
from cryptography.fernet import Fernet
import firebase_admin
import base64
from firebase_admin import credentials, firestore



load_dotenv()

# Test Keys

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY_raw')
VECTOR_STORE_ID = os.getenv('VECTOR_STORE_ID_raw')
ASSISTANT_ID = os.getenv('ASSISTANT_ID_raw')
SERVICE_ACCOUNT= os.getenv('BASE64_SERVICE_KEY')


if not SERVICE_ACCOUNT:
    raise ValueError("Base64-encoded service account key not found in environment variables.")

try:
    # Decode the Base64 string
    decoded_key = base64.b64decode(SERVICE_ACCOUNT).decode('utf-8')

    # Parse the JSON string into a dictionary
    service_account_info = json.loads(decoded_key)
except Exception as e:
    raise ValueError(f"Failed to load service account key: {e}")


# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    cred= credentials.Certificate(service_account_info)
    firebase_admin.initialize_app(cred)

db= firestore.client()

openai.api_key = OPENAI_API_KEY
client = openai.OpenAI(api_key=openai.api_key)
model = "gpt-4o"
assis_id = ASSISTANT_ID
vector_id = VECTOR_STORE_ID


# Clear the vector database

# file_list= client.beta.vector_stores.files.list(vector_store_id=vector_id).data

# list_print= []

# for file in file_list:

#     file_id= file.id

#     print(file_id)

#     list_print.append(list_print)

#     print(file_id)

#     delete_vector_data= client.beta.vector_stores.files.delete(file_id=file_id, vector_store_id= vector_id)

#     message_delete_vector= delete_vector_data.id

#     print(message_delete_vector)

# print(list_print)



# while True:
#     time.sleep(1)

# In production, replace this with actual database calls

def get_all_threads():

    threads= db.collection('threads').stream()

    return [(thread.id, thread.to_dict().get('name','Untitled')) for thread in threads]


def get_thread_name(thread_id):
    doc = db.collection('threads').document(thread_id).get()
    if doc.exists:
        data = doc.to_dict()
        return data.get('name', 'Untitled')
    else:
        return 'Untitled'


def generate_thread_name(messages):

    global model

    # Concatenate user messages to form the conversation text
    conversation_text = "\n".join(
        [f"{msg['role'].capitalize()}: {msg['content']}" for msg in messages]
    )
    
    # Use OpenAI API to summarize the conversation
    response = client.chat.completions.create(
        model='gpt-4o-mini',  # Use an appropriate model
        messages= [
            {"role":"system", "content":"Summarize the main topic of the following user conversations in a short phrase"},
            {"role":"user", "content":f"{conversation_text}"}
            ],
        max_tokens=10,
        temperature=0.5,
        n=1,
        stop=None,
    )

    summary = response.choices[0].message.content
    print(summary)
    return summary if summary else "Untitled"


def update_thread_name(thread_id, thread_name):

    db.collection('threads').document(thread_id).update({'name': thread_name})


def save_thread(thread_id, messages, thread_name='Untitled'):

    try:
        thread_data= {
            'name': thread_name,
            'messages': messages,
        }

        # Saving thread messages to the database
        db.collection('threads').document(thread_id).set(thread_data)

    except Exception as e:
        print(f"Error saving thread {thread_id}: {e}")


def load_thread(thread_id):

    doc= db.collection('threads').document(thread_id).get()

    if doc.exists:
        data= doc.to_dict()

        return data.get('messages', [])
    else:
        return []


def create_new_thread():

    # Create a new thread using OpenAI API
    thread_create = client.beta.threads.create()
    thread_id_new = thread_create.id
    print(f"Created new thread: {thread_id_new}")

    # Initialize the conversation history for the new thread
    save_thread(thread_id_new, [], thread_name="Untitled")
    rename_untitled_threads()
    return thread_id_new


def rename_untitled_threads():

    # Query for docs named exactly "Untitled"
    untitled_docs = list(
        db.collection("threads").where("name", "==", "Untitled").stream()
    )
    
    if not untitled_docs:
        print("No untitled threads found.")
        return
    
    # Keep a dictionary of counters keyed by date:

    counters = {}
    
    for doc_snapshot in untitled_docs:
        doc_id = doc_snapshot.id
        
        # Creation timestamp:

        today_str = datetime.date.today().strftime("%Y-%m-%d")
        
        # Check if we already have a counter for today_str
        if today_str not in counters:
            counters[today_str] = 0
        
        # Increment the date-specific counter
        counters[today_str] += 1
        new_number = counters[today_str]

        # Build a new name
        new_name = f"Untitled_{today_str}_#{new_number}"
        
        # Update Firestore
        db.collection("threads").document(doc_id).update({"name": new_name})
    


class EventHandler(AssistantEventHandler):
    @override
    def on_event(self, event):
        # Retrieve events that are denoted with 'requires_action'
        # since these will have our tool_calls
        if event.event == 'thread.run.requires_action':
            run_id = event.data.id
            self.handle_requires_action(event.data, run_id)


    def handle_requires_action(self, data, run_id):
        tool_outputs = []
        for tool in data.required_action.submit_tool_outputs.tool_calls:
            params_loaded = tool.function.arguments
            params = json.loads(params_loaded)
            print(f"Requested Tool: {tool.function.name}, Params: {params}")

            if isinstance(params, str):
                try:
                    params = json.loads(params)
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON: {e}")


        self.submit_tool_outputs(tool_outputs, run_id)


    def submit_tool_outputs(self, tool_outputs, run_id):

        # Use the submit_tool_outputs_stream helper
        with client.beta.threads.runs.submit_tool_outputs_stream(
            thread_id=self.current_run.thread_id,
            run_id=run_id,
            tool_outputs=tool_outputs,
            event_handler=EventHandler(),
        ) as stream:
            stream.until_done()
            for text in stream.text_deltas:
                print(text, end="", flush=True)
            


# Start Run
def start_run(thread_id, assistant_id):
    try:
        with client.beta.threads.runs.stream(
            thread_id=thread_id,
            assistant_id=assistant_id,
            event_handler=EventHandler()
        ) as stream:
            stream.until_done()
    except openai.BadRequestError as e:
        if 'already has an active run' in str(e):
            print("An active run is already in progress. Please wait for it to complete.")
        else:
            print(f"An error occurred: {e}")




def send_user_message(thread_id, content):
    user_message = client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=content
    )
    return user_message

# thread_id= create_new_thread()

# while True:
#     time.sleep(1)

thread_id= "thread_tS3k160OXiNL1tzGpFwG4hAW"

# Chat input for the user
prompt= "Hello"


# Send user's message to OpenAI API
send_user_message(thread_id, prompt)
start_run(thread_id, assis_id)

# Retrieve assistant's response
assis_messages = client.beta.threads.messages.list(
    thread_id
)

# Find the latest assistant message
assistant_message = None
for msg in assis_messages.data:
    if msg.role == 'assistant':
        assistant_message = msg
        break
if assistant_message:
    final_response = assistant_message.content[0].text.value
    final_clean = re.sub(r'【\d+:\d+†.*?】', '', final_response)

print(final_clean)

# Update AI assistant

# vector= client.beta.vector_stores.create(
#     name="BindaVDB",
#     chunking_strategy= {
#         "type": "static",
#         "static": {
#             "max_chunk_size_tokens": 4000,
#             "chunk_overlap_tokens": 400}}
# )

# latest_vector_id= vector.id

# print(latest_vector_id)

# list_tools= [{
#             "type": "function",
#             "function": {
#                 "name": "download_file",
#                 "description": "Assist users with exporting documents for copying they have drafted for their legal firm. The types of documents you will be exporting are contracts, agreements, letters and othe rlegal documents. You are to get the file data as inputs for this function",
#                 "parameters": {
#                     "type": "object",
#                     "properties": {
#                         "file_data":{"type": "string", "description": "Obtain the file data to be exported to be copied by users. Be sure to get the entire text no matter what the size of the information provided. This represents the data to be copied by users. Please be sure to incude the applicable formatting as per the draft."},
#                         },
#                         "required": ["file_data"],
#                     }
#                 }
#             },
#             {"type": "file_search",
#              "file_search":{
#                  "max_num_results": 4,
#              "ranking_options": {
#                  "score_threshold": 0.4},
#                 }
#             }
#         ]



# legal_ass= client.beta.assistants.update(
#     model= model,
#     assistant_id=assis_id,
#     name= "Legal_Assistant",
#     temperature= 0.3,
#     tools= list_tools,
#     tool_resources={
#         "file_search":{
#             "vector_store_ids": [vector_id],    
#           }
#         }
# )

# print(legal_ass.id)
