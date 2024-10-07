import openai
import streamlit as st
from dotenv import load_dotenv
from os.path import basename
import time
import re
import json
from openai import AssistantEventHandler
import os
import smtplib, ssl
from typing_extensions import override
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from cryptography.fernet import Fernet
from email.mime.application import MIMEApplication
from email.utils import formataddr

load_dotenv()

# Keys

encryption_key = st.secrets['ENCRYPTION_KEY']
cipher_suite = Fernet(encryption_key.encode())


OPENAI_API_KEY= st.secrets['OPENAI_API_KEY']
VECTOR_STORE_ID= st.secrets['VECTOR_STORE_ID']
ASSISTANT_ID= st.secrets['ASSISTANT_ID']
EMAIL_SENDER= st.secrets['EMAIL_SENDER']
EMAIL_PASSWORD= st.secrets['EMAIL_PASSWORD']


encrypted_secrets= {
    'OPENAI_API_KEY': OPENAI_API_KEY,
    'VECTOR_STORE_ID': VECTOR_STORE_ID,
    'ASSISTANT_ID': ASSISTANT_ID,
    'EMAIL_SENDER': EMAIL_SENDER,
    'EMAIL_PASSWORD': EMAIL_PASSWORD
    }


decrypted_secrets = {}
for key, value in encrypted_secrets.items():
    print(f"Decrypting {key}: {value}")
    decrypted_secrets[key] = cipher_suite.decrypt(value.encode()).decode()


# New Thread

def new_thread():

    # thread= client.beta.threads.create()
    thread_create= client.beta.threads.create()
    thread_id_new= thread_create.id
    print(thread_id_new)

    with open('thread_id.txt', 'w') as thread_file:
        thread_file.write(thread_id_new)

        time.sleep(1)

    return thread_id_new


def find_thread():

    path= os.path.join(os.getcwd(), 'thread_id.txt')

    if os.path.exists(path):

        with open('thread_id.txt', 'r') as thread_file:
            response= thread_file.read()

    else:
        response= new_thread()

    return response


openai.api_key= decrypted_secrets['OPENAI_API_KEY']
client= openai.OpenAI(api_key=openai.api_key)
model= "gpt-4o"
assis_id= decrypted_secrets['ASSISTANT_ID']
thread_id= find_thread()
vector_id= decrypted_secrets['VECTOR_STORE_ID']



# Functions

def write_file(file):

    with open(f'{file.name}', 'wb') as f:
        f.write(file.getbuffer())

    return f'{file.name}'


# def send_email(To, CC, BCC, Subject, Body, Attachments): 


#     email_to= To.split(',')
#     email_to_cc= CC.split(',')
#     email_to_bcc= BCC.split(',')
#     email_to_subject= Subject
#     email_to_body= f""" {Body} """

#     email_sender= decrypted_secrets['EMAIL_SENDER']
#     email_password= decrypted_secrets['EMAIL_PASSWORD']

#     print(email_sender)
#     print(email_password)

#     if not email_password:
#         raise ValueError('EMAIL_PASSWORD environment variable not set')

#     all_recipients= email_to + email_to_cc + email_to_bcc

#     print(all_recipients)
#     print(type(all_recipients))

#     msg= MIMEMultipart()
#     msg['From']= formataddr(("Andile Vilakazi", f"{email_sender}"))
#     msg['To']= ", ".join(email_to)
#     msg['Cc']= ", ".join(email_to_cc)
#     msg['Bcc']= ", ".join(email_to_bcc)
#     msg['Subject']= email_to_subject


#     # Attach body text
#     part_1= MIMEText(email_to_body, "plain")   
#     msg.attach(part_1)


#     if Attachments == 'True':

#         for file in st.session_state.file_uploader:

#             copy_file= write_file(file)

#             with open(copy_file, "rb") as f:
                
#                 part= MIMEApplication(f.read(), Name= os.path.basename(copy_file))
#                 part['Content-Disposition']= f'attachment; filename= "{os.path.basename(copy_file)}"'.format(basename(copy_file))
        
#                 # Attach files
#                 msg.attach(part)

#             if os.path.exists(copy_file):
#                 os.remove(copy_file)


#     smtp_server= 'smtp.bindaattorneys.co.za'
#     smtp_port= 25
#     context= ssl.create_default_context()

#     try:

#         with smtplib.SMTP(smtp_server, smtp_port) as server:
#             server.starttls(context=context)
#             server.login(email_sender, email_password)
#             server.sendmail(from_addr= email_sender, to_addrs= all_recipients, msg= msg.as_string())

#             success_message= f'Email succesfully sent to {all_recipients}'

#     except Exception as e:
#         success_message= f'Failure to send email: {e}'

#     print(success_message)

#     return success_message


# Export text file

def remove_file(file_path):

    time.sleep(1)
    os.remove(file_path)


def download_file(file_data):

    # Display Content
    st.sidebar.code(file_data, language='html')

    response= "File made available for export in the sidebar. Please click the copy putton to access your data"

    return response



list_tools= [{
            "type": "function",
            "function": {
                "name": "download_file",
                "description": "Assist users with exporting documents for copying they have drafted for their legal firm. The types of documents you will be exporting are contracts, agreements, letters and othe rlegal documents. You are to get the file data as inputs for this function",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_data":{"type": "string", "description": "Obtain the file data to be exported to be copied by users. Be sure to get the entire text no matter what the size of the information provided. This represents the data to be copied by users. Please be sure to incude the applicable formatting as per the draft."},
                        },
                        "required": ["file_data"],
                    }
                }
            },
            {"type": "file_search"}
        ]


class EventHandler(AssistantEventHandler):

    @override
    def on_event(self, event):

    # Retrieve events that are denoted with 'requires_action'
    # since these will have our tool_calls

        if event.event == 'thread.run.requires_action':
            run_id= event.data.id
            self.handle_requires_action(event.data, run_id)


    def handle_requires_action(self, data, run_id):

        tool_outputs= []

        for tool in data.required_action.submit_tool_outputs.tool_calls:

            params_loaded= tool.function.arguments
            params= json.loads(params_loaded)
            print(f"Requested Tool: {tool.function.name}, Params: {params}")
            print(type(params))

            if isinstance(params, str):
                try:
                    params= json.loads(params)
                except json.JSONDecodeErrror as e:
                    print(f"Error decoding JSON: {e}")
            
            # while True:
            #     time.sleep(1)

            elif tool.function.name == "download_file":
                file_data= download_file(**params)
                tool_outputs.append({"tool_call_id": tool.id, "output": f'{file_data}'})
                
            # elif tool.function.name == "send_email":
            #     send_email_output= send_email(**params)
            #     tool_outputs.append({"tool_call_id": tool.id, "output": f'{send_email_output}'})

        # while True:
        #         time.sleep(1)

        self.submit_tool_outputs(tool_outputs, run_id)


    def submit_tool_outputs(self, tool_outputs, run_id):


        # Use the submit_tool_outputs_stream helper

        with client.beta.threads.runs.submit_tool_outputs_stream(
            thread_id= self.current_run.thread_id,
            run_id= run_id,
            tool_outputs= tool_outputs,
            event_handler= EventHandler(),
        ) as stream:
            stream.until_done()
            for text in stream.text_deltas:
                print(text, end="", flush= True)
            print()


# Start Run
def start_run(thread_id, assistant_id):

    try:
        with st.spinner('Typing...'):

            with client.beta.threads.runs.stream(
                thread_id= thread_id,
                assistant_id= assistant_id,
                event_handler= EventHandler()
            ) as stream:
                stream.until_done()

    except openai.BadRequestError as e:
        if 'already has an active run' in str(e):
            print("An active run is already in progress. Please wait for it to complete.")
        else:
            print(f"An error occurred: {e}")


# End Run
def end_chat():
    st.session_state.start_chat= False
    st.session_state.thread_id= None
    st.session_state.messages= []
    st.rerun()


# Upload to OpenAI
def upload_openai(file_path, file_name):

    with open(file_path, "rb") as files:

        file_batch= client.beta.vector_stores.files.upload_and_poll(
                vector_store_id=vector_id, file= files
                )
                
        time.sleep(2)

        print(file_batch.status)
        st.sidebar.success(f'File successfully uploaded: {file_name}')

    if os.path.exists(file_path):
        os.remove(file_path)


def send_user_message(content):
    global thread_id
    
    user_message = client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=content
    )
    return user_message



# run_cancel= client.beta.threads.runs.cancel(
#     run_id='run_KTk7QmYTQtaI9qlag9CPRPJG', thread_id= thread_id
# )

# print(run_cancel.status)


# while True:
#     time.sleep(1)

# Set Steamlit Application

st.set_page_config(page_title="Legal Assistant", page_icon= ":robot_face:")

st.title("Legal Assistant")
st.write("Interact with the legal assistant for your business needs")


if "is_processing" not in st.session_state:
    st.session_state.is_processing= False


# End Chat to refresh thread

if st.sidebar.button("End Chat"):

    thread_id_updated= new_thread()
    st.session_state.start_chat= False
    st.session_state.thread_id= thread_id_updated
    st.session_state.messages= []
        
    st.rerun()


# Button to initiate the chat session

if st.sidebar.button("Start Chat"):
    st.session_state.start_chat= True
    st.session_state.thread_id= thread_id


if "start_chat" not in st.session_state:
    st.session_state.start_chat= False
    st.sidebar.warning("Please click on 'Start Chat' to speak to your agent!")


if "thread_id" not in st.session_state:
    st.session_state.thread_id= None


if "messages" not in st.session_state:
    st.session_state.messages= []
    st.write("Get started by entering your text below!")


if "file_uploader" not in st.session_state:
    st.session_state.file_uploader= None


# Side bar where users can upload files

file_uploader = st.sidebar.file_uploader("Upload any file below", 
                                    accept_multiple_files= True,
                                    key =0)


# Upload file button - store

if st.sidebar.button("Upload File"):

    file_list= []

    if file_uploader is not None:

        for file in file_uploader:

            file_name = os.path.basename(file.name)
            file_path = os.path.join(os.getcwd(), file_name)
            print(file_path)
            
            with open(file_path, "wb") as f:
                f.write(file.getbuffer())

            upload_openai(file_path, file_name)

        st.session_state.file_uploader= file_uploader

    else:
        st.warning("File upload failed, please try to re-upload documents")


# Check sessions

# st.write(thread_id)

# Show existing messages if any

if st.session_state.start_chat:
    
        for message in st.session_state.messages:

            with st.chat_message(message["role"]):
                    st.markdown(message["content"])


    # Chat input for the user

        if prompt := st.chat_input("Enter text here..."):

            # Display user messages
            with st.chat_message("user", avatar= "user"):
                st.markdown(prompt)

            # Add chat history
            st.session_state.messages.append({"role": "user", "content": prompt})


        # Add the user's message to the existing thread
            send_user_message(prompt)

            start_run(thread_id, assis_id)
                
                # Retrieve messages added by the assistant

            assis_message= client.beta.threads.messages.list(
                thread_id= thread_id
            )
            
        
            # Process assistant messages

            message_response= assis_message.data[0]

            if message_response.role == 'assistant':
                    
                final_response= message_response.content[0].text.value

                final_clean = re.sub(pattern=r'【\d+:\d+†.*?】', repl='', string=final_response)


                # Display Assistant messages
                with st.chat_message("assistant"):
                    st.markdown(final_clean)

                st.session_state.messages.append(
                    {"role": "assistant", 
                    "content": final_clean}
                )

            # Set processing state to False after processing is complete

            st.session_state.is_processing= False