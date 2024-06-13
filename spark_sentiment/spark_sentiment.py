from __future__ import print_function

from pyspark import SparkContext
from pyspark.conf import SparkConf
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, udf, to_json, struct
from pyspark.sql.types import StructType, StructField, StringType, BooleanType
import json
import random
from openai import OpenAI
from pyspark.sql.functions import split
from elasticsearch import Elasticsearch
import os

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "sk-proj-6ijZFEArB42wzCDvU6VXT3BlbkFJKigjxocZSrBQrr7oxIRl")

# Initialize Spark Context and Session
es = Elasticsearch("http://elasticsearch:9200")
sparkConf = SparkConf().set("es.nodes", "elasticsearch") \
                        .set("es.port", "9200") \
                        .set("es.index.auto.create", "true")

mapping = {
    "mappings": {
        "properties": {
            "timestamp": {
                "type": "date",  # Definisce il campo come tipo date
                "format": "epoch_millis"  # Formati di data accettati
            }
        }
    }
}

elastic_index="twitchmessages"

if not es.indices.exists(index=elastic_index):
    es.indices.create(index=elastic_index, body=mapping)
else:
    # Se l'indice esiste già e vuoi aggiornare il mapping
    es.indices.put_mapping(index=elastic_index, body=mapping['mappings'])

sc = SparkContext(appName="PythonStructuredStreamsKafka", conf=sparkConf)
spark = SparkSession(sc)
sc.setLogLevel("ERROR")

# Kafka configuration
kafkaServer = "host.docker.internal:9092"
inputTopic = "no_emotes_general"
kafkaOutputServer = "host.docker.internal:9092"
outputTopic = "enriched_chat"

# Define the schema for the JSON data
json_schema = StructType([
    StructField("is_subscriber", BooleanType(), True),
    StructField("is_mod", BooleanType(), True),
    StructField("channel", StringType(), True),
    StructField("content", StringType(), True),
    StructField("chatter_name", StringType(), True),
    StructField("is_vip", BooleanType(), True),
    StructField("is_broadcaster", BooleanType(), True)
])

# Read streaming data from Kafka
df = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", kafkaServer) \
    .option("subscribe", inputTopic) \
    .load()

# Select the value and timestamp fields and cast them to string
df = df.selectExpr("CAST(value AS STRING)", "CAST(timestamp AS TIMESTAMP)")

# Parse the JSON content and extract fields
json_df = df.withColumn("json_data", from_json(col("value"), json_schema)) \
            .select("json_data.*", col("timestamp"))

""" # Funzione per generare un sentimento casuale (per non sprecare i token di ChatGPT)
def chatgpt_sentiment(text):
    if text is not None and text.strip() != "":
        sentiment = random.uniform(-1,1)
        emotion_list = ["happy", "sad", "angry", "neutral", "surprised", "disgusted", "fearful"]
        emotion = random.choice(emotion_list)
        return f"{sentiment}, {emotion}"
    else:
        return "0, neutral" """
    
def chatgpt_sentiment(text):
    if text is not None and text.strip() != "":
        client = OpenAI(api_key=OPENAI_API_KEY)   
        response = client.chat.completions.create(
            model='gpt-3.5-turbo',
            messages=[{'role': 'system', 'content': 'Classify the sentiment of the following message. Sentiment is a float from -1 to 1, where -1 is negative, 0 is neutral and 1 is positive. Emotion is a word representing the emotion of the message, can be one of the following: happy, sad, angry, neutral, surprised, disgusted, fearful. The response must be a JSON with two fields: sentiment and emotion'}, {"role": "user", "content": text}],
            max_tokens=100,
            temperature=0
        )

        data = json.loads(response.model_dump_json())
        print(json.dumps(data, indent=4))
        
        # Estrai il sentiment o l'emozione dalla risposta
        parsed_data = json.loads(data['choices'][0]['message']['content'])
        return f"{parsed_data['sentiment']}, {parsed_data['emotion']}"
    else:
        return "0, neutral"
    
chatgpt_sentiment_udf = udf(chatgpt_sentiment, StringType())
    
json_df = json_df.withColumn("gpt_sentiment", chatgpt_sentiment_udf(col("content")))

# Split the gpt_sentiment column into sentiment and emotion columns
split_col = split(col("gpt_sentiment"), ", ")
json_df = json_df.withColumn("sentiment", split_col.getItem(0).cast("float")) \
                 .withColumn("emotion", split_col.getItem(1))

# Rimuovi la colonna gpt_sentiment
json_df = json_df.drop("gpt_sentiment")

kafka_compatible_df = json_df.select(to_json(struct(*[col for col in json_df.columns])).alias("value")) # Creazione di un df compatibile con Kafka

# Scrivi il DataFrame a Elasticsearch
elasticQuery = json_df.writeStream \
   .option("checkpointLocation", "/tmp/") \
   .format("es") \
   .start(elastic_index)

kafkaQuery = kafka_compatible_df.writeStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", kafkaOutputServer) \
    .option("topic", outputTopic) \
    .option("checkpointLocation", "/tmp/kafka_checkpoint") \
    .start()

""" json_df.writeStream \
    .outputMode("append") \
    .format("console") \
    .option("truncate", False) \
    .start() \
    .awaitTermination() """

elasticQuery.awaitTermination()
kafkaQuery.awaitTermination()
