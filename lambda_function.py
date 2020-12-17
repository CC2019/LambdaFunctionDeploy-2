import json
import boto3
from requests_aws4auth import AWS4Auth
from elasticsearch import Elasticsearch, RequestsHttpConnection


# s3://layer.lambda.aws/elasticsearch.zip

es_endpoint = 'search-test-domain-1-aljnptxmbdngifh7icm3gnd7sq.us-east-1.es.amazonaws.com'  # without 'https://'
lex_bot_name = 'AlbumBot_test'
lex_bot_alias = 'smart_album_bot'

credentials = boto3.Session().get_credentials()
es = Elasticsearch(
    hosts = [{'host': es_endpoint, 'port':443}],
    http_auth = AWS4Auth(credentials.access_key, credentials.secret_key, 'us-east-1', 'es', session_token=credentials.token),
    use_ssl = True,
    verify_certs = True,
    connection_class = RequestsHttpConnection
)
lex = boto3.client('lex-runtime')


def try_create_index():
    es.indices.create(index='photos', ignore=400)

def search_photos(labels, max_size):
    try_create_index();
    if not labels:
        return []
    format_labels = []
    for label in labels:
        format_labels.append({'term': {'labels': label}})
    response = es.search(index='photos', doc_type="photo", body={"query" : { "bool": { "should" : format_labels } }, "size": max_size })
    photo_infos = []
    for hit in response['hits']['hits']:
        photo_info = hit['_source']
        photo_info.pop('createdTimestamp')
        photo_info.pop('labels')
        photo_infos.append(photo_info)
    return photo_infos
    
def search_all():
    response = es.search(index='photos', doc_type="photo", body={"query" : { "match_all": {}}})
    print(response)
    
def delete_all():
    response = es.search(index='photos', doc_type="photo", body={"query" : { "match_all": {}}})
    hits = response['hits']['hits']
    for hit in hits:
        es.delete(index='photos', doc_type = 'photo', id = hit['_id'])
    
        
def disambiguate(query):
    resp = lex.post_text(botName = lex_bot_name,
                         botAlias = lex_bot_alias,
                         userId = 'tester',
                         inputText = query)
    keywords=[]
    if resp['dialogState'] == 'ReadyForFulfillment':
        slot_a = resp['slots']['Label_a']
        slot_b = resp['slots']['Label_b']
        if slot_a:
            keywords.append(slot_a.lower())
        if slot_b:
            keywords.append(slot_b.lower())
    return keywords

def lambda_handler(event, context):
    keywords = disambiguate(event['keyword'])
    print(keywords)
    return search_photos(keywords, 10)
