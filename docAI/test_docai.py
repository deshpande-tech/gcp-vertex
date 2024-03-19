from typing import Optional

import pytest
from google.api_core.client_options import ClientOptions
from google.api_core.exceptions import NotFound
from google.cloud import documentai
import PyPDF2
from io import BytesIO

project_id = '<<your_project_id>>'
location = 'us'  # Format is 'us' or 'eu'
document_ai_url = 'https://documentai.googleapis.com'
token = '<<token>>'


def create_processor(
        processor_display_name: str, processor_type: str, transport: str
):
    # You must set the api_endpoint if you use a location other than 'us'.
    opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")

    client = documentai.DocumentProcessorServiceClient(client_options=opts, transport=transport)

    # The full resource name of the location
    # e.g.: projects/project_id/locations/location
    parent = client.common_location_path(project_id, location)

    # Create a processor
    processor = client.create_processor(
        parent=parent,
        processor=documentai.Processor(
            display_name=processor_display_name, type_=processor_type
        ),
    )

    return processor

def delete_processor(processor_name: str, transport: str):
    # You must set the api_endpoint if you use a location other than 'us'.
    opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")

    client = documentai.DocumentProcessorServiceClient(client_options=opts, transport=transport)


    # Delete a processor
    try:
        operation = client.delete_processor(name=processor_name)
        # Wait for operation to complete
        operation.result()
        return {"message": processor_name + " deleted!"}
    except NotFound as e:
        return {"message": e.message}

def process_document(pdf_file_path, processor_name, transport, chunk_size=15):
    with open(pdf_file_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        num_pages = len(pdf_reader.pages)
        num_chunks = (num_pages + chunk_size - 1) // chunk_size

        for i in range(num_chunks):
            start_page = i * chunk_size
            end_page = min((i + 1) * chunk_size - 1, num_pages - 1)
            chunk_pdf_writer = PyPDF2.PdfWriter()

            for page_num in range(start_page, end_page + 1):
                page = pdf_reader.pages[page_num]
                chunk_pdf_writer.add_page(page)

            # Create a BytesIO object to hold the chunked PDF
            chunk_pdf_bytes = BytesIO()
            chunk_pdf_writer.write(chunk_pdf_bytes)
            chunk_pdf_bytes.seek(0)
            ocr_response = document_ai(processor_name, chunk_pdf_bytes.read(), transport)
            
            import os
            output_file_path = os.path.join(os.getcwd(), "examples/python/docAI/assets","2023-07-27-notice-dis-a-fr.txt")
            with open(output_file_path, 'a', encoding='utf-8') as text_file:
                text_file.write(ocr_response)
    return "Done"



def document_ai(processor_name: str, chunk_pdf_bytes, transport):

    # You must set the `api_endpoint` if you use a location other than "us".
    client = documentai.DocumentProcessorServiceClient(
        client_options=ClientOptions(
            api_endpoint=f"{location}-documentai.googleapis.com"
        ), transport=transport
    )

    ocr_config = documentai.OcrConfig(
        enable_symbol=False,
        enable_native_pdf_parsing=True,
        premium_features=documentai.OcrConfig.PremiumFeatures(
            enable_math_ocr=True,  # Enable to use Math OCR Model
        ),
    )
    process_options = documentai.ProcessOptions(ocr_config=ocr_config)

    # Configure the process request
    request = documentai.ProcessRequest(
        name=processor_name,
        raw_document=documentai.RawDocument(content=chunk_pdf_bytes, mime_type="application/pdf"),
        # Only supported for Document OCR processor
        process_options=process_options,
    )
    result = client.process_document(request=request)
    return result.document.text

def multiturn_generate_content(config, project_id, location_id):
  import vertexai
  from vertexai.preview.generative_models import GenerativeModel

  vertexai.init(
      project=project_id,
      location=location_id,
   )
 
  model = GenerativeModel("gemini-pro")
  chat = model.start_chat()
 
  # Define your initial prompt
  initial_prompt = "What is the future of AI?"
 
  # Send initial prompt and get response
  response = chat.send_message(initial_prompt)
  print(response.text)  # Print the response to the initial prompt
 
  # Loop for follow-up questions
  while True:
    question = input("Ask your question (or 'q' to quit): ")
    if question.lower() == 'q':
      break
    response = chat.send_message(question)
    print(response.text)
 
  return  # Optional: You can return the entire chat history here


@pytest.fixture(scope='function')
def grpc_ocr_processor(request):
    processor = create_processor("my_ocr_processor", "OCR_PROCESSOR", "grpc")

    def teardown():
        delete_processor(processor.name, "grpc")

    request.addfinalizer(teardown)

    return processor

@pytest.fixture(scope='function')
def grpc_math_ocr_processor(request):
    processor = create_processor("my_math_ocr_processor", "OCR_PROCESSOR", "grpc")

    def teardown():
        delete_processor(processor.name, "grpc")

    request.addfinalizer(teardown)

    return processor

@pytest.fixture(scope='function')
def rest_ocr_processor(request):
    processor = create_processor("my_ocr_processor", "OCR_PROCESSOR", "rest")

    def teardown():
        delete_processor(processor.name, "rest")

    request.addfinalizer(teardown)

    return processor


@pytest.fixture(scope='function')
def grpc_usdl_processor(request):
    processor = create_processor("my_us_dl_processor", "US_DRIVER_LICENSE_PROCESSOR", "grpc")

    def teardown():
        delete_processor(processor.name, "grpc")

    request.addfinalizer(teardown)

    return processor


@pytest.fixture(scope='function')
def rest_usdl_processor(request):
    processor = create_processor("my_us_dl_processor", "US_DRIVER_LICENSE_PROCESSOR", "rest")

    def teardown():
        delete_processor(processor.name, "grpc")

    request.addfinalizer(teardown)

    return processor


class TestDocumentAI:

    def test_ocr_processor_grpc(self, grpc_ocr_processor):
        
        result = process_document("docAI/assets/2023-07-27-notice-dis-a-fr.pdf", grpc_ocr_processor.name, "grpc")
        multiturn_generate_content()
        assert result.__contains__("Done")