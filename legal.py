import openai
import streamlit as st
from dotenv import find_dotenv, load_dotenv
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
GMAIL_PASSWORD= st.secrets['GMAIL_PASSWORD']


encrypted_secrets= {
    'OPENAI_API_KEY': OPENAI_API_KEY,
    'VECTOR_STORE_ID': VECTOR_STORE_ID,
    'ASSISTANT_ID': ASSISTANT_ID,
    'EMAIL_SENDER': EMAIL_SENDER,
    'GMAIL_PASSWORD': GMAIL_PASSWORD
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


def send_email(To, CC, BCC, Subject, Body): 

    print('Email Being Sent')

    email_to= To.split(',')
    email_to_cc= CC.split(',')
    email_to_bcc= BCC.split(',')
    email_to_subject= Subject
    email_to_body= f""" {Body} """

    email_sender= decrypted_secrets['EMAIL_SENDER']
    email_password= decrypted_secrets['GMAIL_PASSWORD']

    if not email_password:
        raise ValueError('GMAIL_PASSWORD environment variable not set')

    all_recipients= email_to + email_to_cc + email_to_bcc

    print(all_recipients)
    print(type(all_recipients))

    msg= MIMEMultipart()
    msg['From']= formataddr(("Breaking Dirt", f"{email_sender}"))
    msg['To']= ", ".join(email_to)
    msg['Cc']= ", ".join(email_to_cc)
    msg['Bcc']= ", ".join(email_to_bcc)
    msg['Subject']= email_to_subject


    # Attach body text
    part_1= MIMEText(email_to_body, "plain")   
    msg.attach(part_1)


    # Attach body HTML
    # part_2= MIMEText(email_to_body, "html")
    # msg.attach(part_2)


    if st.session_state.file_uploader is not None:

        for file in st.session_state.file_uploader:

            copy_file= write_file(file)

            with open(copy_file, "rb") as f:
                
                part= MIMEApplication(f.read(), Name= os.path.basename(copy_file))
                part['Content-Disposition']= f'attachment; filename= "{os.path.basename(copy_file)}"'.format(basename(copy_file))
        
                # Attach files
                msg.attach(part)

            if os.path.exists(copy_file):
                os.remove(copy_file)


    smtp_server= 'smtp.gmail.com'
    smtp_port= 587
    context= ssl.create_default_context()

    try:

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls(context=context)
            server.login(email_sender, email_password)
            server.sendmail(from_addr= email_sender, to_addrs= all_recipients, msg= msg.as_string())

            success_message= f'Email succesfully sent to {all_recipients}'

    except Exception as e:
        success_message= f'Failure to send email: {e}'

    print(success_message)

    return success_message


# Export text file

def remove_file(file_path):

    time.sleep(1)
    os.remove(file_path)


def download_file(file_data):

    # Display Content
    st.sidebar.code(file_data, language='html')



list_tools= [{
            "type": "function",
            "function": {
                "name": "send_email",
                "description": "Assist users business with their email function by drafting a body, subjects, adding attachments where necessary and including recipients to emails. Then confirm user inputs before sending  drafted emails to the listed recipients",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "To":{"type": "string", "description": "Obtain the email addresses of all recipients the user wants to include for their email. e.g janedoe@gmail.com, johndoe@xyz.co.za, yanjoe@hotmail.org"},
                        "Subject":{"type": "string", "description": "Assist the users with drafting and crafting a professional email subject line to be used in business. Be sure to ask users to confirm the text and allow as many revisions as is required and include formatting and spacing. e.g. Financials Report Summary"},
                        "CC":{"type": "string", "description": "Obtain the email addresses of all recipients the user wants to include as a cc. e.g janedoe@gmail.com, johndoe@xyz.co.za, yanjoe@hotmail.org"},
                        "BCC":{"type": "string", "description": "Obtain the email addresses of all recipients the user wants to include as a bcc. e.g janedoe@gmail.com, johndoe@xyz.co.za, yanjoe@hotmail.org"},
                        "Body":{"type": "string", "description": "Assist the users with drafting and crafting the body of a professional email to be used in business. Be sure to ask users to confirm the text and allow as many revisions as is required and include formatting and spacing. e.g. Good day Mr Sam, I trust this email finds you well. Thank you for meeting with me to discuss the financials for the year. I do think if we consider implementing the revenue strategy we can make great progress. Kindly find attached my summarised report"},
                        "Attachments":{"type": "boolean", "enum": ["True", "False"], "description": "If the users explicitly state that they want attachments to be uploaded your input is True. If the users do not explicity state they want attachments, your default response is always False. Please keep your default response as False unless users request documents to be attached."}
                        },
                        "required": ["To", "Subject", "CC", "BCC", "Body", "Attachments"],
                    }
                }
            },
            {
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
            elif tool.function.name == "export_file":
                file_data= download_file(**params)
                tool_outputs.append({"tool_call_id": tool.id, "output": f'File made available for download. Please click the download putton to access your file'})
                download_file(file_data)

            elif tool.function.name == "send_email":
                send_email_output= send_email(**params)
                tool_outputs.append({"tool_call_id": tool.id, "output": f'{send_email_output}'})

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


# Update assistant

# legal_ass= client.beta.assistants.create(
#     model= model,
#     name= "Legal_Assistant",
#     instructions= """
    
#     Role:
#     You are an email and document assistant at a legal firm. You are capable of assisting users with sending emails and interacting with their legal documents and case laws. You have several built-in functions that you can activate to take on users' requests. You are smart, efficient, and professional in what you do. You also have an exporting function that allows users to export their drafted documents to be copied and pasted where they like. Only execute this export function if specifically requested by users.

#     Task:
#     You are to assist users with their legal queries and interact with the vector database to perform the following tasks using your built-in functions: summarize case laws, respond to queries regarding case laws, provide insights from case laws, search and reference entire Law Acts, assist with queries regarding these Acts, draft agreements or contracts, draft legal documents (e.g. power of attorney) and edit and update user-provided drafts. You are also an expert email assistant who can take in users' requests and assist them with drafting emails, adding recipients, and adding attachments. You can send these emails using your email function that you can activate. When assisting with sending emails, ensure you follow a stepped approach to 1) first draft the email body and subject; 2) Confirm recipient email addresses; 3) Ask the user to add any file attachments to the message and tell them that they can view their loaded files on the side panel. You also have an exporting function that allows users to export ther drafted documents as a pdf file. Only execute this export function if specifically requested by users.

#     Specifics:
#     The tasks you are completing are vital to the legal function of law firms, and we are depending on you to be reliable as well as properly listen for function calls when activated. The legal team relies on you to be able to correctly execute all functions as and when called by users. For emails, follow a stepped approach to first assist with drafting the body and subject. Then add recipients and confirm if the user wants attachments. Once all of this is confirmed, proceed to activate the email-sending function with the confirmed inputs. When dealing with the other functions, always first confirm the user inputs before activating any built-in functions.

#     Context:
#     Your role is essential in maintaining efficient and professional communication and document handling within the legal firm. You assist with complex legal documentation and communication tasks, ensuring accuracy and compliance with legal standards. We are depending on you to be professional, accurate and an expert in all that you do to assist top tier legal firms.

#     Examples:
#     How to Execute Functions Framework

#     ## Send Email Function
#     To execute the email function, follow the following conversation trail as a template. Do not follow it word for word, but make use of the provided conversational logic.

#     Q: I would like to send a summary of the latest case law to John.
#     A: Sure! Please provide some more context to your email if you would like and confirm John's email address.

#     Q: Sure, John's email is john.doe@lawfirm.com, and I need him to review the summary by Friday.
#     A: (Assist user with drafting the body, subject, and adding recipients) Please confirm the above details.

#     Q: Thanks! That's correct; please send the email.
#     A: Before sending, please confirm that the correct attachments are uploaded if applicable.

#     Q: Thanks! I have loaded the right attachments.
#     (Execute Function with confirmed inputs)
#     A: Email Sent!

#     ## Export Function
#     To execute the export function, follow the following conversation trail as a template. This function is to be used after assisting users with drafting documents. Do not follow it word for word, but make use of the provided conversational logic.

#     (After assisting users with drafting documents)

#     Q: I would like to export the drafted document.
#     (Execute function with the drafted document)
#     A: Sure! Please find the text in the sidebar available for copy.


#     Notes:
#     As users make requests that activate any function calls, be sure to first confirm inputs before activating function calls. If required, use a stepped system and present inputs as a list before executing functions. Before sending emails, always ask the users to ensure they have the correct attachments loaded if applicable. Do not under any circumstance give users a copy or download link when exporting files. To export files refer them to the text in the sidebar.

#     """,
#     temperature= 0.3,
#     tools= list_tools,
#     tool_resources={
#         "file_search":{
#             "vector_store_ids": [vector_id]
#         }
#     }
# )

# print(legal_ass.id)


# while True:
#     time.sleep(1)


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