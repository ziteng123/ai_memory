import langextract as lx
import textwrap
from pymilvus import MilvusClient, DataType
import uuid
from langchain_ollama import OllamaEmbeddings

COLLECTION_NAME = "document_extractions"
EMBEDDING_MODEL = "bge-m3:latest"

client = MilvusClient(uri="./milvus_demo.db")

sample_documents = [ "John McClane fights terrorists in a Los Angeles skyscraper during Christmas Eve. The action-packed thriller features intense gunfights and explosive scenes.",    "A young wizard named Harry Potter discovers his magical abilities at Hogwarts School. The fantasy adventure includes magical creatures and epic battles.",    "Tony Stark builds an advanced suit of armor to become Iron Man. The superhero movie showcases cutting-edge technology and spectacular action sequences.",    "A group of friends get lost in a haunted forest where supernatural creatures lurk. The horror film creates a terrifying atmosphere with jump scares.",    "Two detectives investigate a series of mysterious murders in New York City. The crime thriller features suspenseful plot twists and dramatic confrontations.",    "A brilliant scientist creates artificial intelligence that becomes self-aware. The sci-fi thriller explores the dangers of advanced technology and human survival.",    "A romantic comedy about two friends who fall in love during a cross-country road trip. The drama explores personal growth and relationship dynamics.",    "An evil sorcerer threatens to destroy the magical kingdom. A brave hero must gather allies and master ancient magic to save the fantasy world.",    "Space marines battle alien invaders on a distant planet. The action sci-fi movie features futuristic weapons and intense combat in space.",    "A detective investigates supernatural crimes in Victorian London. The horror thriller combines period drama with paranormal investigation themes.",]
print("=== LangExtract + Milvus Integration Demo ===")
print(f"Preparing to process {len(sample_documents)} documents")

print("\n1. Setting up Milvus collection...")
if client.has_collection(collection_name=COLLECTION_NAME):
    client.drop_collection(collection_name=COLLECTION_NAME)
    print(f"Dropped existing collection: {COLLECTION_NAME}")

schema = client.create_schema(auto_id=False,
                                  enable_dynamic_field=True,
                                  description="Document extraction results and vector storage",)
schema.add_field(
    field_name="id", datatype=DataType.VARCHAR, max_length=100, is_primary=True
)
schema.add_field(
    field_name="document_text", datatype=DataType.VARCHAR, max_length=10000
)
schema.add_field(
    field_name="embedding", datatype=DataType.FLOAT_VECTOR, dim=1024
)
client.create_collection(collection_name=COLLECTION_NAME, schema=schema)
print(f"Collection '{COLLECTION_NAME}' created successfully")
index_params = client.prepare_index_params()
index_params.add_index(field_name="embedding",    index_type="AUTOINDEX",    metric_type="COSINE",)
client.create_index(collection_name=COLLECTION_NAME, index_params=index_params)
print("Vector index created successfully")

