import json
import boto3

def lambda_handler(event, context):
    # TODO implement
    message = event['body'].split('"text":')[1].split('"')[1]
    userId = event["requestContext"]["accountId"]
    
    client = boto3.client('lex-runtime')
    response = client.post_text(
    botName='GetDinnerSuggestions',
    botAlias='prod',
    userId= userId,
    inputText= message)
    
    return {
        'statusCode': 200,
        'headers': {"Access-Control-Allow-Origin" : "*" },
        'body': json.dumps({'messages': [ {'type': "unstructured", 'unstructured': {'text': response["message"]}  } ] } )
    }
