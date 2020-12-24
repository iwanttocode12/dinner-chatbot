"""
This sample demonstrates an implementation of the Lex Code Hook Interface
in order to serve a sample bot which manages orders for flowers.
Bot, Intent, and Slot models which are compatible with this sample can be found in the Lex Console
as part of the 'OrderFlowers' template.

For instructions on how to set up and test this bot, as well as additional samples,
visit the Lex Getting Started documentation http://docs.aws.amazon.com/lex/latest/dg/getting-started.html.
"""
import math
import dateutil.parser
import datetime
import time
import os
import logging

import boto3  
import json

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


""" --- Helpers to build responses which match the structure of the necessary dialog actions --- """


def get_slots(intent_request):
    return intent_request['currentIntent']['slots']


def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }


def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

    return response


def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }


""" --- Helper Functions --- """


def parse_int(n):
    try:
        return int(n)
    except ValueError:
        return float('nan')


def build_validation_result(is_valid, violated_slot, message_content):
    if message_content is None:
        return {
            "isValid": is_valid,
            "violatedSlot": violated_slot,
        }

    return {
        'isValid': is_valid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }


def isvalid_date(date):
    try:
        dateutil.parser.parse(date)
        return True
    except ValueError:
        return False


def validate_order_flowers(flower_type, date, pickup_time):
    flower_types = ['lilies', 'roses', 'tulips']
    if flower_type is not None and flower_type.lower() not in flower_types:
        return build_validation_result(False,
                                       'FlowerType',
                                       'We do not have {}, would you like a different type of flower?  '
                                       'Our most popular flowers are roses'.format(flower_type))

    if date is not None:
        if not isvalid_date(date):
            return build_validation_result(False, 'PickupDate', 'I did not understand that, what date would you like to pick the flowers up?')
        elif datetime.datetime.strptime(date, '%Y-%m-%d').date() <= datetime.date.today():
            return build_validation_result(False, 'PickupDate', 'You can pick up the flowers from tomorrow onwards.  What day would you like to pick them up?')

    if pickup_time is not None:
        if len(pickup_time) != 5:
            # Not a valid time; use a prompt defined on the build-time model.
            return build_validation_result(False, 'PickupTime', None)

        hour, minute = pickup_time.split(':')
        hour = parse_int(hour)
        minute = parse_int(minute)
        if math.isnan(hour) or math.isnan(minute):
            # Not a valid time; use a prompt defined on the build-time model.
            return build_validation_result(False, 'PickupTime', None)

        if hour < 10 or hour > 16:
            # Outside of business hours
            return build_validation_result(False, 'PickupTime', 'Our business hours are from ten a m. to five p m. Can you specify a time during this range?')

    return build_validation_result(True, None, None)


""" --- Functions that control the bot's behavior --- """


def order_flowers(intent_request):
    """
    Performs dialog management and fulfillment for ordering flowers.
    Beyond fulfillment, the implementation of this intent demonstrates the use of the elicitSlot dialog action
    in slot validation and re-prompting.
    """

    flower_type = get_slots(intent_request)["FlowerType"]
    date = get_slots(intent_request)["PickupDate"]
    pickup_time = get_slots(intent_request)["PickupTime"]
    source = intent_request['invocationSource']

    if source == 'DialogCodeHook':
        # Perform basic validation on the supplied input slots.
        # Use the elicitSlot dialog action to re-prompt for the first violation detected.
        slots = get_slots(intent_request)

        validation_result = validate_order_flowers(flower_type, date, pickup_time)
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] = None
            return elicit_slot(intent_request['sessionAttributes'],
                               intent_request['currentIntent']['name'],
                               slots,
                               validation_result['violatedSlot'],
                               validation_result['message'])

        # Pass the price of the flowers back through session attributes to be used in various prompts defined
        # on the bot model.
        output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
        if flower_type is not None:
            output_session_attributes['Price'] = len(flower_type) * 5  # Elegant pricing model

        return delegate(output_session_attributes, get_slots(intent_request))

    # Order the flowers, and rely on the goodbye message of the bot to define the message to the end user.
    # In a real bot, this would likely involve a call to a backend service.
    return close(intent_request['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': 'Thanks, your order for {} has been placed and will be ready for pickup by {} on {}'.format(flower_type, pickup_time, date)})



def validate_make_suggestions(cuisine_type, location, dining_time):
    cuisine_types = ['mexican', 'thai', 'chinese', 'italian', 'indian']
    if cuisine_type is not None and cuisine_type.lower() not in cuisine_types:
        return build_validation_result(False,
                                       'Cuisine',
                                       'We do not have suggestions for {}, would you like a Cuisine?  '
                                       'Our choices are Mexican, Indian, Thai, Chinese and Italian'.format(cuisine_type))
    
    loc_types = ['manhattan']
    if location is not None and location.lower() not in loc_types:
        return build_validation_result(False,
                                       'Location',
                                       'We do not have suggestions for {}. We currently only have suggestions for Manhattan.'.format(location))

    if dining_time is not None:
        if len(dining_time) != 5:
            return build_validation_result(False, 'DiningTime', None)

        hour, minute = dining_time.split(':')
        hour = parse_int(hour)
        minute = parse_int(minute)
        if math.isnan(hour) or math.isnan(minute):
            return build_validation_result(False, 'DiningTime', None)

        if hour < 17 or hour > 20:
            return build_validation_result(False, 'DiningTime', 'Most dining hours are from five p m. to eight p m. Can you specify a time during this range?')
            
    return build_validation_result(True, None, None)


""" --- Functions that control the bot's behavior --- """


def make_suggestions(intent_request):
    """
    Performs dialog management and fulfillment for ordering flowers.
    Beyond fulfillment, the implementation of this intent demonstrates the use of the elicitSlot dialog action
    in slot validation and re-prompting.
    """

    cuisine_type = get_slots(intent_request)["Cuisine"]
    location = get_slots(intent_request)["Location"]
    dining_time = get_slots(intent_request)["DiningTime"]
    numPeople = get_slots(intent_request)["NumPeople"]
    phoneNumber = get_slots(intent_request)["PhoneNumber"]
    source = intent_request['invocationSource']

    if source == 'DialogCodeHook':
        # Perform basic validation on the supplied input slots.
        # Use the elicitSlot dialog action to re-prompt for the first violation detected.
        slots = get_slots(intent_request)

        validation_result = validate_make_suggestions(cuisine_type, location, dining_time)
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] = None
            return elicit_slot(intent_request['sessionAttributes'],
                               intent_request['currentIntent']['name'],
                               slots,
                               validation_result['violatedSlot'],
                               validation_result['message'])

        # Pass the price of the flowers back through session attributes to be used in various prompts defined
        # on the bot model.
        output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
        return delegate(output_session_attributes, get_slots(intent_request))

    # Order the flowers, and rely on the goodbye message of the bot to define the message to the end user.
    # In a real bot, this would likely involve a call to a backend service.
    return close(intent_request['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': 'Thanks an sms of suggestions for {} food in {} at {} for {} people would be sent to {}.'.format(cuisine_type, location, dining_time, numPeople, phoneNumber)})


"""
def validate_make_suggestions(location, cuisine, dining_time, num_people, phone_number):

    if location is not None and location.lower() != 'manhattan':
        return build_validation_result(False,
                                       'Location',
                                       'We do not have suggestions for {}. We currently only have suggestions for Manhattan.'.format(location))
                        
    cuisine_types = ['mexican', 'chinese', 'italian', 'thai', 'indian']
    if cuisine is not None and cuisine.lower() not in cuisine_types:
        return build_validation_result(False,
                                       'Cuisine',
                                       'We do not have suggestions for {}, We currently only have suggestions for Mexican, Chinese, Italian, Thai and Indian. '
                                       'Please select one from these choices'.format(cuisine))

    if dining_time is not None:
        if len(dining_time) != 5:
            return build_validation_result(False, 'DiningTime', None)
        
        hour, minute = dining_time.split(':')
        hour = parse_int(hour)
        minute = parse_int(minute)
        if math.isnan(hour) or math.isnan(minute):
            return build_validation_result(False, 'DiningTime', None)
            
        if hour <17 or hour > 20:
            return build_validation_result(False, 'DiningTime', 'Most dining hours are from five p m. to eight p m. Can you specify a time during this range?')
     
   
    if num_people is not None:
        num = parse_int(num_people)
        if math.isnan(num) and num <= 0:
            return build_validation_result(False, 'NumPeople', 'Enter a positive whole number')
            

    if phone_number is not None:
        if len(phone_number) != 10:
            return build_validation_result(False, 'PhoneNumber', 'Enter a valid phone number in the format 5555555555')
    return build_validation_result(True, None, None)


def make_suggestions(intent_request):
    
    location = get_slots(intent_request)["Location"]
    cuisine = get_slots(intent_request)["Cuisine"]
    num_people = get_slots(intent_request)["NumPeople"]
    dining_time = get_slots(intent_request)["DiningTime"]
    phone_number = get_slots(intent_request)["PhoneNumber"]
    source = intent_request['invocationSource']
    
    
    if source == 'DialogCodeHook':
        slots = get_slots(intent_request)
        validation_result = validate_make_suggestions(location, cuisine, dining_time, num_people, phone_number)
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] = None
            return elicit_slot(intent_request['sessionAttributes'],
                               intent_request['currentIntent']['name'],
                               slots,
                               validation_result['violatedSlot'],
                               validation_result['message'])
                               
        output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
        return delegate(output_session_attributes, get_slots(intent_request)
        
    return close(intent_request['sessionAttributes'],
                'Fulfilled',
                 {'contentType': 'PlainText',
                 'content': 'Thanks, your order for {} has been placed and will be ready for pickup by {} on {}'.format(flower_type, pickup_time, date)})
"""
""" --- Intents --- """


def dispatch(intent_request):
    """
    Called when the user specifies an intent for this bot.
    """

    logger.debug('dispatch userId={}, intentName={}'.format(intent_request['userId'], intent_request['currentIntent']['name']))

    intent_name = intent_request['currentIntent']['name']

    # Dispatch to your bot's intent handlers
    if intent_name == 'OrderFlowers':
        return order_flowers(intent_request)
    if intent_name == 'MakeGreeting':
        return close(intent_request['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': 'Hey there, how can I help you?'})
    if intent_name == 'MakeThankYou':
        return close(intent_request['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': 'Thanks for coming!'})
    if intent_name == 'MakeDiningSuggestions':
        return make_suggestions(intent_request)

    raise Exception('Intent with name ' + intent_name + ' not supported')


""" --- Main handler --- """


def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    # By default, treat the user request as coming from the America/New_York time zone.
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    logger.debug('event.bot.name={}'.format(event['bot']['name']))
    
    temp = dispatch(event)
    
    if temp['dialogAction']['type'] == 'Close':
        t = temp['dialogAction']['message']['content']
        if t == 'Hey there, how can I help you?' or t =='Thanks for coming!':
            return temp
        else:
            arr = t.split()
            message = {}
            message['location'] = tArray[9]
            message['cuisine'] = tArray[6]
            message['numPeople'] = tArray[13]
            message['diningTime'] = tArray[11]
            message['phoneNumber'] = tArray[19]
        
            sqs = boto3.resource('sqs')
            #queue = sqs.get_queue_by_name(QueueName='NewQueue.fifo')
            #queue.send_message(MessageBody='body': json.dumps(message))
            return temp
        
    return temp
    